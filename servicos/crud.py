"""Clientes, projectos e serviços: listas com HTMX, detalhe, criar, editar e apagar.

Perfis (grupos criados na migração 0002_grupos):
- Administrador (ou superutilizador): tudo, incluindo apagar.
- Gestor comercial: ver, criar e editar tudo.
- Técnico (e quem não tem grupo): só vê os projectos que lhe estão atribuídos, só leitura.
"""
from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.vary import vary_on_headers

from .forms import ClienteForm, ProjectoForm, RenovacaoForm, ServicoForm
from .models import Cliente, Projecto, Renovacao, Servico

POR_PAGINA = 15

ALERTAS = [
    ("atrasado", "Atrasados"),
    ("7_dias", "Até 7 dias"),
    ("30_dias", "8 a 30 dias"),
    ("60_dias", "31 a 60 dias"),
    ("ok", "Mais de 60 dias"),
]


# ---------------------------------------------------------------- permissões
def perfil(request):
    if not hasattr(request, "_perfil"):
        user = request.user
        nomes = set(user.groups.values_list("name", flat=True))
        if user.is_superuser or "Administrador" in nomes:
            request._perfil = "administrador"
        elif "Gestor comercial" in nomes:
            request._perfil = "gestor"
        else:
            request._perfil = "tecnico"
    return request._perfil


def exigir(*perfis):
    """Login obrigatório e perfil dentro da lista; caso contrário, 403."""

    def decorador(view):
        @login_required
        @wraps(view)
        def interna(request, *args, **kwargs):
            if perfil(request) not in perfis:
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return interna

    return decorador


EDITAR = ("administrador", "gestor")
APAGAR = ("administrador",)


def clientes_visiveis(request):
    if perfil(request) == "tecnico":
        ids = Projecto.objects.filter(tecnico=request.user).values("cliente_id")
        return Cliente.objects.filter(pk__in=ids)
    return Cliente.objects.all()


def projectos_visiveis(request):
    qs = Projecto.objects.select_related("cliente", "tecnico")
    if perfil(request) == "tecnico":
        qs = qs.filter(tecnico=request.user)
    return qs


def servicos_visiveis(request):
    qs = Servico.objects.select_related("projecto__cliente")
    if perfil(request) == "tecnico":
        qs = qs.filter(projecto__tecnico=request.user)
    return qs


# ---------------------------------------------------------------- utilitários
def _int(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _escolha(valor, opcoes):
    return valor if valor in dict(opcoes) else ""


def _contexto(request, **extra):
    p = perfil(request)
    return {"pode_editar": p in EDITAR, "pode_apagar": p in APAGAR, **extra}


def _lista(request, completo, parcial, queryset, contexto):
    """Pagina e devolve a página completa, ou só a tabela quando o pedido vem do HTMX."""
    pagina = Paginator(queryset, POR_PAGINA).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    contexto.update(pagina=pagina, qs=params.urlencode())
    htmx = getattr(request, "htmx", None)
    if htmx and not htmx.history_restore_request:
        return render(request, parcial, contexto)
    return render(request, completo, contexto)


def _descrever_alteracoes(form):
    from django import forms as dj
    partes = []
    for nome in form.changed_data:
        campo = form.fields[nome]
        etiqueta = str(campo.label or nome)
        if isinstance(campo, dj.ModelChoiceField) or nome == "notas":
            partes.append(f"{etiqueta} alterado")
            continue
        antes = form.initial.get(nome)
        depois = form.cleaned_data.get(nome)
        antes = "—" if antes in (None, "") else antes
        depois = "—" if depois in (None, "") else depois
        partes.append(f"{etiqueta}: {antes} → {depois}")
    return "; ".join(partes)


def _formulario(request, Form, instancia, titulo, voltar, destino, mensagem, initial=None):
    if request.method == "POST":
        form = Form(request.POST, instance=instancia)
        if form.is_valid():
            from .models import registar
            criar = instancia is None or instancia.pk is None
            alteracoes = "" if criar else _descrever_alteracoes(form)
            obj = form.save()
            registar(request.user, "criou" if criar else "editou", obj, alteracoes)
            messages.success(request, mensagem)
            return redirect(destino, pk=obj.pk)
    else:
        form = Form(instance=instancia, initial=initial)
    return render(
        request,
        "crud/form.html",
        {"form": form, "titulo": titulo, "voltar": voltar, "largos": ["notas"]},
    )


def _apagar(request, obj, titulo, aviso, voltar, depois, erro_protegido=None):
    if request.method == "POST":
        from .models import registar, rotulo_objecto
        rotulo = rotulo_objecto(obj)
        try:
            obj.delete()
        except ProtectedError:
            messages.error(request, erro_protegido or "Não foi possível apagar este registo.")
            return redirect(voltar)
        registar(request.user, "apagou", rotulo)
        messages.success(request, "Apagado.")
        return redirect(depois)
    return render(
        request,
        "crud/confirmar_apagar.html",
        {"titulo": titulo, "objecto": str(obj), "aviso": aviso, "voltar": voltar},
    )


# ---------------------------------------------------------------- clientes
def _anotar_clientes(request, qs):
    if perfil(request) == "tecnico":
        meu = Q(projectos__tecnico=request.user)
        return qs.annotate(
            n_proj=Count("projectos", filter=meu, distinct=True),
            n_serv=Count("projectos__servicos", filter=meu, distinct=True),
        )
    return qs.annotate(
        n_proj=Count("projectos", distinct=True),
        n_serv=Count("projectos__servicos", distinct=True),
    )


@login_required
@vary_on_headers("HX-Request")
def cliente_lista(request):
    q = request.GET.get("q", "").strip()
    qs = _anotar_clientes(request, clientes_visiveis(request))
    if q:
        qs = qs.filter(Q(nome__icontains=q) | Q(email__icontains=q) | Q(telefone__icontains=q))
    return _lista(
        request, "clientes/lista.html", "clientes/_tabela.html", qs, _contexto(request, q=q)
    )


@login_required
def cliente_detalhe(request, pk):
    cliente = get_object_or_404(clientes_visiveis(request), pk=pk)
    projectos = (
        projectos_visiveis(request)
        .filter(cliente=cliente)
        .annotate(n_serv=Count("servicos"))
    )
    servicos = servicos_visiveis(request).filter(projecto__cliente=cliente)
    return render(
        request,
        "clientes/detalhe.html",
        _contexto(
            request,
            cliente=cliente,
            projectos=projectos,
            servicos=servicos[:POR_PAGINA],
            total_servicos=servicos.count(),
        ),
    )


@exigir(*EDITAR)
def cliente_novo(request):
    return _formulario(
        request, ClienteForm, None, "Novo cliente", "/clientes/", "cliente_detalhe",
        "Cliente criado.",
    )


@exigir(*EDITAR)
def cliente_editar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    return _formulario(
        request, ClienteForm, cliente, f"Editar {cliente.nome}",
        f"/clientes/{cliente.pk}/", "cliente_detalhe", "Cliente actualizado.",
    )


@exigir(*APAGAR)
def cliente_apagar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    n = cliente.projectos.count()
    aviso = (
        f"Este cliente tem {n} projecto{'s' if n != 1 else ''}. Apague ou mova os projectos "
        "primeiro, senão a operação será recusada."
        if n
        else "Esta acção não se pode desfazer."
    )
    return _apagar(
        request, cliente, "Apagar cliente", aviso, f"/clientes/{cliente.pk}/", "cliente_lista",
        erro_protegido="Não é possível apagar: o cliente ainda tem projectos.",
    )


# ---------------------------------------------------------------- projectos
@login_required
@vary_on_headers("HX-Request")
def projecto_lista(request):
    q = request.GET.get("q", "").strip()
    estado = _escolha(request.GET.get("estado"), Projecto.Estado.choices)
    cliente = _int(request.GET.get("cliente"))
    tecnico = _int(request.GET.get("tecnico"))

    qs = projectos_visiveis(request).annotate(n_serv=Count("servicos"))
    if q:
        qs = qs.filter(
            Q(nome__icontains=q) | Q(url__icontains=q) | Q(cliente__nome__icontains=q)
        )
    if estado:
        qs = qs.filter(estado=estado)
    if cliente:
        qs = qs.filter(cliente_id=cliente)
    if tecnico:
        qs = qs.filter(tecnico_id=tecnico)

    contexto = _contexto(
        request,
        q=q,
        estado_sel=estado,
        cliente_sel=cliente,
        tecnico_sel=tecnico,
        estados=Projecto.Estado.choices,
        clientes=clientes_visiveis(request),
        tecnicos=get_user_model().objects.filter(projectos_atribuidos__isnull=False).distinct(),
    )
    return _lista(request, "projectos/lista.html", "projectos/_tabela.html", qs, contexto)


@login_required
def projecto_detalhe(request, pk):
    projecto = get_object_or_404(projectos_visiveis(request), pk=pk)
    servicos = servicos_visiveis(request).filter(projecto=projecto)
    return render(
        request,
        "projectos/detalhe.html",
        _contexto(request, projecto=projecto, servicos=servicos),
    )


@exigir(*EDITAR)
def projecto_novo(request):
    initial = {}
    if _int(request.GET.get("cliente")):
        initial["cliente"] = _int(request.GET.get("cliente"))
    return _formulario(
        request, ProjectoForm, None, "Novo projecto", "/projectos/", "projecto_detalhe",
        "Projecto criado.", initial,
    )


@exigir(*EDITAR)
def projecto_editar(request, pk):
    projecto = get_object_or_404(Projecto, pk=pk)
    return _formulario(
        request, ProjectoForm, projecto, f"Editar {projecto.nome}",
        f"/projectos/{projecto.pk}/", "projecto_detalhe", "Projecto actualizado.",
    )


@exigir(*APAGAR)
def projecto_apagar(request, pk):
    projecto = get_object_or_404(Projecto, pk=pk)
    n = projecto.servicos.count()
    aviso = (
        f"Vão ser apagados também {n} serviço{'s' if n != 1 else ''} e o respectivo histórico "
        "de renovações. Esta acção não se pode desfazer."
        if n
        else "Esta acção não se pode desfazer."
    )
    return _apagar(
        request, projecto, "Apagar projecto", aviso, f"/projectos/{projecto.pk}/",
        "projecto_lista",
    )


# ---------------------------------------------------------------- serviços
def _filtrar_alerta(qs, alerta):
    hoje = timezone.localdate()

    def em(dias):
        return hoje + timedelta(days=dias)

    if alerta == "atrasado":
        return qs.filter(expira_em__lt=hoje)
    if alerta == "7_dias":
        return qs.filter(expira_em__gte=hoje, expira_em__lte=em(7))
    if alerta == "30_dias":
        return qs.filter(expira_em__gt=em(7), expira_em__lte=em(30))
    if alerta == "60_dias":
        return qs.filter(expira_em__gt=em(30), expira_em__lte=em(60))
    if alerta == "ok":
        return qs.filter(expira_em__gt=em(60))
    return qs


def _servicos_filtrados(request):
    q = request.GET.get("q", "").strip()
    tipo = _escolha(request.GET.get("tipo"), Servico.Tipo.choices)
    estado = _escolha(request.GET.get("estado"), Servico.Estado.choices)
    alerta = _escolha(request.GET.get("alerta"), ALERTAS)
    cliente = _int(request.GET.get("cliente"))

    qs = servicos_visiveis(request)
    if q:
        qs = qs.filter(
            Q(projecto__nome__icontains=q)
            | Q(projecto__cliente__nome__icontains=q)
            | Q(fornecedor__icontains=q)
        )
    if tipo:
        qs = qs.filter(tipo=tipo)
    if estado:
        qs = qs.filter(estado=estado)
    if cliente:
        qs = qs.filter(projecto__cliente_id=cliente)
    qs = _filtrar_alerta(qs, alerta)
    return q, tipo, estado, alerta, cliente, qs


@login_required
@vary_on_headers("HX-Request")
def servico_lista(request):
    q, tipo, estado, alerta, cliente, qs = _servicos_filtrados(request)

    contexto = _contexto(
        request,
        q=q,
        tipo_sel=tipo,
        estado_sel=estado,
        alerta_sel=alerta,
        cliente_sel=cliente,
        tipos=Servico.Tipo.choices,
        estados=Servico.Estado.choices,
        alertas=ALERTAS,
        clientes=clientes_visiveis(request),
    )
    return _lista(request, "servicos/lista.html", "servicos/_tabela.html", qs, contexto)


@login_required
def servico_detalhe(request, pk):
    servico = get_object_or_404(servicos_visiveis(request), pk=pk)
    return render(
        request,
        "servicos/detalhe.html",
        _contexto(
            request,
            servico=servico,
            renovacoes=servico.renovacoes.select_related("utilizador"),
        ),
    )


@exigir(*EDITAR)
def servico_novo(request):
    initial = {}
    if _int(request.GET.get("projecto")):
        initial["projecto"] = _int(request.GET.get("projecto"))
    return _formulario(
        request, ServicoForm, None, "Novo serviço", "/servicos/", "servico_detalhe",
        "Serviço criado.", initial,
    )


@exigir(*EDITAR)
def servico_editar(request, pk):
    servico = get_object_or_404(Servico, pk=pk)
    return _formulario(
        request, ServicoForm, servico, "Editar serviço",
        f"/servicos/{servico.pk}/", "servico_detalhe", "Serviço actualizado.",
    )


@exigir(*APAGAR)
def servico_apagar(request, pk):
    servico = get_object_or_404(Servico, pk=pk)
    n = servico.renovacoes.count()
    dica = "Se o cliente apenas deixou de usar o serviço, prefira alterar o estado para Cancelado."
    aviso = f"O histórico de {n} renovações também será apagado. {dica}" if n else dica
    return _apagar(
        request, servico, "Apagar serviço", aviso, f"/servicos/{servico.pk}/", "servico_lista"
    )


@exigir(*EDITAR)
def servico_renovar(request, pk):
    from .models import cambio_actual, registar
    servico = get_object_or_404(servicos_visiveis(request), pk=pk, estado=Servico.Estado.ACTIVO)
    if request.method == "POST":
        form = RenovacaoForm(request.POST, servico=servico)
        if form.is_valid():
            with transaction.atomic():
                Renovacao.objects.create(
                    servico=servico,
                    data=form.cleaned_data["data"],
                    valor=form.cleaned_data["valor"],
                    nova_expiracao=form.cleaned_data["nova_expiracao"],
                    utilizador=request.user,
                    custo=servico.custo,
                    cambio=cambio_actual() if servico.moeda == Servico.Moeda.USD else None,
                )
                servico.expira_em = form.cleaned_data["nova_expiracao"]
                servico.tratamento = Servico.Tratamento.POR_CONTACTAR
                servico.save(update_fields=["expira_em", "tratamento"])
                registar(
                    request.user, "renovou", servico,
                    f"nova expiração {form.cleaned_data['nova_expiracao']:%d/%m/%Y}; valor {form.cleaned_data['valor']:,.0f} Kz".replace(",", "."),
                )
            messages.success(request, "Renovação registada.")
            if getattr(request, "htmx", None):
                from django.http import HttpResponse
                from django.urls import reverse
                resposta = HttpResponse(status=204)
                resposta["HX-Redirect"] = reverse("servico_detalhe", args=[servico.pk])
                return resposta
            return redirect("servico_detalhe", pk=servico.pk)
    else:
        from .models import somar_meses
        proxima = somar_meses(servico.expira_em, servico.ciclo)
        form = RenovacaoForm(
            servico=servico,
            initial={"data": timezone.localdate(), "valor": servico.preco_venda, "nova_expiracao": proxima},
        )
    return render(request, "servicos/_renovar.html", {"form": form, "servico": servico})


@exigir(*EDITAR)
def servico_tratamento(request, pk):
    from .models import Nota
    servico = get_object_or_404(servicos_visiveis(request), pk=pk, estado=Servico.Estado.ACTIVO)
    if request.method == "POST":
        novo = request.POST.get("tratamento", "")
        texto = request.POST.get("nota", "").strip()[:500]
        from .models import registar
        if novo in Servico.Tratamento.values:
            if novo != servico.tratamento:
                registar(request.user, "tratamento", servico,
                         f"{servico.get_tratamento_display()} → {Servico.Tratamento(novo).label}")
            servico.tratamento = novo
            servico.save(update_fields=["tratamento"])
        if texto:
            Nota.objects.create(servico=servico, texto=texto, utilizador=request.user)
            registar(request.user, "nota", servico, texto[:200])
        messages.success(request, "Tratamento actualizado.")
    return redirect("servico_detalhe", pk=servico.pk)


@exigir(*EDITAR)
def servico_proforma(request, pk):
    from decouple import config
    from django.http import HttpResponse
    from .proforma import gerar_proforma, numero_proforma
    servico = get_object_or_404(servicos_visiveis(request), pk=pk, estado=Servico.Estado.ACTIVO)
    empresa = {
        "nome": config("EMPRESA_NOME", default=""),
        "nif": config("EMPRESA_NIF", default=""),
        "morada": config("EMPRESA_MORADA", default=""),
        "iban": config("EMPRESA_IBAN", default=""),
    }
    pdf = gerar_proforma(servico, empresa)
    resposta = HttpResponse(pdf, content_type="application/pdf")
    resposta["Content-Disposition"] = f'inline; filename="{numero_proforma(servico, timezone.localdate())}.pdf"'
    return resposta


@exigir("administrador")
def actividade(request):
    from .models import Actividade
    itens = Actividade.objects.select_related("utilizador")[:200]
    return render(request, "actividade.html", {"itens": itens})


def _seguro_csv(valor):
    texto = "" if valor is None else str(valor)
    return "'" + texto if texto[:1] in ("=", "+", "-", "@") else texto


@exigir(*EDITAR)
def servico_exportar(request):
    import csv
    from django.http import HttpResponse
    from .models import registar
    qs = _servicos_filtrados(request)[5].select_related("projecto__cliente")
    resposta = HttpResponse(content_type="text/csv; charset=utf-8")
    resposta["Content-Disposition"] = 'attachment; filename="servicos.csv"'
    resposta.write("\ufeff")
    w = csv.writer(resposta, delimiter=";")
    w.writerow(["Cliente", "Projecto", "Tipo", "Fornecedor", "Início", "Expira em", "Estado", "Ciclo", "Tratamento", "Preço de venda (Kz)"])
    n = 0
    for x in qs:
        w.writerow([_seguro_csv(v) for v in (
            x.projecto.cliente.nome, x.projecto.nome, x.get_tipo_display(), x.fornecedor,
            f"{x.inicio:%d/%m/%Y}", f"{x.expira_em:%d/%m/%Y}", x.get_estado_display(),
            x.get_ciclo_display(), x.get_tratamento_display(), x.preco_venda)])
        n += 1
    registar(request.user, "exportou", "Serviços (CSV)", f"{n} linhas")
    return resposta
