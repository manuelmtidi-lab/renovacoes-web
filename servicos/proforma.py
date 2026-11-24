from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import somar_meses

VERDE = colors.HexColor("#4a7500")


def kz(valor):
    return f"{valor:,.0f}".replace(",", ".") + " Kz"


def numero_proforma(servico, hoje):
    return f"PF-{hoje:%Y%m%d}-{servico.pk}"


def gerar_proforma(servico, empresa):
    """Devolve os bytes do PDF. 'empresa' é um dicionário: nome, nif, morada, iban."""
    hoje = timezone.localdate()
    cliente = servico.projecto.cliente
    nova = somar_meses(servico.expira_em, servico.ciclo)

    base = getSampleStyleSheet()
    normal = ParagraphStyle("n", parent=base["Normal"], fontName="Helvetica", fontSize=10, leading=14)
    pequeno = ParagraphStyle("p", parent=normal, fontSize=8, textColor=colors.HexColor("#555555"))
    titulo = ParagraphStyle("t", parent=normal, fontName="Helvetica-Bold", fontSize=20, leading=24)
    rotulo = ParagraphStyle("r", parent=normal, fontName="Helvetica-Bold", fontSize=8, textColor=VERDE)

    elementos = []
    logo = Path(settings.BASE_DIR) / "static" / "img" / "tunganetu.png"
    if logo.exists():
        elementos.append(Image(str(logo), width=42 * mm, height=42 * mm * 120 / 355))
        elementos.append(Spacer(1, 6 * mm))

    linhas_empresa = [empresa.get("nome") or "", f"NIF {empresa['nif']}" if empresa.get("nif") else "", empresa.get("morada") or ""]
    elementos.append(Paragraph("<br/>".join(x for x in linhas_empresa if x), pequeno))
    elementos.append(Spacer(1, 8 * mm))

    elementos.append(Paragraph("PROFORMA", titulo))
    elementos.append(Paragraph("Este documento não é uma factura.", pequeno))
    elementos.append(Spacer(1, 5 * mm))
    elementos.append(Paragraph(f"Número: <b>{numero_proforma(servico, hoje)}</b> &nbsp;&nbsp; Data: <b>{hoje:%d/%m/%Y}</b>", normal))
    elementos.append(Spacer(1, 6 * mm))

    elementos.append(Paragraph("CLIENTE", rotulo))
    dados_cliente = [cliente.nome, cliente.email, cliente.telefone]
    elementos.append(Paragraph("<br/>".join(x for x in dados_cliente if x), normal))
    elementos.append(Spacer(1, 8 * mm))

    descricao = Paragraph(
        f"<b>Renovação de {servico.get_tipo_display()}</b><br/>Projecto: {servico.projecto.nome}"
        + (f"<br/>Fornecedor: {servico.fornecedor}" if servico.fornecedor else "")
        + f"<br/>Válido até {nova:%d/%m/%Y}",
        normal,
    )
    tabela = Table([["Descrição", "Valor"], [descricao, kz(servico.preco_venda)], ["Total", kz(servico.preco_venda)]],
                   colWidths=[125 * mm, 45 * mm])
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), VERDE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 1), (-1, 1), 0.5, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elementos.append(tabela)

    if empresa.get("iban"):
        elementos.append(Spacer(1, 8 * mm))
        elementos.append(Paragraph("PAGAMENTO", rotulo))
        elementos.append(Paragraph(f"IBAN: {empresa['iban']}", normal))

    saida = BytesIO()
    SimpleDocTemplate(saida, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                      title=f"Proforma {numero_proforma(servico, hoje)}").build(elementos)
    return saida.getvalue()
