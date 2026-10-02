"use client";

import type { StartRequest } from "@/lib/types";
import { productLabel } from "@/lib/labels";
import { ChevronIcon } from "./icons";

type Tone = "ok" | "warn" | "bad" | "info" | "err";

type TestUser = {
  n: number;
  name: string;
  cedula: string;
  product: string;
  expected: string;
  tone: Tone;
  submitDirect?: boolean;
};

const TEST_USERS: TestUser[] = [
  { n: 1, name: "Juan Perez", cedula: "1712345675", product: "cuenta_ahorros", expected: "Aprobado", tone: "ok" },
  { n: 2, name: "Juan Perez", cedula: "1712345678", product: "cuenta_ahorros", expected: "Cédula inválida", tone: "bad" },
  { n: 3, name: "Maria Fernanda Loor", cedula: "0918765439", product: "cuenta_ahorros", expected: "Baja confianza (acercarse al banco)", tone: "warn" },
  { n: 4, name: "Luis Ortega", cedula: "0104567896", product: "cuenta_ahorros", expected: "No existe en Registro Civil", tone: "warn" },
  { n: 5, name: "Carlos Andrade", cedula: "1709988776", product: "cuenta_ahorros", expected: "Riesgo alto", tone: "warn" },
  { n: 6, name: "Patricia Salazar", cedula: "1805566773", product: "cuenta_corriente", expected: "PEP: pide información adicional", tone: "info" },
  { n: 7, name: "Mateo Cedeño", cedula: "1302244668", product: "cuenta_ahorros", expected: "Menor de edad", tone: "bad" },
  { n: 8, name: "Rosa Vera", cedula: "1107788992", product: "cuenta_ahorros", expected: "Fallecido en R.C.", tone: "warn" },
  { n: 9, name: "Diego Paredes", cedula: "0603344557", product: "cuenta_ahorros", expected: "Registro Civil no responde", tone: "err" },
  { n: 10, name: "Sofia Mena", cedula: "1711122232", product: "cuenta_ahorros", expected: "Listas de riesgo no responden", tone: "err" },
  { n: 11, name: "Pedro Gomez", cedula: "0922233341", product: "cuenta_ahorros", expected: "Nombre no coincide", tone: "warn" },
  { n: 12, name: "Juan Perez", cedula: "1712345675", product: "cuenta_ahorros", expected: "Duplicado (409) — ejecuta antes el #1", tone: "bad" },
  { n: 13, name: "Juan Perez", cedula: "1712345675", product: "tarjeta_oro", expected: "Producto inválido (400)", tone: "bad", submitDirect: true },
  { n: 14, name: "Valeria Rios", cedula: "1717171712", product: "cuenta_ahorros", expected: "Aprobado, documentos vía RAG", tone: "ok" },
  { n: 15, name: "Camila Herrera", cedula: "1724680242", product: "cuenta_ahorros", expected: "Aprobado, falla creación de usuario", tone: "ok" },
];

const TONE_CLS: Record<Tone, string> = {
  ok: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  warn: "bg-orange-50 text-orange-800 ring-orange-200",
  bad: "bg-red-50 text-red-800 ring-red-200",
  info: "bg-amber-50 text-amber-800 ring-amber-200",
  err: "bg-slate-100 text-slate-700 ring-slate-300",
};

type Props = {
  disabled?: boolean;
  onFill: (req: StartRequest) => void;
  onSubmitDirect: (req: StartRequest) => void;
};

export default function TestUsersPanel({ disabled, onFill, onSubmitDirect }: Props) {
  return (
    <details className="group rounded-2xl border border-dashed border-brand-300 bg-white shadow-sm">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 rounded-2xl px-5 py-4 focus-visible:outline-2 focus-visible:outline-brand-600 [&::-webkit-details-marker]:hidden">
        <span>
          <span className="block font-semibold text-slate-900">Usuarios de prueba</span>
          <span className="block text-sm text-slate-500">
            15 escenarios con resultado conocido para la demo.
          </span>
        </span>
        <ChevronIcon className="h-5 w-5 shrink-0 text-slate-500 transition-transform group-open:rotate-180" />
      </summary>
      <ul className="divide-y divide-slate-100 border-t border-slate-100">
        {TEST_USERS.map((u) => {
          const req: StartRequest = {
            prospect_name: u.name,
            document_id: u.cedula,
            product: u.product,
          };
          return (
            <li key={u.n} className="flex flex-wrap items-center gap-x-3 gap-y-2 px-5 py-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-50 text-xs font-semibold text-brand-800">
                {u.n}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-slate-900">{u.name}</p>
                <p className="text-xs text-slate-500">
                  <span className="font-mono">{u.cedula}</span> · {productLabel(u.product)}
                </p>
              </div>
              <span className={`rounded-md px-2 py-0.5 text-xs ring-1 ${TONE_CLS[u.tone]}`}>
                {u.expected}
              </span>
              <button
                type="button"
                disabled={disabled}
                onClick={() => (u.submitDirect ? onSubmitDirect(req) : onFill(req))}
                className="rounded-md border border-brand-300 px-2.5 py-1 text-xs font-semibold text-brand-700 hover:bg-brand-50 focus-visible:outline-2 focus-visible:outline-brand-600 disabled:opacity-50"
                aria-label={`${u.submitDirect ? "Enviar" : "Usar"} escenario ${u.n}: ${u.expected}`}
              >
                {u.submitDirect ? "Enviar" : "Usar"}
              </button>
            </li>
          );
        })}
      </ul>
      <p className="border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
        «Usar» completa el formulario. El escenario 13 se envía directamente porque el producto
        <code className="mx-1 rounded bg-slate-100 px-1">tarjeta_oro</code>no existe en el catálogo.
      </p>
    </details>
  );
}
