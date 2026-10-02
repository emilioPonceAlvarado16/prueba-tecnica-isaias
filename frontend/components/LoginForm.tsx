"use client";

import { useSearchParams } from "next/navigation";
import { useState } from "react";
import {
  cognitoConfigured,
  cognitoErrorMessage,
  signIn,
  type IdTokenClaims,
  type SignInOutcome,
} from "@/lib/cognito";
import { AlertIcon, CheckCircleIcon, Spinner } from "./icons";

const inputCls =
  "mt-1.5 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30";
const btnCls =
  "inline-flex w-full items-center justify-center gap-2 rounded-lg bg-brand-700 px-4 py-3 font-semibold text-white shadow-sm hover:bg-brand-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 disabled:opacity-70";

type Stage =
  | { name: "credentials" }
  | { name: "new_password"; complete: (pw: string) => Promise<SignInOutcome> }
  | { name: "done"; claims: IdTokenClaims; signOut: () => void };

export default function LoginForm() {
  const params = useSearchParams();
  const [username, setUsername] = useState(params.get("u") ?? "");
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [stage, setStage] = useState<Stage>({ name: "credentials" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleOutcome(o: SignInOutcome) {
    if (o.kind === "success") setStage({ name: "done", claims: o.claims, signOut: o.signOut });
    else setStage({ name: "new_password", complete: o.complete });
  }

  async function run(fn: () => Promise<SignInOutcome>) {
    setBusy(true);
    setError(null);
    try {
      handleOutcome(await fn());
    } catch (e) {
      setError(cognitoErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  function onLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError("Ingresa tu usuario y contraseña.");
      return;
    }
    run(() => signIn(username.trim(), password));
  }

  function onNewPassword(e: React.FormEvent) {
    e.preventDefault();
    if (stage.name !== "new_password") return;
    if (newPassword.length < 8) {
      setError("La nueva contraseña debe tener al menos 8 caracteres.");
      return;
    }
    if (newPassword !== confirm) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    run(() => stage.complete(newPassword));
  }

  if (!cognitoConfigured) {
    return (
      <div className="flex gap-3 rounded-xl bg-amber-50 p-4 text-sm text-amber-900 ring-1 ring-amber-200">
        <AlertIcon className="h-5 w-5 shrink-0" />
        <div>
          <p className="font-semibold">Login disponible solo en el despliegue AWS</p>
          <p className="mt-1">
            Configura <code className="font-mono text-xs">NEXT_PUBLIC_COGNITO_USER_POOL_ID</code> y{" "}
            <code className="font-mono text-xs">NEXT_PUBLIC_COGNITO_CLIENT_ID</code> para habilitar el
            inicio de sesión con Amazon Cognito.
          </p>
        </div>
      </div>
    );
  }

  const errorBox = error && (
    <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800 ring-1 ring-red-200">
      {error}
    </p>
  );

  if (stage.name === "done") {
    const c = stage.claims;
    const rows: [string, unknown][] = [
      ["Nombre", c.name],
      ["Usuario (cognito:username)", c["cognito:username"]],
      ["Correo", c.email],
      ["Emitido", typeof c.iat === "number" ? new Date(c.iat * 1000).toLocaleString("es-EC") : null],
      ["Expira", typeof c.exp === "number" ? new Date(c.exp * 1000).toLocaleString("es-EC") : null],
    ];
    return (
      <div role="status" className="space-y-4">
        <div className="flex items-center gap-3 rounded-xl bg-emerald-50 p-4 text-emerald-900 ring-1 ring-emerald-200">
          <CheckCircleIcon className="h-6 w-6 shrink-0 text-emerald-600" />
          <div>
            <p className="font-semibold">Sesión iniciada</p>
            <p className="text-sm">
              {typeof c.name === "string" ? `¡Hola, ${c.name.split(" ")[0]}!` : "¡Bienvenido!"} Tu
              acceso digital funciona correctamente.
            </p>
          </div>
        </div>
        <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-2 text-sm">
          {rows
            .filter(([, v]) => v != null && v !== "")
            .map(([k, v]) => (
              <div key={k} className="contents">
                <dt className="text-slate-500">{k}</dt>
                <dd className="break-all font-medium text-slate-900">{String(v)}</dd>
              </div>
            ))}
        </dl>
        <details className="text-sm">
          <summary className="cursor-pointer text-brand-700">Ver todos los claims del ID token</summary>
          <pre className="mt-2 max-h-72 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
            {JSON.stringify(c, null, 2)}
          </pre>
        </details>
        <button
          type="button"
          onClick={() => {
            stage.signOut();
            setPassword("");
            setStage({ name: "credentials" });
          }}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
        >
          Cerrar sesión
        </button>
      </div>
    );
  }

  if (stage.name === "new_password") {
    return (
      <form onSubmit={onNewPassword} noValidate className="space-y-4">
        <p className="rounded-lg bg-brand-50 px-3 py-2 text-sm text-brand-900 ring-1 ring-brand-100">
          Es tu primer ingreso. Crea una nueva contraseña para reemplazar la temporal.
        </p>
        <div>
          <label htmlFor="new-password" className="text-sm font-medium text-slate-800">
            Nueva contraseña
          </label>
          <input
            id="new-password"
            type="password"
            autoComplete="new-password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            aria-describedby="new-password-help"
            className={inputCls}
          />
          <p id="new-password-help" className="mt-1.5 text-xs text-slate-500">
            Mínimo 8 caracteres, con mayúsculas, minúsculas, números y símbolos.
          </p>
        </div>
        <div>
          <label htmlFor="confirm-password" className="text-sm font-medium text-slate-800">
            Confirma la nueva contraseña
          </label>
          <input
            id="confirm-password"
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className={inputCls}
          />
        </div>
        {errorBox}
        <button type="submit" disabled={busy} className={btnCls}>
          {busy && <Spinner className="h-4 w-4" />}
          Guardar y continuar
        </button>
      </form>
    );
  }

  return (
    <form onSubmit={onLogin} noValidate className="space-y-4">
      <div>
        <label htmlFor="username" className="text-sm font-medium text-slate-800">
          Usuario (tu número de cédula)
        </label>
        <input
          id="username"
          inputMode="numeric"
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className={`${inputCls} font-mono`}
        />
      </div>
      <div>
        <label htmlFor="password" className="text-sm font-medium text-slate-800">
          Contraseña
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={inputCls}
        />
      </div>
      {errorBox}
      <button type="submit" disabled={busy} className={btnCls}>
        {busy && <Spinner className="h-4 w-4" />}
        {busy ? "Ingresando…" : "Ingresar"}
      </button>
    </form>
  );
}
