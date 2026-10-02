"use client";

import { useEffect, useState } from "react";
import { CheckCircleIcon, Spinner } from "./icons";

export const START_STEPS = [
  "Validando cédula",
  "Agente de identidad",
  "Agente de listas de riesgo",
  "Agente de políticas",
  "Generando respuesta",
];

export const CONTINUE_STEPS = [
  "Registrando tu información",
  "Agente de políticas",
  "Generando respuesta",
];

type Props = {
  steps?: string[];
  title?: string;
  intervalMs?: number;
};

export default function AgentProgress({
  steps = START_STEPS,
  title = "Estamos revisando tu solicitud",
  intervalMs = 2200,
}: Props) {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const t = setInterval(
      () => setActive((a) => Math.min(a + 1, steps.length - 1)),
      intervalMs,
    );
    return () => clearInterval(t);
  }, [steps.length, intervalMs]);

  return (
    <div
      role="status"
      aria-live="polite"
      className="rounded-2xl border border-brand-100 bg-white p-6 shadow-sm"
    >
      <p className="font-semibold text-slate-900">{title}</p>
      <p className="mt-1 text-sm text-slate-500">
        Nuestros agentes trabajan en tu solicitud. Esto puede tardar hasta 15 segundos.
      </p>
      <ol className="mt-5 space-y-3">
        {steps.slice(0, active + 1).map((label, i) => {
          const done = i < active;
          return (
            <li key={label} className="animate-step-in flex items-center gap-3 text-sm">
              {done ? (
                <CheckCircleIcon className="h-5 w-5 text-emerald-600" />
              ) : (
                <Spinner className="h-5 w-5 text-brand-600" />
              )}
              <span className={done ? "text-slate-500" : "font-medium text-slate-900"}>
                {label}
                {!done && "…"}
              </span>
            </li>
          );
        })}
      </ol>
      <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-brand-500 transition-all duration-700"
          style={{ width: `${((active + 1) / steps.length) * 92}%` }}
        />
      </div>
    </div>
  );
}
