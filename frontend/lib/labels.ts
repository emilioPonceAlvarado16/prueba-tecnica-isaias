const NODE_LABELS: Record<string, string> = {
  validate_input: "Validación de cédula",
  identity_agent: "Agente de identidad",
  risk_agent: "Agente de listas de riesgo",
  request_customer_info: "Solicitud de información al cliente",
  policy_agent: "Agente de políticas",
  decision: "Decisión (reglas)",
  response_agent: "Agente de respuesta",
  provision_user: "Creación de acceso digital",
  finalize: "Cierre del proceso",
};

export const nodeLabel = (node: string) =>
  NODE_LABELS[node] ??
  node.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

const PRODUCT_LABELS: Record<string, string> = {
  cuenta_ahorros: "Cuenta de Ahorros",
  cuenta_corriente: "Cuenta Corriente",
  deposito_plazo: "Depósito a Plazo",
};

export const productLabel = (code?: string | null) =>
  code ? (PRODUCT_LABELS[code] ?? code) : "";

export function formatDuration(ms: number | null) {
  if (ms == null) return null;
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`;
}

export function formatDateTime(iso?: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("es-EC", { dateStyle: "medium", timeStyle: "short" });
}

export function formatTime(iso?: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("es-EC", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}
