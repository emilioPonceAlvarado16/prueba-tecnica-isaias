import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Estado de tu solicitud · Banco Andino Demo",
};

export default function OnboardingLayout({ children }: { children: React.ReactNode }) {
  return children;
}
