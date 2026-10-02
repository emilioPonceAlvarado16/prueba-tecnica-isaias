import type { AgentTraceStep } from "@/lib/types";
import { formatDuration, formatTime, nodeLabel } from "@/lib/labels";
import {
  AlertIcon,
  CheckCircleIcon,
  MinusCircleIcon,
  XCircleIcon,
} from "./icons";

const STATUS = {
  ok: { label: "Completado", cls: "text-emerald-600", Icon: CheckCircleIcon },
  failed: { label: "Falló", cls: "text-red-600", Icon: XCircleIcon },
  escalated: { label: "Escalado", cls: "text-orange-500", Icon: AlertIcon },
  skipped: { label: "Omitido", cls: "text-slate-400", Icon: MinusCircleIcon },
} as const;

export default function AgentTimeline({ steps }: { steps: AgentTraceStep[] }) {
  if (!steps.length) {
    return <p className="text-sm text-slate-500">Aún no hay pasos registrados.</p>;
  }
  return (
    <ol className="relative">
      {steps.map((step, i) => {
        const s = STATUS[step.status] ?? STATUS.skipped;
        const duration = formatDuration(step.duration_ms);
        const last = i === steps.length - 1;
        return (
          <li key={`${step.node}-${i}`} className="relative flex gap-3 pb-5 last:pb-0">
            {!last && (
              <span
                aria-hidden="true"
                className="absolute left-[11px] top-7 bottom-0 w-px bg-slate-200"
              />
            )}
            <s.Icon className={`relative h-6 w-6 shrink-0 bg-white ${s.cls}`} />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                <p className="font-medium text-slate-900">
                  {nodeLabel(step.node)}
                  <span className="sr-only"> — {s.label}</span>
                </p>
                <p className="text-xs tabular-nums text-slate-500">
                  {[formatTime(step.started_at), duration].filter(Boolean).join(" · ")}
                </p>
              </div>
              <p className="mt-0.5 flex flex-wrap gap-1.5 text-[11px]">
                <code className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-600">
                  {step.node}
                </code>
                {step.agent && step.agent !== step.node && (
                  <span className="rounded bg-brand-50 px-1.5 py-0.5 text-brand-700 ring-1 ring-brand-100">
                    {step.agent}
                  </span>
                )}
                <span className={`rounded px-1.5 py-0.5 ring-1 ring-current/20 ${s.cls}`}>
                  {s.label}
                </span>
              </p>
              {step.summary && (
                <p className="mt-1 text-sm text-slate-600">{step.summary}</p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
