"use client";

import Link from "next/link";
import { useState } from "react";
import type { Provisioning } from "@/lib/types";
import { AlertIcon, CopyIcon, KeyIcon } from "./icons";

function CopyButton({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }
  return (
    <button
      type="button"
      onClick={copy}
      className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-brand-600"
      aria-label={`Copiar ${label}`}
    >
      <CopyIcon className="h-3.5 w-3.5" />
      <span aria-live="polite">{copied ? "¡Copiado!" : "Copiar"}</span>
    </button>
  );
}

export default function ProvisioningCard({
  provisioning,
}: {
  provisioning: Provisioning;
}) {
  const [visible, setVisible] = useState(false);
  const ok = provisioning.status === "created";
  const password = provisioning.temporary_password;

  return (
    <section
      aria-labelledby="acceso-titulo"
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
    >
      <div className="flex items-center gap-2">
        <KeyIcon className="h-5 w-5 text-brand-600" />
        <h2 id="acceso-titulo" className="text-lg font-semibold text-slate-900">
          Tu acceso a la banca en línea
        </h2>
      </div>
      <p className="mt-1 text-xs text-slate-500">
        Proveedor: {provisioning.provider === "cognito" ? "Amazon Cognito" : "Simulado (local)"} ·
        Estado: {ok ? "creado" : "falló"}
      </p>

      {!ok ? (
        <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900 ring-1 ring-amber-200">
          No pudimos crear tu acceso digital todavía. Estará listo en breve.
        </p>
      ) : (
        <dl className="mt-4 space-y-3">
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Usuario</dt>
            <dd className="mt-1 flex items-center gap-2">
              <code className="rounded-md bg-slate-100 px-2.5 py-1.5 font-mono text-slate-900">
                {provisioning.username}
              </code>
              <CopyButton value={provisioning.username} label="usuario" />
            </dd>
          </div>
          {password && (
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Contraseña temporal
              </dt>
              <dd className="mt-1 flex flex-wrap items-center gap-2">
                <code className="rounded-md bg-slate-100 px-2.5 py-1.5 font-mono text-slate-900">
                  {visible ? password : "•".repeat(Math.max(password.length, 8))}
                </code>
                <button
                  type="button"
                  onClick={() => setVisible((v) => !v)}
                  className="rounded-md px-2 py-1.5 text-xs font-medium text-brand-700 hover:bg-brand-50 focus-visible:outline-2 focus-visible:outline-brand-600"
                  aria-pressed={visible}
                >
                  {visible ? "Ocultar" : "Mostrar"}
                </button>
                <CopyButton value={password} label="contraseña temporal" />
              </dd>
            </div>
          )}
        </dl>
      )}

      {password && (
        <p className="mt-4 flex gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900 ring-1 ring-amber-200">
          <AlertIcon className="h-4 w-4 shrink-0" />
          Solo visible en modo demo. En producción la contraseña temporal se envía por un canal seguro
          y deberás cambiarla en tu primer ingreso.
        </p>
      )}

      {ok && (
        <Link
          href={`/login/?u=${encodeURIComponent(provisioning.username)}`}
          className="mt-4 inline-flex text-sm font-medium text-brand-700 underline-offset-4 hover:underline"
        >
          Probar inicio de sesión →
        </Link>
      )}
    </section>
  );
}
