from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from servicos.models import Cliente, Projecto, Servico

CLIENTES = [
    ("Mercearia Girassol", "Loja online"),
    ("Clínica Vida Plena", "Marcações online"),
    ("Escola Horizonte", "Portal da escola"),
    ("Transportes Kalunga", "Site institucional"),
    ("Pousada Baía Azul", "Reservas"),
]
TIPOS = [
    (Servico.Tipo.DOMINIO, "NomeCerto", 12000, 18000),
    (Servico.Tipo.HOSTING, "HostAngola", 45000, 70000),
    (Servico.Tipo.SSL, "Certifica+", 8000, 15000),
    (Servico.Tipo.MANUTENCAO, "Equipa interna", 60000, 120000),
    (Servico.Tipo.LICENCA, "Licenças Norte", 80000, 130000),
]
DIAS = [-12, -3, 2, 5, 9, 14, 21, 28, 33, 47, 58, 75, 120, 200, 300]


class Command(BaseCommand):
    help = "Cria dados inventados para testar o painel."

    def add_arguments(self, parser):
        parser.add_argument("--forcar", action="store_true", help="Cria mesmo que já existam clientes.")

    def handle(self, *args, **opcoes):
        if Cliente.objects.exists() and not opcoes["forcar"]:
            self.stdout.write("Já existem clientes. Use --forcar para criar mesmo assim.")
            return

        hoje = timezone.localdate()
        projectos = []
        for nome, projecto in CLIENTES:
            cliente = Cliente.objects.create(
                nome=nome, email="contacto@example.com", telefone="900 000 000"
            )
            projectos.append(Projecto.objects.create(cliente=cliente, nome=projecto))

        for i, dias in enumerate(DIAS):
            tipo, fornecedor, custo, preco = TIPOS[i % len(TIPOS)]
            expira = hoje + timedelta(days=dias)
            Servico.objects.create(
                projecto=projectos[i % len(projectos)],
                tipo=tipo,
                fornecedor=fornecedor,
                custo=Decimal(custo),
                preco_venda=Decimal(preco),
                inicio=expira - timedelta(days=365),
                expira_em=expira,
            )
        self.stdout.write(self.style.SUCCESS("Dados de demonstração criados."))
