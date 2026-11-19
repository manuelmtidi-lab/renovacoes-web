from django.conf import settings
from django.db import models
from django.utils import timezone


class Cliente(models.Model):
    nome = models.CharField(max_length=200)
    email = models.EmailField("email de contacto", blank=True)
    telefone = models.CharField("telefone de contacto", max_length=30, blank=True)
    notas = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Projecto(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        PAUSADO = "pausado", "Pausado"
        ARQUIVADO = "arquivado", "Arquivado"

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="projectos")
    nome = models.CharField(max_length=200)
    url = models.URLField(blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.ACTIVO)
    tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="técnico responsável",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="projectos_atribuidos",
    )

    class Meta:
        ordering = ["cliente__nome", "nome"]

    def __str__(self):
        return f"{self.nome} ({self.cliente})"


class Servico(models.Model):
    class Tipo(models.TextChoices):
        DOMINIO = "dominio", "Domínio"
        HOSTING = "hosting", "Hosting"
        SSL = "ssl", "Certificado SSL"
        MANUTENCAO = "manutencao", "Manutenção"
        LICENCA = "licenca", "Licença"

    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        CANCELADO = "cancelado", "Cancelado"

    projecto = models.ForeignKey(Projecto, on_delete=models.CASCADE, related_name="servicos")
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    fornecedor = models.CharField(max_length=150, blank=True)
    custo = models.DecimalField(max_digits=12, decimal_places=2)
    preco_venda = models.DecimalField("preço de venda", max_digits=12, decimal_places=2)
    inicio = models.DateField("início")
    expira_em = models.DateField("expira em")
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.ACTIVO)

    class Meta:
        ordering = ["expira_em"]
        verbose_name = "serviço"
        verbose_name_plural = "serviços"

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.projecto.nome}"

    @property
    def dias_para_expirar(self):
        return (self.expira_em - timezone.localdate()).days

    @property
    def estado_alerta(self):
        dias = self.dias_para_expirar
        if dias < 0:
            return "atrasado"
        if dias <= 7:
            return "7_dias"
        if dias <= 30:
            return "30_dias"
        if dias <= 60:
            return "60_dias"
        return "ok"

    @property
    def margem(self):
        return self.preco_venda - self.custo


class Renovacao(models.Model):
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE, related_name="renovacoes")
    data = models.DateField(default=timezone.localdate)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    nova_expiracao = models.DateField("nova expiração")
    utilizador = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="renovacoes"
    )

    class Meta:
        ordering = ["-data"]
        verbose_name = "renovação"
        verbose_name_plural = "renovações"

    def __str__(self):
        return f"Renovação de {self.servico} em {self.data}"


class Alerta(models.Model):
    DIAS = [(60, "60 dias"), (30, "30 dias"), (7, "7 dias")]

    servico = models.ForeignKey(Servico, on_delete=models.CASCADE, related_name="alertas")
    dias_antes = models.PositiveSmallIntegerField(choices=DIAS)
    expira_em_ref = models.DateField("expiração a que se refere")
    enviado_em = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-enviado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["servico", "dias_antes", "expira_em_ref"],
                name="alerta_unico_por_servico_prazo_e_expiracao",
            )
        ]

    def __str__(self):
        return f"Alerta {self.dias_antes} dias - {self.servico}"
