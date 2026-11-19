from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from servicos.models import Alerta, Servico

PRAZOS = (7, 30, 60)


def prazo_aplicavel(dias):
    """Menor prazo (7, 30 ou 60) que ainda cobre os dias que faltam."""
    for p in PRAZOS:
        if dias <= p:
            return p
    return None


def destinatarios(servico):
    User = get_user_model()
    q = Q(groups__name__in=["Administrador", "Gestor comercial"])
    if servico.projecto.tecnico_id:
        q |= Q(pk=servico.projecto.tecnico_id)
    emails = (
        User.objects.filter(q, is_active=True).exclude(email="")
        .values_list("email", flat=True).distinct()
    )
    return sorted(set(emails))


class Command(BaseCommand):
    help = "Envia alertas de expiração (60, 30 e 7 dias), sem repetir no mesmo ciclo."

    def add_arguments(self, parser):
        parser.add_argument("--simular", action="store_true", help="Mostra o que enviaria, sem enviar nem gravar.")

    def handle(self, *args, **opcoes):
        hoje = timezone.localdate()
        servicos = (
            Servico.objects.filter(
                estado=Servico.Estado.ACTIVO,
                expira_em__gte=hoje,
                expira_em__lte=hoje + timedelta(days=max(PRAZOS)),
            ).select_related("projecto__cliente", "projecto__tecnico")
        )
        enviados = 0
        for s in servicos:
            prazo = prazo_aplicavel(s.dias_para_expirar)
            para = destinatarios(s)
            if not para:
                self.stdout.write(self.style.WARNING(f"Sem destinatários: {s}"))
                continue
            if Alerta.objects.filter(servico=s, dias_antes=prazo, expira_em_ref=s.expira_em).exists():
                continue
            if opcoes["simular"]:
                self.stdout.write(f"[simular] {s} ({s.dias_para_expirar} dias) -> {', '.join(para)}")
                continue
            try:
                with transaction.atomic():
                    Alerta.objects.create(servico=s, dias_antes=prazo, expira_em_ref=s.expira_em)
                    send_mail(
                            subject=f"[Renovações] {s.get_tipo_display()} de {s.projecto.cliente.nome} expira em {s.dias_para_expirar} dia(s)",
                            message=(
                                f"Serviço: {s.get_tipo_display()}\n"
                                f"Projecto: {s.projecto.nome}\n"
                                f"Cliente: {s.projecto.cliente.nome}\n"
                                f"Expira em: {s.expira_em:%d/%m/%Y} (faltam {s.dias_para_expirar} dias)\n"
                            ),
                            from_email=None,
                            recipient_list=para,
                        )
            except Exception as erro:
                self.stdout.write(self.style.ERROR(f"Falhou {s}: {erro}"))
                continue
            enviados += 1
        self.stdout.write(self.style.SUCCESS(f"Alertas enviados: {enviados}"))
