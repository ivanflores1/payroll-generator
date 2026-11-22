"""Punto de entrada: python -m payroll.main data/trabajadores_ejemplo.xlsx --periodo 2026-11"""
import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .calculator import Payslip, calculate_payslip
from .pdf import build_pdf
from .reader import read_employees


def default_config_path() -> Path:
    """config.json junto al ejecutable (editable); si no existe, el que va empaquetado."""
    if getattr(sys, "frozen", False):
        external = Path(sys.executable).parent / "config.json"
        if external.exists():
            return external
        return Path(sys._MEIPASS) / "config.json"
    return Path("config.json")


@dataclass
class Result:
    summary_path: Path
    payslips: list[Payslip]
    errors: list[str]

    @property
    def count(self) -> int:
        return len(self.payslips)


def generate(excel, periodo: str, salida, config_path=None) -> Result:
    """Genera los PDFs y el resumen (con hoja 'Detalle diario' si la planilla lo trae)."""
    config_path = Path(config_path) if config_path else default_config_path()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    employees = read_employees(excel, periodo)

    payslips, errors = [], []
    for employee in employees:
        try:
            payslip = calculate_payslip(employee, config)
        except ValueError as e:
            errors.append(str(e))
            continue
        build_pdf(payslip, periodo, config["company_name"], salida)
        payslips.append(payslip)

    Path(salida).mkdir(parents=True, exist_ok=True)
    summary_path = Path(salida) / f"resumen_{periodo}.xlsx"
    with pd.ExcelWriter(summary_path) as writer:
        pd.DataFrame([p.to_dict() for p in payslips]).to_excel(writer, sheet_name="Resumen", index=False)
        daily = [
            {"rut": p.rut, "nombre": p.nombre, "fecha": d["fecha"], "dia": d["dia"], "monto": d["monto"]}
            for p in payslips for d in p.dias
        ]
        if daily:
            pd.DataFrame(daily).to_excel(writer, sheet_name="Detalle diario", index=False)
    return Result(summary_path, payslips, errors)


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera liquidaciones de sueldo en PDF desde un Excel.")
    parser.add_argument("excel", help="Planilla con los datos de los trabajadores")
    parser.add_argument("--periodo", required=True, help="Período, por ejemplo 2026-11")
    parser.add_argument("--config", default=None, help="Archivo de parámetros")
    parser.add_argument("--salida", default="output", help="Carpeta de salida")
    args = parser.parse_args()

    result = generate(args.excel, args.periodo, args.salida, args.config)
    print(f"✔ {result.count} liquidaciones generadas en '{args.salida}/'")
    print(f"✔ Resumen: {result.summary_path}")
    for err in result.errors:
        print(f"✘ {err}")


if __name__ == "__main__":
    main()
