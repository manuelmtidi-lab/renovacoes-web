from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone

from .crud import servicos_visiveis
from .models import Renovacao, Servico

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def ultimos_meses(hoje, n=12):
    """Lista de (ano, mês) dos últimos n meses, do mais antigo ao actual."""
    ano, mes, lista = hoje.year, hoje.month, []
    for _ in range(n):
        lista.append((ano, mes))
        mes -= 1
        if mes == 0:
            ano, mes = ano - 1, 12
    return lista[::-1]


@login_required
def inicio(request):
    hoje = timezone.localdate()
    visiveis = servicos_visiveis(request)
    activos = visiveis.filter(estado=Servico.Estado.ACTIVO)

    em_30 = activos.filter(expira_em__gte=hoje, expira_em__lte=hoje + timedelta(days=30))
    totais = em_30.aggregate(receita=Sum("preco_venda"), custo=Sum("custo"))
    receita = totais["receita"] or Decimal("0")
    custo = totais["custo"] or Decimal("0")

    ta = activos.aggregate(venda=Sum("preco_venda"), custo=Sum("custo"))
    margem_activa = (ta["venda"] or Decimal("0")) - (ta["custo"] or Decimal("0"))

    meses = ultimos_meses(hoje)
    inicio_periodo = date(meses[0][0], meses[0][1], 1)
    por_mes = {
        (r["mes"].year, r["mes"].month): r["total"]
        for r in Renovacao.objects.filter(
            servico__in=visiveis.values("pk"), data__gte=inicio_periodo
        )
        .annotate(mes=TruncMonth("data"))
        .values("mes")
        .annotate(total=Sum("valor"))
    }
    valores = [float(por_mes.get(m, 0)) for m in meses]

    contexto = {
        "hoje": hoje,
        "atrasados": activos.filter(expira_em__lt=hoje).count(),
        "em_7": activos.filter(
            expira_em__gte=hoje, expira_em__lte=hoje + timedelta(days=7)
        ).count(),
        "em_30": em_30.count(),
        "receita": receita,
        "margem": receita - custo,
        "margem_activa": margem_activa,
        "receita_12m": sum(valores),
        "grafico": {
            "etiquetas": [f"{MESES[m - 1]} {str(a)[2:]}" for a, m in meses],
            "valores": valores,
        },
        "proximos": activos.filter(expira_em__lte=hoje + timedelta(days=60))[:8],
    }
    return render(request, "inicio.html", contexto)


def entrada(request):
    """Raiz do site: painel para quem tem sessão, página de entrada para os outros."""
    if request.user.is_authenticated:
        return inicio(request)
    from django.shortcuts import render
    return render(request, "entrada.html")
