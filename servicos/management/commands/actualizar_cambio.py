import json
import urllib.request
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from servicos.models import Cambio, Servico, cambio_actual, usd_para_kz

URL_POR_OMISSAO = "https://open.er-api.com/v6/latest/USD"


def taxa_plausivel(nova, anterior, limite=Decimal("0.25")):
    """Aceita a nova taxa se for positiva e não saltar mais de 25% face à anterior."""
    if nova <= 0:
        return False
    if anterior is None:
        return True
    return abs(nova - anterior) / anterior <= limite


class Command(BaseCommand):
    help = "Actualiza o câmbio USD/Kz e recalcula o custo dos serviços activos em dólares."

    def add_arguments(self, parser):
        parser.add_argument("--manual", type=Decimal, help="Define a taxa à mão (Kz por 1 USD).")
        parser.add_argument("--forcar", action="store_true", help="Aceita a taxa mesmo com salto grande.")

    def handle(self, *args, **opcoes):
        anterior = cambio_actual()
        if opcoes["manual"] is not None:
            taxa, fonte = opcoes["manual"], "manual"
        else:
            url = getattr(settings, "CAMBIO_URL", URL_POR_OMISSAO)
            try:
                with urllib.request.urlopen(url, timeout=10) as r:
                    dados = json.load(r)
                taxa = Decimal(str(dados["rates"]["AOA"]))
            except Exception as e:
                raise CommandError(f"Não consegui obter o câmbio ({type(e).__name__}). Fica a taxa anterior: {anterior}.")
            fonte = url.split("/")[2]

        if not opcoes["forcar"] and not taxa_plausivel(taxa, anterior):
            raise CommandError(f"Taxa {taxa} suspeita (anterior: {anterior}). Usa --forcar se estiver certa.")

        Cambio.objects.create(usd_kz=taxa, fonte=fonte)
        n = 0
        for s in Servico.objects.filter(moeda=Servico.Moeda.USD, estado=Servico.Estado.ACTIVO, custo_usd__isnull=False):
            s.custo = usd_para_kz(s.custo_usd, taxa)
            s.save(update_fields=["custo"])
            n += 1
        self.stdout.write(self.style.SUCCESS(f"Câmbio: {taxa} Kz/USD ({fonte}). Serviços recalculados: {n}."))
