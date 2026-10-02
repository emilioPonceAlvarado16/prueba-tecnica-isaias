import type { Metadata } from "next";
import Link from "next/link";
import { LogoMark } from "@/components/icons";
import "./globals.css";

export const metadata: Metadata = {
  title: "Banco Andino Demo · Apertura digital",
  description:
    "Prueba de concepto de onboarding digital multi-agente de Banco Andino Demo.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es-EC" className="h-full antialiased">
      <body className="flex min-h-full flex-col font-sans">
        <a
          href="#contenido"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-white focus:px-3 focus:py-2 focus:shadow"
        >
          Saltar al contenido
        </a>
        <header className="bg-brand-900 text-white">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
            <Link
              href="/"
              className="flex items-center gap-2.5 rounded-md focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white"
            >
              <LogoMark className="h-8 w-8" />
              <span className="leading-tight">
                <span className="block whitespace-nowrap text-base font-semibold tracking-tight">
                  Banco Andino
                </span>
                <span className="block text-[11px] uppercase tracking-[0.18em] text-brand-200">
                  Demo
                </span>
              </span>
            </Link>
            <nav aria-label="Principal" className="flex items-center gap-1 text-sm">
              <Link
                href="/"
                className="hidden whitespace-nowrap rounded-md px-3 py-2 text-brand-100 hover:bg-white/10 hover:text-white sm:inline-flex"
              >
                Abrir cuenta
              </Link>
              <Link
                href="/login/"
                className="whitespace-nowrap rounded-md border border-white/25 px-3 py-2 font-medium hover:bg-white/10"
              >
                Iniciar sesión
              </Link>
            </nav>
          </div>
        </header>
        <main id="contenido" className="flex-1">
          {children}
        </main>
        <footer className="border-t border-slate-200 bg-white">
          <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-5 text-xs text-slate-500 sm:flex-row sm:justify-between sm:px-6">
            <p>© 2026 Banco Andino Demo · Entidad ficticia para prueba de concepto.</p>
            <p>Datos de prueba. No ingreses información personal real.</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
