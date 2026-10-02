import type { Metadata } from "next";
import { Suspense } from "react";
import LoginForm from "@/components/LoginForm";

export const metadata: Metadata = {
  title: "Iniciar sesión · Banco Andino Demo",
};

export default function LoginPage() {
  return (
    <div className="mx-auto max-w-md px-4 py-12 sm:py-16">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h1 className="text-2xl font-semibold text-slate-900">Banca en línea</h1>
        <p className="mt-1 mb-6 text-sm text-slate-500">
          Ingresa con el usuario y la contraseña temporal que recibiste al aprobarse tu cuenta.
        </p>
        <Suspense fallback={null}>
          <LoginForm />
        </Suspense>
      </div>
    </div>
  );
}
