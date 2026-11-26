from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from servicos.models import Servico

DIAS = 14


def kz(valor):
    return f"{valor:,.0f}".replace(",", ".") + " Kz"


def destinatarios_resumo():
    User = get_user_model()
    emails = (
        User.objects.filter(Q(groups__name__in=["Administrador", "Gestor comercial"]), is_active=True)
        .exclude(email="").values_list("email", flat=True).distinct()
    )
    return sorted(set(emails))


def _linha(s):
    dias = s.dias_para_expirar
    quando = f"há {-dias} dia(s)" if dias < 0 else ("hoje" if dias == 0 else f"em {dias} dia(s)")
    return (
        f"- {s.get_tipo_display()} · {s.projecto.nome} ({s.projecto.cliente.nome}): "
        f"{s.expira_em:%d/%m/%Y}, {quando} · {kz(s.preco_venda)} · {s.get_tratamento_display()}"
    )


def montar_resumo(hoje):
    """Devolve (assunto, texto) ou None se não houver nada para avisar."""
    activos = Servico.objects.filter(estado=Servico.Estado.ACTIVO).select_related("projecto__cliente")
    atrasados = list(activos.filter(expira_em__lt=hoje).order_by("expira_em"))
    proximos = list(activos.filter(expira_em__gte=hoje, expira_em__lte=hoje + timedelta(days=DIAS)).order_by("expira_em"))
    if not atrasados and not proximos:
        return None
    receita = sum((s.preco_venda for s in proximos), Decimal("0"))
    margem = sum((s.preco_venda - s.custo for s in proximos), Decimal("0"))
    partes = [f"Resumo semanal de renovações · {hoje:%d/%m/%Y}", "", f"EM ATRASO ({len(atrasados)})"]
    partes += [_linha(s) for s in atrasados] or ["- Nenhum."]
    partes += ["", f"A EXPIRAR NOS PRÓXIMOS {DIAS} DIAS ({len(proximos)})"]
    partes += [_linha(s) for s in proximos] or ["- Nenhum."]
    partes += ["", f"Receita em jogo (próximos {DIAS} dias): {kz(receita)}", f"Margem prevista: {kz(margem)}"]
    assunto = f"[Renovações] Resumo semanal: {len(atrasados)} em atraso, {len(proximos)} a expirar"
    return assunto, "\n".join(partes)


class Command(BaseCommand):
    help = "Envia o resumo semanal ao Administrador e ao Gestor comercial."

    def add_arguments(self, parser):
        parser.add_argument("--simular", action="store_true", help="Mostra o texto, sem enviar.")

    def handle(self, *args, **opcoes):
        resumo = montar_resumo(timezone.localdate())
        if resumo is None:
            self.stdout.write("Nada em atraso nem a expirar: não enviei nada.")
            return
        assunto, texto = resumo
        para = destinatarios_resumo()
        if opcoes["simular"]:
            self.stdout.write(f"[simular] Para: {', '.join(para) or '(sem destinatários)'}")
            self.stdout.write(f"Assunto: {assunto}\n\n{texto}")
            return
        if not para:
            self.stdout.write(self.style.WARNING("Sem destinatários."))
            return
        enviados = 0
        for email in para:
            try:
                send_mail(subject=assunto, message=texto, from_email=None, recipient_list=[email])
                enviados += 1
            except Exception as erro:
                self.stdout.write(self.style.ERROR(f"Falhou {email}: {erro}"))
        self.stdout.write(self.style.SUCCESS(f"Resumos enviados: {enviados}"))
