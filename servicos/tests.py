from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from .models import Alerta, Cliente, Projecto, Servico

User = get_user_model()


def novo_servico(projecto, dias, tipo=Servico.Tipo.HOSTING):
    hoje = timezone.localdate()
    return Servico.objects.create(
        projecto=projecto, tipo=tipo, custo=Decimal("1000"), preco_venda=Decimal("1500"),
        inicio=hoje - timedelta(days=300), expira_em=hoje + timedelta(days=dias),
    )


class BaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor_grupo = Group.objects.get_or_create(name="Gestor comercial")[0]
        cls.gestor = User.objects.create_user("gestor", "gestor@exemplo.ao", "x")
        cls.gestor.groups.add(cls.gestor_grupo)
        cls.tecnico = User.objects.create_user("tecnico", "tecnico@exemplo.ao", "x")
        cls.outro = User.objects.create_user("outro", "outro@exemplo.ao", "x")
        cls.cliente = Cliente.objects.create(nome="Cliente Teste")
        cls.projecto = Projecto.objects.create(cliente=cls.cliente, nome="P1", tecnico=cls.tecnico)
        cls.projecto2 = Projecto.objects.create(cliente=cls.cliente, nome="P2", tecnico=cls.outro)


class DiasETestEstado(BaseTest):
    def test_dias_para_expirar_e_estado_alerta(self):
        casos = {-1: "atrasado", 0: "7_dias", 7: "7_dias", 8: "30_dias",
                 30: "30_dias", 31: "60_dias", 60: "60_dias", 61: "ok"}
        for dias, estado in casos.items():
            s = novo_servico(self.projecto, dias)
            self.assertEqual(s.dias_para_expirar, dias)
            self.assertEqual(s.estado_alerta, estado, f"{dias} dias")


class PermissoesTecnico(BaseTest):
    def test_tecnico_so_ve_os_seus_servicos(self):
        meu = novo_servico(self.projecto, 10)
        alheio = novo_servico(self.projecto2, 10)
        self.client.force_login(self.tecnico)
        self.assertEqual(self.client.get(f"/servicos/{meu.pk}/").status_code, 200)
        self.assertEqual(self.client.get(f"/servicos/{alheio.pk}/").status_code, 404)

    def test_tecnico_nao_pode_renovar(self):
        meu = novo_servico(self.projecto, 10)
        self.client.force_login(self.tecnico)
        self.assertEqual(self.client.get(f"/servicos/{meu.pk}/renovar/").status_code, 403)


class AlertasSemDuplicados(BaseTest):
    def correr(self):
        call_command("enviar_alertas", stdout=StringIO())

    def test_alerta_nao_se_repete_no_mesmo_ciclo(self):
        s = novo_servico(self.projecto, 5)
        self.correr()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(Alerta.objects.filter(servico=s).count(), 1)
        self.correr()
        self.assertEqual(len(mail.outbox), 1)

    def test_alerta_volta_a_poder_ser_enviado_apos_renovacao(self):
        s = novo_servico(self.projecto, 5)
        self.correr()
        s.expira_em = timezone.localdate() + timedelta(days=6)
        s.save()
        self.correr()
        self.assertEqual(len(mail.outbox), 2)


from django.test import SimpleTestCase
from servicos.models import telefone_whatsapp


class TelefoneWhatsappTests(SimpleTestCase):
    def test_formatos_de_angola(self):
        for entrada in ("923 456 789", "923456789", "+244 923 456 789", "00244923456789", "(244) 923-456-789"):
            self.assertEqual(telefone_whatsapp(entrada), "244923456789")

    def test_invalidos(self):
        for entrada in ("", None, "12345", "abc"):
            self.assertEqual(telefone_whatsapp(entrada), "")


class TratamentoTests(BaseTest):
    def test_gestor_altera_tratamento_e_guarda_nota(self):
        s = novo_servico(self.projecto, 20)
        self.client.force_login(self.gestor)
        r = self.client.post(f"/servicos/{s.pk}/tratamento/", {"tratamento": "contactado", "nota": "Falei com o cliente"})
        self.assertEqual(r.status_code, 302)
        s.refresh_from_db()
        self.assertEqual(s.tratamento, "contactado")
        nota = s.notas.get()
        self.assertEqual(nota.texto, "Falei com o cliente")
        self.assertEqual(nota.utilizador, self.gestor)

    def test_tecnico_nao_pode_alterar(self):
        s = novo_servico(self.projecto, 20)
        self.client.force_login(self.tecnico)
        r = self.client.post(f"/servicos/{s.pk}/tratamento/", {"tratamento": "pago", "nota": "x"})
        self.assertEqual(r.status_code, 403)
        s.refresh_from_db()
        self.assertEqual(s.tratamento, "por_contactar")
        self.assertEqual(s.notas.count(), 0)

    def test_estado_invalido_e_ignorado(self):
        s = novo_servico(self.projecto, 20)
        self.client.force_login(self.gestor)
        self.client.post(f"/servicos/{s.pk}/tratamento/", {"tratamento": "inventado"})
        s.refresh_from_db()
        self.assertEqual(s.tratamento, "por_contactar")

    def test_renovar_repoe_tratamento_e_mantem_notas(self):
        from datetime import timedelta
        from django.utils import timezone
        s = novo_servico(self.projecto, 10)
        self.client.force_login(self.gestor)
        self.client.post(f"/servicos/{s.pk}/tratamento/", {"tratamento": "pago", "nota": "Pago em dinheiro"})
        nova = s.expira_em + timedelta(days=365)
        r = self.client.post(f"/servicos/{s.pk}/renovar/", {
            "data": timezone.localdate().isoformat(),
            "valor": "50000",
            "nova_expiracao": nova.isoformat(),
        })
        self.assertEqual(r.status_code, 302)
        s.refresh_from_db()
        self.assertEqual(s.expira_em, nova)
        self.assertEqual(s.tratamento, "por_contactar")
        self.assertEqual(s.notas.count(), 1)
        self.assertEqual(s.renovacoes.count(), 1)


class DiferencaSslTests(SimpleTestCase):
    def test_dias_de_diferenca(self):
        from datetime import date
        from servicos.management.commands.verificar_ssl import dias_de_diferenca
        self.assertEqual(dias_de_diferenca(date(2026, 12, 10), date(2026, 12, 1)), 9)
        self.assertEqual(dias_de_diferenca(date(2026, 12, 1), date(2026, 12, 10)), -9)
        self.assertEqual(dias_de_diferenca(date(2026, 12, 1), date(2026, 12, 1)), 0)


class SomarMesesTests(SimpleTestCase):
    def test_somar_meses(self):
        from datetime import date
        from servicos.models import somar_meses
        self.assertEqual(somar_meses(date(2026, 1, 31), 1), date(2026, 2, 28))
        self.assertEqual(somar_meses(date(2027, 1, 31), 1), date(2027, 2, 28))
        self.assertEqual(somar_meses(date(2028, 1, 31), 1), date(2028, 2, 29))
        self.assertEqual(somar_meses(date(2028, 2, 29), 12), date(2029, 2, 28))
        self.assertEqual(somar_meses(date(2026, 11, 24), 3), date(2027, 2, 24))
        self.assertEqual(somar_meses(date(2026, 12, 15), 24), date(2028, 12, 15))


class CambioTests(SimpleTestCase):
    def test_usd_para_kz(self):
        from decimal import Decimal
        from servicos.models import usd_para_kz
        self.assertEqual(usd_para_kz("10.00", "912.5"), Decimal("9125.00"))

    def test_taxa_plausivel(self):
        from decimal import Decimal
        from servicos.management.commands.actualizar_cambio import taxa_plausivel
        self.assertTrue(taxa_plausivel(Decimal("920"), None))
        self.assertTrue(taxa_plausivel(Decimal("920"), Decimal("900")))
        self.assertFalse(taxa_plausivel(Decimal("1500"), Decimal("900")))
        self.assertFalse(taxa_plausivel(Decimal("0"), Decimal("900")))


class ProformaTests(BaseTest):
    def test_gestor_recebe_pdf(self):
        s = novo_servico(self.projecto, 20)
        self.client.force_login(self.gestor)
        r = self.client.get(f"/servicos/{s.pk}/proforma/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))

    def test_tecnico_nao_pode(self):
        s = novo_servico(self.projecto, 20)
        self.client.force_login(self.tecnico)
        self.assertEqual(self.client.get(f"/servicos/{s.pk}/proforma/").status_code, 403)


class RenovarHtmxTests(BaseTest):
    def test_renovar_via_htmx_devolve_hx_redirect(self):
        from datetime import timedelta
        from django.utils import timezone
        s = novo_servico(self.projecto, 10)
        self.client.force_login(self.gestor)
        r = self.client.post(f"/servicos/{s.pk}/renovar/", {
            "data": timezone.localdate().isoformat(),
            "valor": "50000",
            "nova_expiracao": (s.expira_em + timedelta(days=365)).isoformat(),
        }, HTTP_HX_REQUEST="true")
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r["HX-Redirect"], f"/servicos/{s.pk}/")


class ActividadeTests(BaseTest):
    def test_tratamento_fica_registado(self):
        from servicos.models import Actividade
        s = novo_servico(self.projecto, 20)
        self.client.force_login(self.gestor)
        self.client.post(f"/servicos/{s.pk}/tratamento/", {"tratamento": "contactado", "nota": "Liguei"})
        acoes = set(Actividade.objects.values_list("acao", flat=True))
        self.assertEqual(acoes, {"tratamento", "nota"})
        self.assertEqual(Actividade.objects.filter(acao="tratamento").get().utilizador, self.gestor)

    def test_so_administrador_ve_a_pagina(self):
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.get("/actividade/").status_code, 403)
        admin = User.objects.create_user("admin1", "admin1@exemplo.ao", "x")
        admin.groups.add(Group.objects.get_or_create(name="Administrador")[0])
        self.client.force_login(admin)
        self.assertEqual(self.client.get("/actividade/").status_code, 200)

    def test_apagar_fica_registado(self):
        from servicos.models import Actividade
        s = novo_servico(self.projecto, 20)
        admin = User.objects.create_user("admin2", "admin2@exemplo.ao", "x")
        admin.groups.add(Group.objects.get_or_create(name="Administrador")[0])
        self.client.force_login(admin)
        self.client.post(f"/servicos/{s.pk}/apagar/")
        self.assertTrue(Actividade.objects.filter(acao="apagou").exists())


class ResumoSemanalTests(BaseTest):
    def test_sem_nada_nao_envia(self):
        from django.utils import timezone
        from servicos.management.commands.resumo_semanal import montar_resumo
        self.assertIsNone(montar_resumo(timezone.localdate()))

    def test_resumo_inclui_atrasados_e_proximos(self):
        from django.utils import timezone
        from servicos.management.commands.resumo_semanal import montar_resumo
        novo_servico(self.projecto, -3)
        novo_servico(self.projecto, 5)
        novo_servico(self.projecto, 40)
        assunto, texto = montar_resumo(timezone.localdate())
        self.assertIn("1 em atraso, 1 a expirar", assunto)
        self.assertIn("EM ATRASO (1)", texto)
        self.assertIn("PRÓXIMOS 14 DIAS (1)", texto)

    def test_so_admin_e_gestor_recebem(self):
        from servicos.management.commands.resumo_semanal import destinatarios_resumo
        self.assertEqual(destinatarios_resumo(), ["gestor@exemplo.ao"])


class ExportarCsvTests(BaseTest):
    def test_gestor_exporta_com_filtro(self):
        novo_servico(self.projecto, 10)
        self.client.force_login(self.gestor)
        r = self.client.get("/servicos/exportar/?tipo=dominio")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r["Content-Type"])
        self.assertTrue(r.content.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn("Custo", r.content.decode("utf-8-sig").splitlines()[0])

    def test_tecnico_nao_exporta(self):
        self.client.force_login(self.tecnico)
        self.assertEqual(self.client.get("/servicos/exportar/").status_code, 403)


class LoteTests(BaseTest):
    def _dados(self, a, b, nova_b=None):
        from datetime import timedelta
        from django.utils import timezone
        return {
            "ids": [a.pk, b.pk], "data": timezone.localdate().isoformat(),
            f"nova_{a.pk}": (a.expira_em + timedelta(days=365)).isoformat(), f"valor_{a.pk}": "1000",
            f"nova_{b.pk}": nova_b or (b.expira_em + timedelta(days=365)).isoformat(), f"valor_{b.pk}": "2000",
        }

    def test_lote_renova_todos(self):
        a, b = novo_servico(self.projecto, 5), novo_servico(self.projecto2, 8)
        self.client.force_login(self.gestor)
        r = self.client.post("/servicos/lote/", self._dados(a, b))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(a.renovacoes.count() + b.renovacoes.count(), 2)

    def test_erro_num_nao_grava_nenhum(self):
        a, b = novo_servico(self.projecto, 5), novo_servico(self.projecto, 8)
        self.client.force_login(self.gestor)
        r = self.client.post("/servicos/lote/", self._dados(a, b, nova_b=b.expira_em.isoformat()))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(a.renovacoes.count() + b.renovacoes.count(), 0)

    def test_tecnico_nao_pode(self):
        self.client.force_login(self.tecnico)
        self.assertEqual(self.client.get("/servicos/lote/").status_code, 403)
