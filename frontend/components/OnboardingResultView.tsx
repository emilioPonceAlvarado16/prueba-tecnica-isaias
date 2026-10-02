"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ApiError,
  continueOnboarding,
  getOnboarding,
  startOnboarding,
} from "@/lib/api";
import { formatDateTime, productLabel } from "@/lib/labels";
import { loadRequest, loadResult, saveLastRequest, saveResult } from "@/lib/session";
import type { Answers, OnboardingResult } from "@/lib/types";
import AgentProgress, { CONTINUE_STEPS } from "./AgentProgress";
import AgentTimeline from "./AgentTimeline";
import ConversationLog from "./ConversationLog";
import DocumentsList from "./DocumentsList";
import NextActionCard from "./NextActionCard";
import PendingQuestionsForm from "./PendingQuestionsForm";
import ProvisioningCard from "./ProvisioningCard";
import StatusBanner from "./StatusBanner";
import { AlertIcon, Spinner } from "./icons";

const card = "rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6";

function mergeResult(prev: OnboardingResult | null, next: OnboardingResult): OnboardingResult {
  const sameId = prev?.onboarding_id === next.onboarding_id;
  const keptPassword = sameId ? prev?.provisioning?.temporary_password : null;
  return {
    ...next,
    messages: next.messages ?? (sameId ? prev?.messages : undefined),
    provisioning:
      next.provisioning && !next.provisioning.temporary_password && keptPassword
        ? { ...next.provisioning, temporary_password: keptPassword }
        : next.provisioning,
  };
}

function focusStatus() {
  requestAnimationFrame(() => document.getElementById("estado-titulo")?.focus());
}

export function MessagePanel({
  title,
  text,
}: {
  title: string;
  text: string;
}) {
  return (
    <div className="mx-auto max-w-xl px-4 py-16 text-center sm:px-6">
      <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
      <p className="mt-2 text-slate-600">{text}</p>
      <Link
        href="/"
        className="mt-6 inline-flex rounded-lg bg-brand-700 px-5 py-2.5 font-semibold text-white hover:bg-brand-800"
      >
        Iniciar una nueva solicitud
      </Link>
    </div>
  );
}

export default function OnboardingResultView({ id }: { id: string }) {
  const router = useRouter();
  const [result, setResult] = useState<OnboardingResult | null>(() => loadResult(id));
  const [loadError, setLoadError] = useState<ApiError | null>(null);
  const [refreshing, setRefreshing] = useState(true);

  const [continuing, setContinuing] = useState(false);
  const [continueError, setContinueError] = useState<string | null>(null);
  const [continueFieldErrors, setContinueFieldErrors] = useState<Record<string, string[]>>();

  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);
  const [canRetry] = useState(() => loadRequest(id) !== null);

  useEffect(() => {
    let alive = true;
    getOnboarding(id)
      .then((r) => {
        if (!alive) return;
        applyResult(r, false);
        setLoadError(null);
      })
      .catch((e: unknown) => {
        if (!alive) return;
        setLoadError(
          e instanceof ApiError ? e : new ApiError("server", "No pudimos cargar tu solicitud."),
        );
      })
      .finally(() => alive && setRefreshing(false));
    return () => {
      alive = false;
    };
  }, [id]);

  function applyResult(r: OnboardingResult, focus = true) {
    setResult((prev) => {
      const next = mergeResult(prev ?? loadResult(r.onboarding_id), r);
      saveResult(next);
      return next;
    });
    if (focus) focusStatus();
  }

  async function handleContinue(answers: Answers) {
    setContinuing(true);
    setContinueError(null);
    setContinueFieldErrors(undefined);
    try {
      const r = await continueOnboarding(id, answers);
      applyResult(r);
      getOnboarding(id).then((g) => applyResult(g, false)).catch(() => undefined);
    } catch (e) {
      if (e instanceof ApiError) {
        setContinueError(`${e.message}${e.code ? ` (${e.code})` : ""}`);
        if (e.kind === "validation") setContinueFieldErrors(e.fieldErrors);
        if (e.kind === "conflict" || e.kind === "duplicate") {
          getOnboarding(id).then((g) => applyResult(g, false)).catch(() => undefined);
        }
      } else {
        setContinueError("Ocurrió un error inesperado. Intenta de nuevo.");
      }
    } finally {
      setContinuing(false);
    }
  }

  async function handleRetry() {
    const req = loadRequest(id);
    if (!req) {
      router.push("/");
      return;
    }
    setRetrying(true);
    setRetryError(null);
    try {
      const r = await startOnboarding(req);
      saveResult(r, req);
      saveLastRequest(req);
      if (r.onboarding_id === id) {
        applyResult(r);
        setRetrying(false);
      } else {
        router.push(`/onboarding/?id=${encodeURIComponent(r.onboarding_id)}`);
      }
    } catch (e) {
      setRetrying(false);
      if (e instanceof ApiError && e.kind === "duplicate" && e.onboardingId) {
        router.push(`/onboarding/?id=${encodeURIComponent(e.onboardingId)}`);
        return;
      }
      setRetryError(e instanceof ApiError ? e.message : "No pudimos reintentar tu solicitud.");
    }
  }

  if (loadError?.kind === "not_found") {
    return (
      <MessagePanel
        title="No encontramos esta solicitud"
        text="El enlace puede estar incompleto o la solicitud ya no existe. Verifica el enlace o inicia una nueva solicitud."
      />
    );
  }

  if (!result) {
    if (loadError) {
      return <MessagePanel title="No pudimos cargar tu solicitud" text={loadError.message} />;
    }
    return (
      <div role="status" className="flex items-center justify-center gap-3 py-24 text-slate-600">
        <Spinner className="h-6 w-6 text-brand-600" />
        Cargando tu solicitud…
      </div>
    );
  }

  const awaiting =
    result.status === "AWAITING_CUSTOMER" && result.pending_questions?.length > 0;
  const messages = result.messages ?? [];

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2 text-sm">
        <Link href="/" className="font-medium text-brand-700 hover:underline">
          ← Nueva solicitud
        </Link>
        {refreshing && (
          <span className="inline-flex items-center gap-2 text-slate-500" role="status">
            <Spinner className="h-4 w-4" /> Actualizando…
          </span>
        )}
      </div>

      {loadError && (
        <p
          role="alert"
          className="mb-4 flex gap-2 rounded-lg bg-amber-50 px-4 py-2.5 text-sm text-amber-900 ring-1 ring-amber-200"
        >
          <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />
          No pudimos actualizar el estado; se muestra la última información disponible.{" "}
          {loadError.message}
        </p>
      )}

      <StatusBanner result={result} />

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-6">
          {awaiting && (
            <section id="info-adicional" aria-labelledby="info-titulo" className={card}>
              <h2 id="info-titulo" className="text-lg font-semibold text-slate-900">
                Información adicional
              </h2>
              <p className="mt-1 mb-5 text-sm text-slate-500">
                Completa estos datos para continuar con tu apertura.
              </p>
              {continuing ? (
                <AgentProgress steps={CONTINUE_STEPS} title="Procesando tu información" />
              ) : (
                <PendingQuestionsForm
                  questions={result.pending_questions}
                  submitting={continuing}
                  error={continueError}
                  fieldErrors={continueFieldErrors}
                  onSubmit={handleContinue}
                />
              )}
            </section>
          )}

          <NextActionCard
            result={result}
            canRetry={canRetry}
            retrying={retrying}
            onRetry={handleRetry}
          />
          {retryError && (
            <p role="alert" className="rounded-lg bg-red-50 px-4 py-2.5 text-sm text-red-800 ring-1 ring-red-200">
              {retryError}
            </p>
          )}

          {result.provisioning && <ProvisioningCard provisioning={result.provisioning} />}

          {result.required_documents?.length > 0 && (
            <section aria-labelledby="docs-titulo" className={card}>
              <h2 id="docs-titulo" className="text-lg font-semibold text-slate-900">
                Documentos requeridos
              </h2>
              <p className="mt-1 mb-4 text-sm text-slate-500">
                Según las políticas aplicables a tu producto.
              </p>
              <DocumentsList documents={result.required_documents} />
            </section>
          )}

          {messages.length > 0 && (
            <section aria-labelledby="conv-titulo" className={card}>
              <h2 id="conv-titulo" className="mb-4 text-lg font-semibold text-slate-900">
                Conversación
              </h2>
              <ConversationLog messages={messages} />
            </section>
          )}
        </div>

        <div className="space-y-6">
          <section aria-labelledby="resumen-titulo" className={card}>
            <h2 id="resumen-titulo" className="text-lg font-semibold text-slate-900">
              Resumen de la solicitud
            </h2>
            <dl className="mt-4 grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-2 text-sm">
              {result.prospect_name && (
                <>
                  <dt className="text-slate-500">Solicitante</dt>
                  <dd className="font-medium text-slate-900">{result.prospect_name}</dd>
                </>
              )}
              {result.document_id_masked && (
                <>
                  <dt className="text-slate-500">Cédula</dt>
                  <dd className="font-mono text-slate-900">{result.document_id_masked}</dd>
                </>
              )}
              {result.product && (
                <>
                  <dt className="text-slate-500">Producto</dt>
                  <dd className="text-slate-900">{productLabel(result.product)}</dd>
                </>
              )}
              <dt className="text-slate-500">Fecha</dt>
              <dd className="text-slate-900">{formatDateTime(result.created_at)}</dd>
              <dt className="text-slate-500">N.º solicitud</dt>
              <dd className="break-all font-mono text-xs text-slate-700">{result.onboarding_id}</dd>
            </dl>
          </section>

          <section aria-labelledby="orq-titulo" className={card}>
            <h2 id="orq-titulo" className="text-lg font-semibold text-slate-900">
              Orquestación de agentes
            </h2>
            <p className="mt-1 mb-5 text-sm text-slate-500">
              Pasos ejecutados por el orquestador LangGraph.
            </p>
            <AgentTimeline steps={result.agents_trace ?? []} />
          </section>
        </div>
      </div>
    </div>
  );
}
