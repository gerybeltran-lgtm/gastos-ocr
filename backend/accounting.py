"""Pure accounting rules, kept separate so they can be tested without services."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from fastapi import HTTPException


VALID_ORIGINS = {"Caja Principal", "Casa Comercial", "Cuentas por Recuperar", "Fondos Mixtos"}
VALID_STATUSES = {"Pendiente", "Pendiente de Revisión", "Aprobado", "Rechazado", "Anulado", "Anulada"}
MONEY_QUANTUM = Decimal("0.01")


def money(value: object, field: str = "monto") -> Decimal:
    try:
        result = Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"{field} inválido") from exc
    if not result.is_finite() or result < 0:
        raise HTTPException(status_code=422, detail=f"{field} debe ser un número no negativo")
    return result


def calculate_vat(total: Decimal, transaction_type: str | None) -> Decimal:
    if transaction_type not in {"Factura", "Nota de Crédito"}:
        return Decimal("0.00")
    return (total * Decimal(19) / Decimal(119)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def normalize_ledger(total_value: object, origin: str | None, transaction_type: str | None,
                     cash_value: object = 0, credit_value: object = 0) -> tuple[str, Decimal, Decimal, Decimal]:
    total = money(total_value, "monto_total")
    final_origin = origin or "Caja Principal"
    if final_origin not in VALID_ORIGINS:
        raise HTTPException(status_code=422, detail="origen_fondos inválido")

    if transaction_type == "Sin Respaldo" or final_origin == "Cuentas por Recuperar":
        return "Cuentas por Recuperar", total, Decimal("0.00"), total
    if final_origin == "Casa Comercial":
        return final_origin, Decimal("0.00"), total, total
    if final_origin == "Fondos Mixtos":
        cash = money(cash_value, "monto_caja")
        credit = money(credit_value, "monto_nc")
        if cash + credit != total:
            raise HTTPException(status_code=422, detail="Monto Caja + Monto NC debe coincidir exactamente con Monto Total")
        return final_origin, cash, credit, total
    return "Caja Principal", total, Decimal("0.00"), total


def as_db_number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)
