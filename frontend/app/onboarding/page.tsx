"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import OnboardingResultView, { MessagePanel } from "@/components/OnboardingResultView";
import { Spinner } from "@/components/icons";

function Loading() {
  return (
    <div role="status" className="flex items-center justify-center gap-3 py-24 text-slate-600">
      <Spinner className="h-6 w-6 text-brand-600" />
      Cargando tu solicitud…
    </div>
  );
}

function OnboardingPageInner() {
  const id = useSearchParams().get("id");
  if (!id) {
    return (
      <MessagePanel
        title="Falta el número de solicitud"
        text="El enlace no incluye el identificador de tu solicitud."
      />
    );
  }
  return <OnboardingResultView key={id} id={id} />;
}

export default function OnboardingPage() {
  return (
    <Suspense fallback={<Loading />}>
      <OnboardingPageInner />
    </Suspense>
  );
}
