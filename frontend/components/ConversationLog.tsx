import type { ConversationMessage } from "@/lib/types";
import { formatTime } from "@/lib/labels";

const ROLE = {
  customer: { label: "Tú", cls: "ml-auto bg-brand-700 text-white", meta: "text-brand-100" },
  assistant: { label: "Banco Andino", cls: "bg-slate-100 text-slate-900", meta: "text-slate-500" },
  system: { label: "Sistema", cls: "mx-auto bg-amber-50 text-amber-900 ring-1 ring-amber-200 text-xs", meta: "text-amber-700" },
} as const;

export default function ConversationLog({
  messages,
}: {
  messages: ConversationMessage[];
}) {
  return (
    <ol className="flex flex-col gap-3">
      {messages.map((m, i) => {
        const r = ROLE[m.role as keyof typeof ROLE] ?? ROLE.system;
        return (
          <li key={i} className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${r.cls}`}>
            <p className={`mb-0.5 text-[11px] font-medium ${r.meta}`}>
              {r.label}
              {m.created_at && ` · ${formatTime(m.created_at)}`}
            </p>
            <p className="whitespace-pre-line leading-relaxed">{m.content}</p>
          </li>
        );
      })}
    </ol>
  );
}
