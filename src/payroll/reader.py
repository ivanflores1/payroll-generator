"""Lectura y validación de la planilla de trabajadores."""
import re
import unicodedata
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    "rut",
    "nombre",
    "cargo",
    "tipo_contrato",
    "afp",
    "sueldo_base",
    "horas_extra",
    "bonos_imponibles",
    "colacion",
    "movilizacion",
]

NUMERIC_COLUMNS = ["sueldo_base", "horas_extra", "bonos_imponibles", "colacion", "movilizacion"]


class InvalidSpreadsheetError(Exception):
    """La planilla no tiene el formato esperado."""


_PART_TIME = {"parcial", "part_time", "parttime", "jornada_parcial", "contrato_parcial",
              "contrato_part_time", "part_time_indefinido", "parcial_indefinido"}


def normalize_contract(value) -> str:
    """'Part Time', 'Contrato Parcial', 'Plazo Fijo'... -> clave usada en config.json."""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    text = re.sub(r"[\s\-]+", "_", text.strip().lower())
    return "part_time" if text in _PART_TIME else text


DAILY_SHEET = "Detalle diario"
DAILY_COLUMNS = ["rut", "fecha", "trabajado", "monto"]
WEEKDAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
_YES = {"1", "1.0", "si", "sí", "s", "x", "true", "yes"}


def _read_daily(xls: pd.ExcelFile, periodo: str | None) -> dict[str, list[dict]] | None:
    """Lee la hoja 'Detalle diario' (si existe): días trabajados por RUT, filtrados por período."""
    sheet = next((s for s in xls.sheet_names if s.strip().lower() == DAILY_SHEET.lower()), None)
    if sheet is None:
        return None

    df = xls.parse(sheet)
    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = [c for c in DAILY_COLUMNS if c not in df.columns]
    if missing:
        raise InvalidSpreadsheetError(f"En '{DAILY_SHEET}' faltan columnas: {', '.join(missing)}")

    df = df.dropna(subset=["rut", "fecha"])
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["fecha"])
    if periodo:
        df = df[df["fecha"].dt.strftime("%Y-%m") == periodo]
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)
    worked = df["trabajado"].astype(str).str.strip().str.lower().isin(_YES)
    df = df[worked & (df["monto"] > 0)].sort_values("fecha")

    days: dict[str, list[dict]] = {}
    for row in df.itertuples():
        days.setdefault(str(row.rut).strip(), []).append(
            {"fecha": row.fecha.date(), "dia": WEEKDAYS[row.fecha.weekday()], "monto": round(row.monto)}
        )
    return days


def read_employees(path: str | Path, periodo: str | None = None) -> list[dict]:
    """Lee la planilla y devuelve una lista de trabajadores (un dict por fila).

    Si el libro tiene la hoja 'Detalle diario', cada trabajador incluye la clave
    'dias' con los días trabajados del período (y el sueldo se calcula con ellos).
    """
    xls = pd.ExcelFile(path)
    df = xls.parse(0)
    df.columns = [str(c).strip().lower() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise InvalidSpreadsheetError(f"Faltan columnas: {', '.join(missing)}")

    df = df.dropna(subset=["rut", "nombre"])
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["tipo_contrato"] = df["tipo_contrato"].map(normalize_contract)
    employees = df[REQUIRED_COLUMNS].to_dict(orient="records")

    daily = _read_daily(xls, periodo)
    if daily is not None:
        for emp in employees:
            emp["dias"] = daily.get(str(emp["rut"]).strip(), [])
    return employees
