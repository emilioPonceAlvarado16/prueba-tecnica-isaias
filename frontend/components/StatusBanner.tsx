import type { OnboardingResult, OnboardingStatus } from "@/lib/types";
import {
  AlertIcon,
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
} from "./icons";

type Tone = {
  label: string;
  box: string;
  icon: string;
  Icon: (p: { className?: string }) => React.JSX.Element;
};

const TONES: Record<OnboardingStatus, Tone> = {
  APPROVED: {
    label: "¡Solicitud aprobada!",
    box: "border-emerald-200 bg-emerald-50 text-emerald-950",
    icon: "bg-emerald-600 text-white",
    Icon: CheckCircleIcon,
  },
  APPROVED_PENDING_PROVISIONING: {
    label: "Solicitud aprobada · acceso digital en proceso",
    box: "border-emerald-200 bg-emerald-50 text-emerald-950",
    icon: "bg-emerald-600 text-white",
    Icon: CheckCircleIcon,
  },
  AWAITING_CUSTOMER: {
    label: "Necesitamos un poco más de información",
    box: "border-amber-200 bg-amber-50 text-amber-950",
    icon: "bg-amber-500 text-white",
    Icon: ClockIcon,
  },
  ESCALATED: {
    label: "Tu solicitud requiere atención en agencia",
    box: "border-orange-200 bg-orange-50 text-orange-950",
    icon: "bg-orange-500 text-white",
    Icon: AlertIcon,
  },
  REJECTED: {
    label: "No pudimos aprobar tu solicitud",
    box: "border-red-200 bg-red-50 text-red-950",
    icon: "bg-red-600 text-white",
    Icon: XCircleIcon,
  },
  ERROR: {
    label: "Servicio temporalmente no disponible",
    box: "border-slate-300 bg-slate-100 text-slate-900",
    icon: "bg-red-700 text-white",
    Icon: AlertIcon,
  },
  RECEIVED: {
    label: "Solicitud recibida",
    box: "border-brand-200 bg-brand-50 text-brand-950",
    icon: "bg-brand-600 text-white",
    Icon: ClockIcon,
  },
  IN_PROGRESS: {
    label: "Estamos procesando tu solicitud",
    box: "border-brand-200 bg-brand-50 text-brand-950",
    icon: "bg-brand-600 text-white",
    Icon: ClockIcon,
  },
};

export default function StatusBanner({ result }: { result: OnboardingResult }) {
  const tone = TONES[result.status] ?? TONES.IN_PROGRESS;
  const { Icon } = tone;
  const codes = [result.reason_code, result.error?.code].filter(
    (c, i, arr): c is string => !!c && arr.indexOf(c) === i,
  );

  return (
    <section
      aria-labelledby="estado-titulo"
      className={`rounded-2xl border p-5 sm:p-6 ${tone.box}`}
    >
      <div className="flex items-start gap-4">
        <span
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full ${tone.icon}`}
        >
          <Icon className="h-6 w-6" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-wider opacity-70">
            Estado: {result.status}
          </p>
          <h1 id="estado-titulo" tabIndex={-1} className="mt-0.5 text-xl font-semibold sm:text-2xl">
            {tone.label}
          </h1>
          {result.customer_message && (
            <p className="mt-3 whitespace-pre-line text-base leading-relaxed sm:text-lg">
              {result.customer_message}
            </p>
          )}
          {result.error?.message && result.error.message !== result.customer_message && (
            <p className="mt-2 text-sm opacity-80">{result.error.message}</p>
          )}
          {codes.length > 0 && (
            <p className="mt-3 flex flex-wrap gap-2 text-xs">
              {codes.map((c) => (
                <span
                  key={c}
                  className="rounded-md bg-white/70 px-2 py-0.5 font-mono ring-1 ring-black/10"
                >
                  Código {c}
                </span>
              ))}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
