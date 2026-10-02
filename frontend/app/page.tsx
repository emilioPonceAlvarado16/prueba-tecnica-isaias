import OnboardingForm from "@/components/OnboardingForm";

const STEPS = [
  { title: "Validación de cédula", text: "Verificamos el formato y dígito verificador." },
  { title: "Agente de identidad", text: "Consulta al Registro Civil y nivel de confianza." },
  { title: "Agente de listas de riesgo", text: "Revisión de listas de control y PEP." },
  { title: "Agente de políticas", text: "Documentos requeridos según las políticas del banco." },
  { title: "Agente de respuesta", text: "Te explicamos el resultado y tu siguiente paso." },
];

export default function Home() {
  return (
    <div className="relative">
      <div aria-hidden="true" className="absolute inset-x-0 top-0 h-64 bg-brand-900 sm:h-72" />
      <div className="relative mx-auto max-w-6xl px-4 pb-14 pt-8 sm:px-6 sm:pt-12">
        <div className="max-w-2xl text-white">
          <p className="text-sm font-medium uppercase tracking-[0.16em] text-brand-200">
            Apertura 100% digital
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
            Abre tu cuenta en minutos
          </h1>
          <p className="mt-3 text-brand-100">
            Completa tus datos y nuestros agentes revisarán tu solicitud al instante.
          </p>
        </div>

        <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
          <OnboardingForm />

          <aside className="space-y-6">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="font-semibold text-slate-900">¿Cómo funciona?</h2>
              <ol className="mt-4 space-y-4">
                {STEPS.map((s, i) => (
                  <li key={s.title} className="flex gap-3">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-semibold text-brand-800">
                      {i + 1}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-slate-900">{s.title}</p>
                      <p className="text-xs text-slate-500">{s.text}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </section>
            <section className="rounded-2xl bg-brand-50 p-5 text-sm text-brand-900 ring-1 ring-brand-100">
              <h2 className="font-semibold">Ten a mano</h2>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                <li>Tu cédula de identidad ecuatoriana vigente.</li>
                <li>Una planilla de servicio básico (máx. 3 meses).</li>
                <li>Tu correo electrónico para recibir tu acceso.</li>
              </ul>
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}
