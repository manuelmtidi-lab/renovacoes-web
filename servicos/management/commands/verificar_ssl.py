import socket
import ssl
from datetime import datetime, timezone as tz
from urllib.parse import urlparse

from django.core.management.base import BaseCommand

from servicos.models import Servico

TEMPO_LIMITE = 6


def dias_de_diferenca(real, registada):
    """Dias entre a data real do certificado e a registada (positivo = real é depois)."""
    return (real - registada).days


def data_do_certificado(host, porta=443):
    contexto = ssl.create_default_context()
    with socket.create_connection((host, porta), timeout=TEMPO_LIMITE) as sock:
        with contexto.wrap_socket(sock, server_hostname=host) as ssock:
            cert = ssock.getpeercert()
    fim = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
    return fim.replace(tzinfo=tz.utc).date()


class Command(BaseCommand):
    help = "Compara a data real do certificado SSL com a registada. Só mostra, a menos que uses --aplicar."

    def add_arguments(self, parser):
        parser.add_argument("--aplicar", action="store_true", help="Actualiza a expiração registada com a data real.")

    def handle(self, *args, **opcoes):
        servicos = (
            Servico.objects.filter(tipo=Servico.Tipo.SSL, estado=Servico.Estado.ACTIVO)
            .select_related("projecto__cliente")
        )
        verificados = diferentes = erros = 0
        for s in servicos:
            url = s.projecto.url
            host = urlparse(url).hostname if url.startswith("https://") else None
            if not host:
                self.stdout.write(f"- {s}: sem URL https no projecto, ignorado")
                continue
            try:
                real = data_do_certificado(host)
            except Exception as e:
                erros += 1
                self.stdout.write(self.style.ERROR(f"! {s} ({host}): {type(e).__name__}"))
                continue
            verificados += 1
            dif = dias_de_diferenca(real, s.expira_em)
            if dif == 0:
                self.stdout.write(self.style.SUCCESS(f"= {s} ({host}): igual ({real:%d/%m/%Y})"))
                continue
            diferentes += 1
            self.stdout.write(self.style.WARNING(
                f"~ {s} ({host}): registada {s.expira_em:%d/%m/%Y}, real {real:%d/%m/%Y} ({dif:+d} dias)"
            ))
            if opcoes["aplicar"]:
                s.expira_em = real
                s.save(update_fields=["expira_em"])
                self.stdout.write("  actualizada")
        self.stdout.write(f"Verificados: {verificados} · Diferentes: {diferentes} · Erros: {erros}")
        if diferentes and not opcoes["aplicar"]:
            self.stdout.write("Para actualizar as datas, corre com --aplicar.")
