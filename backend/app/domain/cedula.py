"""Validación de cédula ecuatoriana (POL-KYC-001 Art. 2)."""
from dataclasses import dataclass

COEFFICIENTS = (2, 1, 2, 1, 2, 1, 2, 1, 2)


@dataclass(frozen=True)
class CedulaCheck:
    valid: bool
    reason: str | None = None


def check_digit(first_nine: str) -> int:
    total = 0
    for digit, coef in zip(first_nine, COEFFICIENTS):
        product = int(digit) * coef
        total += product - 9 if product > 9 else product
    return (10 - total % 10) % 10


def validate_cedula(value: str) -> CedulaCheck:
    if len(value) != 10 or not value.isdigit():
        return CedulaCheck(False, "debe tener 10 dígitos numéricos")
    province = int(value[:2])
    if not (1 <= province <= 24 or province == 30):
        return CedulaCheck(False, f"código de provincia {value[:2]} inexistente")
    if int(value[2]) >= 6:
        return CedulaCheck(False, "el tercer dígito no corresponde a persona natural")
    if check_digit(value[:9]) != int(value[9]):
        return CedulaCheck(False, "dígito verificador incorrecto (módulo 10)")
    return CedulaCheck(True)


def mask(value: str) -> str:
    """Enmascarado para logs (POL-KYC-001 Art. 7): primeros 6 dígitos."""
    return value[:6] + "****" if value else value
