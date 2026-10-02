export type CedulaCheck =
  | { valid: true }
  | { valid: false; reason: string };

const COEFFICIENTS = [2, 1, 2, 1, 2, 1, 2, 1, 2];

export function validateCedula(value: string): CedulaCheck {
  if (!/^\d{10}$/.test(value)) {
    return { valid: false, reason: "Debe tener exactamente 10 dígitos." };
  }
  const province = Number(value.slice(0, 2));
  if (!((province >= 1 && province <= 24) || province === 30)) {
    return {
      valid: false,
      reason: "Los dos primeros dígitos no corresponden a una provincia válida.",
    };
  }
  const digits = value.split("").map(Number);
  if (digits[2] >= 6) {
    return { valid: false, reason: "El tercer dígito debe ser menor a 6." };
  }
  const sum = COEFFICIENTS.reduce((acc, coef, i) => {
    const p = digits[i] * coef;
    return acc + (p > 9 ? p - 9 : p);
  }, 0);
  const check = (10 - (sum % 10)) % 10;
  if (check !== digits[9]) {
    return { valid: false, reason: "El dígito verificador no coincide." };
  }
  return { valid: true };
}
