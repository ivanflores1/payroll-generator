"""Generación de la liquidación en PDF."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .calculator import Payslip


def clp(amount: int) -> str:
    """Formatea un monto en pesos chilenos: 1234567 -> $1.234.567"""
    return "$" + f"{amount:,}".replace(",", ".")


def build_pdf(payslip: Payslip, period: str, company: str, output_dir: str | Path) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_rut = str(payslip.rut).replace(".", "").replace("-", "")
    path = output_dir / f"liquidacion_{safe_rut}_{period}.pdf"

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4, title=f"Liquidación {payslip.nombre} {period}")

    header = [
        Paragraph(f"<b>{company}</b>", styles["Title"]),
        Paragraph(f"Liquidación de sueldo — período {period}", styles["Heading3"]),
        Spacer(1, 8),
        Paragraph(
            f"<b>Trabajador:</b> {payslip.nombre} &nbsp;&nbsp; <b>RUT:</b> {payslip.rut}<br/>"
            f"<b>Cargo:</b> {payslip.cargo} &nbsp;&nbsp; <b>AFP:</b> {payslip.afp}",
            styles["Normal"],
        ),
        Spacer(1, 12),
    ]

    rows = [
        ["HABERES", ""],
        ["Sueldo base", clp(payslip.sueldo_base)],
        ["Horas extra", clp(payslip.horas_extra)],
        ["Gratificación legal", clp(payslip.gratificacion)],
        ["Bonos imponibles", clp(payslip.bonos_imponibles)],
        ["Total imponible", clp(payslip.total_imponible)],
        ["Colación", clp(payslip.colacion)],
        ["Movilización", clp(payslip.movilizacion)],
        ["Total haberes", clp(payslip.total_haberes)],
        ["DESCUENTOS", ""],
        [f"AFP {payslip.afp}", clp(payslip.descuento_afp)],
        ["Salud (7%)", clp(payslip.descuento_salud)],
        ["Seguro de cesantía", clp(payslip.seguro_cesantia)],
        ["Total descuentos", clp(payslip.total_descuentos)],
        ["LÍQUIDO A PAGAR", clp(payslip.liquido_a_pagar)],
    ]

    blue = colors.HexColor("#3873b3")
    table = Table(rows, colWidths=[300, 150])
    table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("BACKGROUND", (0, 0), (-1, 0), blue),
        ("BACKGROUND", (0, 9), (-1, 9), blue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("TEXTCOLOR", (0, 9), (-1, 9), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 9), (-1, 9), "Helvetica-Bold"),
        ("FONTNAME", (0, 5), (-1, 5), "Helvetica-Bold"),
        ("FONTNAME", (0, 8), (-1, 8), "Helvetica-Bold"),
        ("FONTNAME", (0, 13), (-1, 13), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f0fa")),
        ("FONTSIZE", (0, -1), (-1, -1), 12),
    ]))

    story = header + [table]

    if payslip.dias:
        detail_rows = [["Fecha", "Día", "Monto"]]
        detail_rows += [[d["fecha"].strftime("%d-%m-%Y"), d["dia"], clp(d["monto"])] for d in payslip.dias]
        detail_rows.append([f"Total ({len(payslip.dias)} días)", "", clp(sum(d["monto"] for d in payslip.dias))])
        detail = Table(detail_rows, colWidths=[150, 150, 150], repeatRows=1)
        detail.setStyle(TableStyle([
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("BACKGROUND", (0, 0), (-1, 0), blue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f0fa")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story += [Spacer(1, 14), KeepTogether([Paragraph("<b>Detalle por día trabajado</b>", styles["Heading4"]), detail])]

    doc.build(story)
    return path
