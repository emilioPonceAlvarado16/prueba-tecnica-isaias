import Link from "next/link";
import type { OnboardingResult } from "@/lib/types";
import { BuildingIcon, Spinner } from "./icons";

type Props = {
  result: OnboardingResult;
  canRetry: boolean;
  retrying: boolean;
  onRetry: () => void;
};

const btn =
  "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold shadow-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600";
const primary = `${btn} bg-brand-700 text-white hover:bg-brand-800 disabled:opacity-70`;

export default function NextActionCard({ result, canRetry, retrying, onRetry }: Props) {
  const { type, detail } = result.next_action ?? { type: "NONE" };
  const username = result.provisioning?.username;

  let action: React.ReactNode = null;
  switch (type) {
    case "LOGIN":
      action = (
        <Link
          href={username ? `/login/?u=${encodeURIComponent(username)}` : "/login/"}
          className={primary}
        >
          Ingresar a la banca en línea
        </Link>
      );
      break;
    case "VISIT_BRANCH":
      action = (
        <div className="flex gap-3 rounded-xl bg-brand-50 p-4 text-sm text-brand-950 ring-1 ring-brand-100">
          <BuildingIcon className="h-6 w-6 shrink-0 text-brand-700" />
          <div>
            <p className="font-semibold">Encuentra tu agencia</p>
            <p className="mt-1 text-brand-900">
              Acércate a cualquier agencia de Banco Andino Demo con tu cédula original. Atendemos de
              lunes a viernes de 09:00 a 17:00 y sábados de 09:00 a 13:00.
            </p>
            <p className="mt-1 text-brand-900">Línea de atención: 1800-ANDINO (demo).</p>
          </div>
        </div>
      );
      break;
    case "RETRY_LATER":
      action = canRetry ? (
        <button type="button" onClick={onRetry} disabled={retrying} className={primary}>
          {retrying && <Spinner className="h-4 w-4" />}
          {retrying ? "Reintentando…" : "Reintentar ahora"}
        </button>
      ) : (
        <Link href="/" className={primary}>
          Volver al formulario
        </Link>
      );
      break;
    case "FIX_INPUT":
      action = (
        <Link href="/" className={primary}>
          Corregir mis datos
        </Link>
      );
      break;
  }

  if (!result.proposed_solution && !detail && !action) return null;

  return (
    <section
      aria-labelledby="siguiente-titulo"
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
    >
      <h2 id="siguiente-titulo" className="text-lg font-semibold text-slate-900">
        Tu siguiente paso
      </h2>
      {result.proposed_solution && (
        <p className="mt-2 text-slate-700">{result.proposed_solution}</p>
      )}
      {detail && <p className="mt-2 text-sm text-slate-500">{detail}</p>}
      {action && <div className="mt-4">{action}</div>}
    </section>
  );
}
