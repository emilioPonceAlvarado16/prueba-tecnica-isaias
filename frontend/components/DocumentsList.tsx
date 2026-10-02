import type { RequiredDocument } from "@/lib/types";
import { DocumentIcon } from "./icons";

export default function DocumentsList({
  documents,
}: {
  documents: RequiredDocument[];
}) {
  return (
    <ul className="divide-y divide-slate-100">
      {documents.map((doc) => (
        <li key={doc.code} className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
          <DocumentIcon className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" />
          <div className="min-w-0 flex-1">
            <p className="font-medium text-slate-900">{doc.name}</p>
            <p className="mt-1 flex flex-wrap gap-1.5 text-[11px]">
              <span
                className={
                  doc.mandatory
                    ? "rounded bg-brand-700 px-1.5 py-0.5 font-medium text-white"
                    : "rounded bg-slate-100 px-1.5 py-0.5 text-slate-600"
                }
              >
                {doc.mandatory ? "Obligatorio" : "Opcional"}
              </span>
              {doc.policy_ref && (
                <span
                  className="rounded bg-brand-50 px-1.5 py-0.5 font-mono text-brand-800 ring-1 ring-brand-200"
                  title="Política que exige este documento"
                >
                  {doc.policy_ref}
                </span>
              )}
              {doc.source === "rag_fallback" && (
                <span
                  className="rounded bg-amber-50 px-1.5 py-0.5 text-amber-800 ring-1 ring-amber-200"
                  title="El servicio de documentación no respondió; documento derivado de las políticas"
                >
                  Fuente: políticas (RAG)
                </span>
              )}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}
