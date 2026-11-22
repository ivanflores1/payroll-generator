import json
from pathlib import Path

import pytest

from payroll.calculator import calculate_payslip, legal_gratification, overtime_pay

CONFIG = json.loads((Path(__file__).parent.parent / "config.json").read_text(encoding="utf-8"))


def employee(**overrides):
    data = {
        "rut": "11.111.111-1",
        "nombre": "Test",
        "cargo": "Operario",
        "tipo_contrato": "indefinido",
        "afp": "Modelo",
        "sueldo_base": 600000,
        "horas_extra": 0,
        "bonos_imponibles": 0,
        "colacion": 0,
        "movilizacion": 0,
    }
    data.update(overrides)
    return data


def test_overtime_zero_hours_is_zero():
    assert overtime_pay(600000, 0, CONFIG) == 0


def test_overtime_formula():
    expected = round((600000 / 30 * 28) / (CONFIG["weekly_hours"] * 4) * 1.5 * 10)
    assert overtime_pay(600000, 10, CONFIG) == expected


def test_gratification_is_capped():
    cap = round(CONFIG["gratification_cap_minimum_wages"] * CONFIG["minimum_wage"] / 12)
    assert legal_gratification(5_000_000, CONFIG) == cap


def test_gratification_below_cap_is_25_percent():
    assert legal_gratification(400000, CONFIG) == 100000


def test_fixed_term_contract_has_no_unemployment_insurance():
    p = calculate_payslip(employee(tipo_contrato="plazo_fijo"), CONFIG)
    assert p.seguro_cesantia == 0


def test_net_pay_adds_up():
    p = calculate_payslip(employee(colacion=50000, movilizacion=40000), CONFIG)
    assert p.total_haberes == p.total_imponible + 90000
    assert p.liquido_a_pagar == p.total_haberes - p.total_descuentos


def test_daily_pay_sums_days_instead_of_base_salary():
    days = [{"fecha": None, "dia": "Lunes", "monto": 27000}] * 17
    p = calculate_payslip(employee(sueldo_base=0, dias=days), CONFIG)
    assert p.sueldo_base == 459000
    assert len(p.dias) == 17
    assert p.to_dict()["dias_trabajados"] == 17
    assert "dias" not in p.to_dict()


def test_daily_mode_without_days_raises():
    with pytest.raises(ValueError):
        calculate_payslip(employee(dias=[]), CONFIG)


@pytest.mark.parametrize("text", ["Part Time", "part-time", "PARCIAL", "Contrato Parcial", "Jornada Parcial", " Part time "])
def test_part_time_spellings_are_recognised(text):
    from payroll.reader import normalize_contract
    assert normalize_contract(text) == "part_time"
    p = calculate_payslip(employee(tipo_contrato=normalize_contract(text)), CONFIG)
    assert p.seguro_cesantia == round(p.total_imponible * 0.006)


def test_existing_contract_types_unchanged():
    from payroll.reader import normalize_contract
    assert normalize_contract("Plazo Fijo") == "plazo_fijo"
    assert normalize_contract("Indefinido") == "indefinido"


def test_unknown_afp_raises():
    with pytest.raises(ValueError):
        calculate_payslip(employee(afp="Inexistente"), CONFIG)
