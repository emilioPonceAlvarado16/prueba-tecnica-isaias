import type {
  Answers,
  OnboardingResult,
  Product,
  StartRequest,
} from "./types";

export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010"
).replace(/\/+$/, "");

export const FALLBACK_PRODUCTS: Product[] = [
  {
    code: "cuenta_ahorros",
    name: "Cuenta de Ahorros",
    description: "Ahorra de forma segura y gestiona tu dinero en línea.",
  },
  {
    code: "cuenta_corriente",
    name: "Cuenta Corriente",
    description: "Maneja tus pagos y cheques con firma digital.",
  },
  {
    code: "deposito_plazo",
    name: "Depósito a Plazo",
    description: "Haz crecer tus ahorros con una tasa fija.",
  },
];

export type ApiErrorKind =
  | "validation"
  | "duplicate"
  | "not_found"
  | "conflict"
  | "network"
  | "server";

export class ApiError extends Error {
  kind: ApiErrorKind;
  status: number;
  code?: string;
  fieldErrors?: Record<string, string[]>;
  onboardingId?: string;

  constructor(
    kind: ApiErrorKind,
    message: string,
    opts: {
      status?: number;
      code?: string;
      fieldErrors?: Record<string, string[]>;
      onboardingId?: string;
    } = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = opts.status ?? 0;
    this.code = opts.code;
    this.fieldErrors = opts.fieldErrors;
    this.onboardingId = opts.onboardingId;
  }
}

const NETWORK_MESSAGE =
  "No pudimos conectarnos con el banco. Revisa tu conexión a internet e intenta de nuevo en unos minutos.";

type ErrorBody = {
  code?: string;
  message?: string;
  errors?: Record<string, string[] | string | Record<string, unknown>>;
  onboarding_id?: string;
};

function isOnboardingResult(body: unknown): body is OnboardingResult {
  return (
    typeof body === "object" &&
    body !== null &&
    "onboarding_id" in body &&
    "status" in body
  );
}

function normalizeFieldErrors(
  errors: ErrorBody["errors"],
): Record<string, string[]> | undefined {
  if (!errors || typeof errors !== "object") return undefined;
  const out: Record<string, string[]> = {};
  for (const [field, value] of Object.entries(errors)) {
    if (Array.isArray(value)) out[field] = value.map(String);
    else if (typeof value === "string") out[field] = [value];
    else if (value && typeof value === "object")
      out[field] = Object.values(value).flat().map(String);
  }
  return out;
}

async function request(path: string, init?: RequestInit) {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError("network", NETWORK_MESSAGE);
  }
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  return { res, body };
}

function toApiError(status: number, body: unknown): ApiError {
  const b = (body ?? {}) as ErrorBody;
  const message =
    b.message ||
    (status >= 500
      ? "Tuvimos un problema procesando tu solicitud. Intenta de nuevo en unos minutos."
      : "No pudimos procesar tu solicitud.");
  const opts = { status, code: b.code };
  switch (status) {
    case 400:
    case 422:
      return new ApiError("validation", message, {
        ...opts,
        fieldErrors: normalizeFieldErrors(b.errors),
      });
    case 404:
      return new ApiError(
        "not_found",
        b.message || "No encontramos la solicitud indicada.",
        opts,
      );
    case 409:
      return new ApiError(b.onboarding_id ? "duplicate" : "conflict", message, {
        ...opts,
        onboardingId: b.onboarding_id,
      });
    default:
      return new ApiError("server", message, opts);
  }
}

export async function getProducts(): Promise<Product[]> {
  try {
    const { res, body } = await request("/api/v1/products");
    if (res.ok && Array.isArray(body) && body.length > 0) {
      return body as Product[];
    }
  } catch {
    /* fall through */
  }
  return FALLBACK_PRODUCTS;
}

export async function startOnboarding(
  data: StartRequest,
): Promise<OnboardingResult> {
  const { res, body } = await request("/api/v1/onboarding/start", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if ((res.ok || res.status === 503) && isOnboardingResult(body)) return body;
  throw toApiError(res.status, body);
}

export async function getOnboarding(id: string): Promise<OnboardingResult> {
  const { res, body } = await request(
    `/api/v1/onboarding/${encodeURIComponent(id)}`,
  );
  if (res.ok && isOnboardingResult(body)) return body;
  throw toApiError(res.status, body);
}

export async function continueOnboarding(
  id: string,
  answers: Answers,
): Promise<OnboardingResult> {
  const { res, body } = await request(
    `/api/v1/onboarding/${encodeURIComponent(id)}/continue`,
    { method: "POST", body: JSON.stringify({ answers }) },
  );
  if ((res.ok || res.status === 503) && isOnboardingResult(body)) return body;
  throw toApiError(res.status, body);
}
