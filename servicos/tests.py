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
