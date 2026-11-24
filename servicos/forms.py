from django import forms
from django.contrib.auth import get_user_model

from .models import Cliente, Projecto, Servico


class EstiloMixin:
    """Aplica a classe .campo (definida em static/css/crud.css) a todos os campos."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs["class"] = "campo"


class ClienteForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["nome", "email", "telefone", "notas"]
        widgets = {"notas": forms.Textarea(attrs={"rows": 4})}


class _NomeUtilizador(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name() or obj.get_username()


class ProjectoForm(EstiloMixin, forms.ModelForm):
    tecnico = _NomeUtilizador(
        label="Técnico responsável", queryset=None, required=False, empty_label="Sem técnico"
    )

    class Meta:
        model = Projecto
        fields = ["cliente", "nome", "url", "estado", "tecnico"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tecnico"].queryset = get_user_model().objects.filter(is_active=True).order_by(
            "first_name", "username"
        )
        self.fields["cliente"].empty_label = "Escolha o cliente"


class ServicoForm(EstiloMixin, forms.ModelForm):
    class Meta:
        model = Servico
        fields = [
            "projecto",
            "tipo",
            "fornecedor",
            "custo",
            "preco_venda",
            "inicio",
            "expira_em",
            "ciclo",
            "estado",
        ]
        widgets = {
            "inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "expira_em": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["projecto"].queryset = Projecto.objects.select_related("cliente").order_by(
            "cliente__nome", "nome"
        )
        self.fields["projecto"].empty_label = "Escolha o projecto"
        self.fields["custo"].label = "Custo (Kz)"
        self.fields["preco_venda"].label = "Preço de venda (Kz)"

    def clean(self):
        dados = super().clean()
        inicio, expira = dados.get("inicio"), dados.get("expira_em")
        if inicio and expira and expira < inicio:
            self.add_error("expira_em", "A expiração não pode ser anterior ao início.")
        for nome in ("custo", "preco_venda"):
            valor = dados.get(nome)
            if valor is not None and valor < 0:
                self.add_error(nome, "O valor não pode ser negativo.")
        return dados


class RenovacaoForm(forms.Form):
    data = forms.DateField(label="Data da renovação", widget=forms.DateInput(attrs={"type": "date"}))
    valor = forms.DecimalField(label="Valor cobrado (Kz)", max_digits=12, decimal_places=2, min_value=0)
    nova_expiracao = forms.DateField(label="Nova expiração", widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, servico=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.servico = servico

    def clean_nova_expiracao(self):
        nova = self.cleaned_data["nova_expiracao"]
        if self.servico and nova <= self.servico.expira_em:
            raise forms.ValidationError("Tem de ser posterior à expiração actual.")
        return nova
