"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ApiError, FALLBACK_PRODUCTS, getProducts, startOnboarding } from "@/lib/api";
import { validateCedula } from "@/lib/cedula";
import { saveLastRequest, saveResult } from "@/lib/session";
import type { Product, StartRequest } from "@/lib/types";
import AgentProgress from "./AgentProgress";
import TestUsersPanel from "./TestUsersPanel";
import { AlertIcon, CheckCircleIcon } from "./icons";

type FieldErrors = Record<string, string[]>;

const FIELDS = ["prospect_name", "document_id", "product", "email"] as const;

const EMPTY: StartRequest = {
  prospect_name: "",
  document_id: "",
  product: "cuenta_ahorros",
  email: "",
};

const inputCls =
  "mt-1.5 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-slate-900 shadow-sm placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30 aria-[invalid=true]:border-red-500 aria-[invalid=true]:ring-red-500/20";

function FieldError({ id, errors }: { id: string; errors?: string[] }) {
  if (!errors?.length) return null;
  return (
    <p id={id} className="mt-1.5 text-sm text-red-700">
      {errors.join(" ")}
    </p>
  );
}

export default function OnboardingForm() {
  const router = useRouter();
  const [form, setForm] = useState<StartRequest>(EMPTY);
  const [products, setProducts] = useState<Product[]>(FALLBACK_PRODUCTS);
  const [submitting, setSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [duplicate, setDuplicate] = useState<{ message: string; id: string } | null>(null);

  useEffect(() => {
    let alive = true;
    getProducts().then((p) => alive && setProducts(p));
    return () => {
      alive = false;
    };
  }, []);

  const cedulaHint = useMemo(() => {
    const v = form.document_id;
    if (!v) return null;
    if (v.length < 10) return { tone: "muted" as const, text: `${v.length}/10 dígitos` };
    const check = validateCedula(v);
    return check.valid
      ? { tone: "ok" as const, text: "Cédula válida (módulo 10)." }
      : {
          tone: "warn" as const,
          text: `Esta cédula parece no ser válida: ${check.reason} Puedes enviarla igual; el banco la verificará.`,
        };
  }, [form.document_id]);

  const selectedProduct = products.find((p) => p.code === form.product);
  const extraErrors = Object.entries(fieldErrors).filter(
    ([k]) => !(FIELDS as readonly string[]).includes(k),
  );

  function update<K extends keyof StartRequest>(key: K, value: StartRequest[K]) {
    setForm((f) => ({ ...f, [key]: value }));
    if (fieldErrors[key]) {
      setFieldErrors((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
    }
  }

  function focusFirstError(errors: FieldErrors) {
    const first = FIELDS.find((f) => errors[f]);
    if (first) requestAnimationFrame(() => document.getElementById(`f-${first}`)?.focus());
  }

  async function submit(data: StartRequest) {
    const req: StartRequest = {
      prospect_name: data.prospect_name.trim(),
      document_id: data.document_id.trim(),
      product: data.product,
      ...(data.email?.trim() ? { email: data.email.trim() } : {}),
    };

    const local: FieldErrors = {};
    if (!req.prospect_name) local.prospect_name = ["Ingresa tu nombre completo."];
    if (!req.document_id) local.document_id = ["Ingresa tu número de cédula."];
    setFieldErrors(local);
    setGeneralError(null);
    setDuplicate(null);
    if (Object.keys(local).length) {
      focusFirstError(local);
      return;
    }

    setSubmitting(true);
    try {
      const result = await startOnboarding(req);
      saveResult(result, req);
      saveLastRequest(req);
      router.push(`/onboarding/?id=${encodeURIComponent(result.onboarding_id)}`);
    } catch (err) {
      setSubmitting(false);
      if (!(err instanceof ApiError)) {
        setGeneralError("Ocurrió un error inesperado. Intenta de nuevo.");
        return;
      }
      if (err.kind === "validation") {
        const errs = err.fieldErrors ?? {};
        setFieldErrors(errs);
        setGeneralError(`${err.message}${err.code ? ` (${err.code})` : ""}`);
        focusFirstError(errs);
      } else if (err.kind === "duplicate" && err.onboardingId) {
        setDuplicate({ message: err.message, id: err.onboardingId });
      } else {
        setGeneralError(`${err.message}${err.code ? ` (${err.code})` : ""}`);
      }
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    submit(form);
  }

  function fill(req: StartRequest) {
    setForm({ ...EMPTY, ...req, email: req.email ?? "" });
    setFieldErrors({});
    setGeneralError(null);
    setDuplicate(null);
    requestAnimationFrame(() => document.getElementById("f-prospect_name")?.focus());
  }

  function submitDirect(req: StartRequest) {
    setForm({ ...EMPTY, ...req, email: req.email ?? "" });
    submit(req);
  }

  const err = (k: string) => fieldErrors[k];
  const describedBy = (k: string, ...extra: (string | false | null | undefined)[]) =>
    [err(k) && `f-${k}-err`, ...extra].filter(Boolean).join(" ") || undefined;

  return (
    <div className="space-y-6">
      {submitting ? (
        <AgentProgress />
      ) : (
        <form
          onSubmit={handleSubmit}
          noValidate
          aria-labelledby="form-titulo"
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7"
        >
          <h2 id="form-titulo" className="text-lg font-semibold text-slate-900">
            Datos del solicitante
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Los campos marcados con <span className="text-red-600">*</span> son obligatorios.
          </p>

          {duplicate && (
            <div
              role="alert"
              className="mt-5 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-900 ring-1 ring-amber-200"
            >
              <p className="font-medium">{duplicate.message}</p>
              <p className="mt-1 text-xs opacity-80">Código ONB-DUP-409</p>
              <Link
                href={`/onboarding/?id=${encodeURIComponent(duplicate.id)}`}
                className="mt-2 inline-flex font-semibold text-amber-950 underline underline-offset-4"
              >
                Ver mi solicitud existente →
              </Link>
            </div>
          )}

          {generalError && (
            <div
              role="alert"
              className="mt-5 flex gap-2 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800 ring-1 ring-red-200"
            >
              <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <p>{generalError}</p>
                {extraErrors.length > 0 && (
                  <ul className="mt-1 list-disc pl-4">
                    {extraErrors.map(([k, v]) => (
                      <li key={k}>
                        <span className="font-mono text-xs">{k}</span>: {v.join(" ")}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}

          <div className="mt-6 grid gap-5 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label htmlFor="f-prospect_name" className="text-sm font-medium text-slate-800">
                Nombre completo <span className="text-red-600" aria-hidden="true">*</span>
              </label>
              <input
                id="f-prospect_name"
                name="prospect_name"
                autoComplete="name"
                required
                value={form.prospect_name}
                onChange={(e) => update("prospect_name", e.target.value)}
                aria-invalid={!!err("prospect_name")}
                aria-describedby={describedBy("prospect_name")}
                placeholder="Como consta en tu cédula"
                className={inputCls}
              />
              <FieldError id="f-prospect_name-err" errors={err("prospect_name")} />
            </div>

            <div>
              <label htmlFor="f-document_id" className="text-sm font-medium text-slate-800">
                Número de cédula <span className="text-red-600" aria-hidden="true">*</span>
              </label>
              <input
                id="f-document_id"
                name="document_id"
                inputMode="numeric"
                autoComplete="off"
                required
                maxLength={10}
                value={form.document_id}
                onChange={(e) => update("document_id", e.target.value.replace(/\D/g, "").slice(0, 10))}
                aria-invalid={!!err("document_id")}
                aria-describedby={describedBy("document_id", cedulaHint && "f-document_id-hint")}
                placeholder="10 dígitos"
                className={`${inputCls} font-mono tracking-wider`}
              />
              {cedulaHint && (
                <p
                  id="f-document_id-hint"
                  aria-live="polite"
                  className={`mt-1.5 flex gap-1.5 text-xs ${
                    cedulaHint.tone === "ok"
                      ? "text-emerald-700"
                      : cedulaHint.tone === "warn"
                        ? "text-amber-700"
                        : "text-slate-500"
                  }`}
                >
                  {cedulaHint.tone === "ok" && <CheckCircleIcon className="h-4 w-4 shrink-0" />}
                  {cedulaHint.tone === "warn" && <AlertIcon className="h-4 w-4 shrink-0" />}
                  {cedulaHint.text}
                </p>
              )}
              <FieldError id="f-document_id-err" errors={err("document_id")} />
            </div>

            <div>
              <label htmlFor="f-product" className="text-sm font-medium text-slate-800">
                Producto <span className="text-red-600" aria-hidden="true">*</span>
              </label>
              <select
                id="f-product"
                name="product"
                value={form.product}
                onChange={(e) => update("product", e.target.value)}
                aria-invalid={!!err("product")}
                aria-describedby={describedBy("product", selectedProduct && "f-product-desc")}
                className={inputCls}
              >
                {products.map((p) => (
                  <option key={p.code} value={p.code}>
                    {p.name}
                  </option>
                ))}
                {!selectedProduct && (
                  <option value={form.product}>{form.product} (no disponible)</option>
                )}
              </select>
              {selectedProduct?.description && (
                <p id="f-product-desc" className="mt-1.5 text-xs text-slate-500">
                  {selectedProduct.description}
                </p>
              )}
              <FieldError id="f-product-err" errors={err("product")} />
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="f-email" className="text-sm font-medium text-slate-800">
                Correo electrónico <span className="font-normal text-slate-500">(opcional)</span>
              </label>
              <input
                id="f-email"
                name="email"
                type="email"
                autoComplete="email"
                value={form.email ?? ""}
                onChange={(e) => update("email", e.target.value)}
                aria-invalid={!!err("email")}
                aria-describedby={describedBy("email", "f-email-desc")}
                placeholder="tucorreo@ejemplo.com"
                className={inputCls}
              />
              <p id="f-email-desc" className="mt-1.5 text-xs text-slate-500">
                Si lo ingresas, te enviaremos tu acceso a la banca en línea.
              </p>
              <FieldError id="f-email-err" errors={err("email")} />
            </div>
          </div>

          <button
            type="submit"
            className="mt-7 inline-flex w-full items-center justify-center rounded-lg bg-brand-700 px-5 py-3 font-semibold text-white shadow-sm transition hover:bg-brand-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 sm:w-auto"
          >
            Iniciar mi apertura
          </button>
          <p className="mt-3 text-xs text-slate-500">
            Al continuar autorizas el tratamiento de tus datos conforme a la Ley Orgánica de
            Protección de Datos Personales.
          </p>
        </form>
      )}

      <TestUsersPanel disabled={submitting} onFill={fill} onSubmitDirect={submitDirect} />
    </div>
  );
}
