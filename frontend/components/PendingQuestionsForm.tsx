"use client";

import { useState } from "react";
import type { Answers, PendingQuestion } from "@/lib/types";
import { Spinner } from "./icons";

type Props = {
  questions: PendingQuestion[];
  submitting: boolean;
  error?: string | null;
  fieldErrors?: Record<string, string[]>;
  onSubmit: (answers: Answers) => void;
};

const inputCls =
  "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-slate-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30 aria-[invalid=true]:border-red-500";

export default function PendingQuestionsForm({
  questions,
  submitting,
  error,
  fieldErrors,
  onSubmit,
}: Props) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [missing, setMissing] = useState<string[]>([]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const empty = questions
      .filter((q) => q.required && !values[q.field]?.trim())
      .map((q) => q.field);
    setMissing(empty);
    if (empty.length) {
      document.getElementById(`q-${empty[0]}`)?.focus();
      return;
    }
    const answers: Answers = {};
    for (const q of questions) {
      const raw = values[q.field]?.trim();
      if (!raw) continue;
      answers[q.field] = q.type === "number" ? Number(raw) : raw;
    }
    onSubmit(answers);
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      {questions.map((q) => {
        const id = `q-${q.field}`;
        const errs = [
          ...(missing.includes(q.field) ? ["Este campo es obligatorio."] : []),
          ...(fieldErrors?.[q.field] ?? []),
        ];
        const common = {
          id,
          name: q.field,
          value: values[q.field] ?? "",
          disabled: submitting,
          required: q.required,
          "aria-invalid": errs.length > 0,
          "aria-describedby": errs.length ? `${id}-err` : undefined,
          className: inputCls,
        };
        const set = (v: string) => setValues((prev) => ({ ...prev, [q.field]: v }));
        return (
          <div key={q.field}>
            <label htmlFor={id} className="block text-sm font-medium text-slate-800">
              {q.label}
              {q.required ? (
                <span className="text-red-600" aria-hidden="true"> *</span>
              ) : (
                <span className="font-normal text-slate-500"> (opcional)</span>
              )}
            </label>
            {q.type === "select" ? (
              <select {...common} onChange={(e) => set(e.target.value)}>
                <option value="">Selecciona una opción</option>
                {(q.options ?? []).map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            ) : (
              <input
                {...common}
                type={q.type === "number" ? "number" : "text"}
                inputMode={q.type === "number" ? "decimal" : undefined}
                min={q.type === "number" ? 0 : undefined}
                step={q.type === "number" ? "any" : undefined}
                onChange={(e) => set(e.target.value)}
              />
            )}
            {errs.length > 0 && (
              <p id={`${id}-err`} className="mt-1 text-sm text-red-700">
                {errs.join(" ")}
              </p>
            )}
          </div>
        );
      })}
      {error && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800 ring-1 ring-red-200">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={submitting}
        className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-brand-700 px-4 py-3 font-semibold text-white shadow-sm hover:bg-brand-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 disabled:cursor-not-allowed disabled:opacity-70 sm:w-auto"
      >
        {submitting && <Spinner className="h-4 w-4" />}
        {submitting ? "Enviando…" : "Enviar información"}
      </button>
    </form>
  );
}
