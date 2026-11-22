"""Cálculo de la liquidación de sueldo (versión simplificada, Chile)."""
from dataclasses import dataclass, field, asdict


@dataclass
class Payslip:
    rut: str
    nombre: str
    cargo: str
    afp: str
    # Haberes
    sueldo_base: int
    horas_extra: int
    gratificacion: int
    bonos_imponibles: int
    total_imponible: int
    colacion: int
    movilizacion: int
    total_haberes: int
    # Descuentos
    descuento_afp: int
    descuento_salud: int
    seguro_cesantia: int
    total_descuentos: int
    # Resultado
    liquido_a_pagar: int
    # Detalle diario (solo si la planilla lo trae): [{"fecha", "dia", "monto"}, ...]
    dias: list = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop("dias")
        data["dias_trabajados"] = len(self.dias)
        return data


def overtime_pay(base_salary: float, hours: float, config: dict) -> int:
    """Valor de las horas extra: (sueldo / 30 * 28) / (horas semanales * 4) * recargo."""
    hourly = (base_salary / 30 * 28) / (config["weekly_hours"] * 4)
    return round(hourly * config["overtime_multiplier"] * hours)


def legal_gratification(monthly_pay: float, config: dict) -> int:
    """Gratificación legal mensual: 25% de lo devengado, con tope de 4,75 IMM al año."""
    monthly_cap = config["gratification_cap_minimum_wages"] * config["minimum_wage"] / 12
    return round(min(monthly_pay * config["gratification_rate"], monthly_cap))


def calculate_payslip(employee: dict, config: dict) -> Payslip:
    afp = str(employee["afp"]).strip()
    if afp not in config["afp_commissions"]:
        raise ValueError(f"AFP desconocida para {employee['nombre']}: {afp}")

    contract = employee["tipo_contrato"]
    if contract not in config["unemployment_insurance_rate"]:
        valid = ", ".join(config["unemployment_insurance_rate"])
        raise ValueError(
            f"Tipo de contrato desconocido para {employee['nombre']}: '{contract}' (válidos: {valid})"
        )

    days = employee.get("dias")
    if days is not None:
        if not days:
            raise ValueError(f"Sin días trabajados en el período para {employee['nombre']}")
        base = sum(d["monto"] for d in days)  # pago por día: el sueldo sale del detalle diario
    else:
        base = round(employee["sueldo_base"])
    overtime = overtime_pay(base, employee["horas_extra"], config)
    bonuses = round(employee["bonos_imponibles"])
    gratification = legal_gratification(base + overtime + bonuses, config)
    taxable = base + overtime + bonuses + gratification

    lunch = round(employee["colacion"])
    transport = round(employee["movilizacion"])
    total_earnings = taxable + lunch + transport

    afp_rate = config["pension_base_rate"] + config["afp_commissions"][afp]
    afp_deduction = round(taxable * afp_rate)
    health = round(taxable * config["health_rate"])
    unemployment = round(taxable * config["unemployment_insurance_rate"][contract])
    total_deductions = afp_deduction + health + unemployment

    return Payslip(
        rut=employee["rut"],
        nombre=employee["nombre"],
        cargo=employee["cargo"],
        afp=afp,
        sueldo_base=base,
        horas_extra=overtime,
        gratificacion=gratification,
        bonos_imponibles=bonuses,
        total_imponible=taxable,
        colacion=lunch,
        movilizacion=transport,
        total_haberes=total_earnings,
        descuento_afp=afp_deduction,
        descuento_salud=health,
        seguro_cesantia=unemployment,
        total_descuentos=total_deductions,
        liquido_a_pagar=total_earnings - total_deductions,
        dias=list(days or []),
    )
