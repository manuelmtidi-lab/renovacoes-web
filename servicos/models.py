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

    class Tratamento(models.TextChoices):
        POR_CONTACTAR = "por_contactar", "Por contactar"
        CONTACTADO = "contactado", "Cliente contactado"
        PROFORMA = "proforma", "Proforma enviada"
        PAGO = "pago", "Pago"

    class Ciclo(models.IntegerChoices):
        MENSAL = 1, "Mensal"
        TRIMESTRAL = 3, "Trimestral"
        SEMESTRAL = 6, "Semestral"
        ANUAL = 12, "Anual"
        BIENAL = 24, "Bienal"

    ciclo = models.PositiveSmallIntegerField("ciclo de renovação", choices=Ciclo.choices, default=Ciclo.ANUAL)
    class Moeda(models.TextChoices):
        KZ = "kz", "Kwanza"
        USD = "usd", "Dólar"

    moeda = models.CharField("moeda do custo", max_length=3, choices=Moeda.choices, default=Moeda.KZ)
    custo_usd = models.DecimalField("custo em USD", max_digits=12, decimal_places=2, null=True, blank=True)
    tratamento = models.CharField("tratamento", max_length=15, choices=Tratamento.choices, default=Tratamento.POR_CONTACTAR)

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


# ---- WhatsApp: ligação com a mensagem já escrita ----
def telefone_whatsapp(numero):
    """Devolve só dígitos em formato internacional (Angola +244), ou "" se não servir."""
    d = "".join(c for c in (numero or "") if c.isdigit())
    if d.startswith("00"):
        d = d[2:]
    if len(d) == 9 and d.startswith("9"):
        d = "244" + d
    if d.startswith("244") and len(d) == 12:
        return d
    if len(d) >= 11 and not d.startswith("244"):
        return d  # outro país, já com indicativo
    return ""


def _link_whatsapp(self):
    from urllib.parse import quote
    numero = telefone_whatsapp(self.projecto.cliente.telefone)
    if not numero:
        return ""
    preco = f"{self.preco_venda:,.0f}".replace(",", ".")
    verbo = "expirou a" if self.dias_para_expirar < 0 else "expira a"
    texto = (
        f"Bom dia, {self.projecto.cliente.nome}. "
        f"O serviço {self.get_tipo_display()} do projecto {self.projecto.nome} "
        f"{verbo} {self.expira_em:%d/%m/%Y}. "
        f"A renovação custa {preco} Kz. Quer que renovemos?"
    )
    return f"https://wa.me/{numero}?text={quote(texto)}"


Servico.link_whatsapp = property(_link_whatsapp)


from django.conf import settings


class Nota(models.Model):
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE, related_name="notas")
    texto = models.CharField(max_length=500)
    utilizador = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return self.texto[:40]


def somar_meses(data, meses):
    """Soma meses a uma data; se o dia não existir no mês final, usa o último dia (31/01 + 1 mês = 28/02)."""
    import calendar
    total = data.year * 12 + (data.month - 1) + meses
    ano, mes = divmod(total, 12)
    mes += 1
    dia = min(data.day, calendar.monthrange(ano, mes)[1])
    return data.replace(year=ano, month=mes, day=dia)


class Cambio(models.Model):
    usd_kz = models.DecimalField("Kz por 1 USD", max_digits=12, decimal_places=4)
    fonte = models.CharField(max_length=80, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.usd_kz} Kz/USD ({self.criado_em:%d/%m/%Y})"


def cambio_actual():
    c = Cambio.objects.first()
    return c.usd_kz if c else None


def usd_para_kz(valor_usd, taxa):
    from decimal import Decimal
    return (Decimal(valor_usd) * Decimal(taxa)).quantize(Decimal("0.01"))
