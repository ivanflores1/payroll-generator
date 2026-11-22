"""Crea data/trabajadores_ejemplo_dias.xlsx: pago por día, trabajan de lunes a jueves.

Uso:  python scripts/crear_planilla_ejemplo.py [AAAA-MM] [valor_dia]
"""
import calendar
import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

PERIODO = sys.argv[1] if len(sys.argv) > 1 else "2026-11"
VALOR_DIA = int(sys.argv[2]) if len(sys.argv) > 2 else 27000
WORK_DAYS = {0, 1, 2, 3}  # lunes a jueves
WEEKDAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

WORKERS = [
    ("12.345.678-5", "Ana Torres", "Analista RR.HH.", "Part Time", "Habitat", 0, 40000, 30000),
    ("15.987.654-3", "Pedro Rojas", "Operario", "Plazo Fijo", "Modelo", 0, 30000, 25000),
    ("18.222.333-K", "Camila Soto", "Supervisora", "Part Time", "Provida", 0, 50000, 40000),
    ("19.444.555-6", "Diego Muñoz", "Bodeguero", "Part Time", "Uno", 0, 30000, 25000),
]

BLUE = PatternFill("solid", fgColor="3873B3")
GREY = PatternFill("solid", fgColor="F0F0F0")
HEAD_FONT = Font(bold=True, color="FFFFFF")


def style_header(ws, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill, cell.font = BLUE, HEAD_FONT
        cell.alignment = Alignment(horizontal="center")
    ws.freeze_panes = "A2"


year, month = map(int, PERIODO.split("-"))
wb = Workbook()

# --- Hoja 1: trabajadores (mismo formato de siempre) ---
ws = wb.active
ws.title = "Trabajadores"
ws.append(["rut", "nombre", "cargo", "tipo_contrato", "afp", "sueldo_base",
           "horas_extra", "bonos_imponibles", "colacion", "movilizacion"])
for i, (rut, nombre, cargo, contrato, afp, bonos, colacion, movil) in enumerate(WORKERS, start=2):
    # sueldo_base = suma del detalle diario (la aplicación lo recalcula desde esa hoja)
    ws.append([rut, nombre, cargo, contrato, afp,
               f"=SUMIFS('Detalle diario'!F:F,'Detalle diario'!A:A,A{i})", 0, bonos, colacion, movil])
    ws.cell(row=i, column=6).number_format = '"$"#,##0'
    for c in (8, 9, 10):
        ws.cell(row=i, column=c).number_format = '"$"#,##0'
style_header(ws, 10)
for col, width in zip("ABCDEFGHIJ", (15, 16, 18, 14, 11, 14, 12, 17, 11, 13)):
    ws.column_dimensions[col].width = width

# --- Hoja 2: detalle por día (todos los días del mes) ---
wd = wb.create_sheet("Detalle diario")
wd.append(["rut", "nombre", "fecha", "dia", "trabajado", "monto"])
row = 2
for rut, nombre, *_ in WORKERS:
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        d = date(year, month, day)
        works = d.weekday() in WORK_DAYS
        wd.append([rut, nombre, d, WEEKDAYS[d.weekday()], "Sí" if works else "No", VALOR_DIA if works else 0])
        wd.cell(row=row, column=3).number_format = "DD-MM-YYYY"
        wd.cell(row=row, column=6).number_format = '"$"#,##0'
        if not works:
            for c in range(1, 7):
                wd.cell(row=row, column=c).fill = GREY
        row += 1
style_header(wd, 6)
for col, width in zip("ABCDEF", (15, 16, 13, 12, 11, 12)):
    wd.column_dimensions[col].width = width
wd.auto_filter.ref = f"A1:{get_column_letter(6)}{row - 1}"

out = Path(__file__).resolve().parent.parent / "data" / "trabajadores_ejemplo_dias.xlsx"
wb.save(out)
print(f"Creado: {out}")

