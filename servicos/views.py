from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from .crud import servicos_visiveis
from .models import Servico


@login_required
def inicio(request):
    hoje = timezone.localdate()
    activos = servicos_visiveis(request).filter(estado=Servico.Estado.ACTIVO)

    em_30 = activos.filter(expira_em__gte=hoje, expira_em__lte=hoje + timedelta(days=30))
    totais = em_30.aggregate(receita=Sum("preco_venda"), custo=Sum("custo"))
    receita = totais["receita"] or Decimal("0")
    custo = totais["custo"] or Decimal("0")

    contexto = {
        "hoje": hoje,
        "atrasados": activos.filter(expira_em__lt=hoje).count(),
        "em_7": activos.filter(
            expira_em__gte=hoje, expira_em__lte=hoje + timedelta(days=7)
        ).count(),
        "em_30": em_30.count(),
        "receita": receita,
        "margem": receita - custo,
        "proximos": activos.filter(expira_em__lte=hoje + timedelta(days=60))[:8],
    }
    return render(request, "inicio.html", contexto)
