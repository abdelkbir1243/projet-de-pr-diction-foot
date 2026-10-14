"use client";
/* Assistant statistique : panneau de discussion accessible partout (en-tête, bouton flottant) et page /assistant. */
import Link from "next/link";
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { ArrowUp, Bot, Sparkles, X } from "lucide-react";
import { cn } from "@/lib/utils";

type Msg = { role: "user" | "assistant"; content: string; links?: { label: string; href: string }[] };
const SUGGESTIONS = ["Quels sont les matchs les moins risqués ?", "Le modèle est-il fiable ?", "Classement de la Premier League", "C'est quoi les xG ?"];

const Ctx = createContext<{ open: boolean; setOpen: (o: boolean) => void; msgs: Msg[]; send: (q: string) => void; busy: boolean }>({
  open: false, setOpen: () => {}, msgs: [], send: () => {}, busy: false,
});
export const useAssistant = () => useContext(Ctx);

export function AssistantProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const send = async (q: string) => {
    const text = q.trim();
    if (!text || busy) return;
    const next: Msg[] = [...msgs, { role: "user", content: text }];
    setMsgs(next); setBusy(true);
    try {
      const r = await fetch("/api/assistant", { method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ messages: next.map(({ role, content }) => ({ role, content })) }) });
      const j = await r.json();
      setMsgs([...next, { role: "assistant", content: j.reply ?? "Je n'ai pas pu répondre.", links: j.links }]);
    } catch {
      setMsgs([...next, { role: "assistant", content: "L'assistant est momentanément indisponible. Réessayez dans un instant." }]);
    } finally { setBusy(false); }
  };
  return <Ctx.Provider value={{ open, setOpen, msgs, send, busy }}>{children}<AssistantSheet /></Ctx.Provider>;
}

/** Rendu léger : **gras**, listes « - », retours à la ligne. Aucun HTML injecté. */
function Rich({ text }: { text: string }) {
  return (
    <div className="space-y-1">
      {text.split("\n").filter((l) => l.trim()).map((l, i) => {
        const bullet = l.startsWith("- ");
        const parts = (bullet ? l.slice(2) : l).split(/(\*\*[^*]+\*\*)/g).map((p, k) => p.startsWith("**") ? <strong key={k} className="font-semibold text-text">{p.slice(2, -2)}</strong> : p);
        return bullet ? <div key={i} className="flex gap-2"><span className="mt-[7px] size-1 shrink-0 rounded-full bg-text-3" /><span>{parts}</span></div> : <p key={i}>{parts}</p>;
      })}
    </div>
  );
}

export function Chat({ className, compact }: { className?: string; compact?: boolean }) {
  const { msgs, send, busy, setOpen } = useAssistant();
  const [q, setQ] = useState("");
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [msgs, busy]);
  return (
    <div className={cn("flex min-h-0 flex-col", className)}>
      <div className="scrollbar-thin min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4" aria-live="polite">
        <div className="flex gap-2.5">
          <span className="ai-gradient grid size-7 shrink-0 place-items-center rounded-full text-white"><Bot className="size-4" /></span>
          <div className="rounded-2xl rounded-tl-sm bg-surface-2 px-3.5 py-2.5 text-[13px] leading-relaxed text-text-2">
            Bonjour ! Je réponds à vos questions à partir des statistiques du site : analyse d&apos;un match, forme d&apos;une équipe, classement, niveau de risque, fiabilité du modèle.
          </div>
        </div>
        {msgs.map((m, i) => m.role === "user" ? (
          <div key={i} className="flex justify-end"><div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-brand px-3.5 py-2 text-[13px] text-white">{m.content}</div></div>
        ) : (
          <div key={i} className="flex gap-2.5">
            <span className="ai-gradient grid size-7 shrink-0 place-items-center rounded-full text-white"><Bot className="size-4" /></span>
            <div className="min-w-0 max-w-[90%] rounded-2xl rounded-tl-sm bg-surface-2 px-3.5 py-2.5 text-[13px] leading-relaxed text-text-2">
              <Rich text={m.content} />
              {!!m.links?.length && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {m.links.map((l) => <Link key={l.href} href={l.href} onClick={() => setOpen(false)} className="rounded-full border border-border bg-surface px-2.5 py-1 text-[12px] font-medium text-brand hover:border-brand">{l.label} →</Link>)}
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && <div className="flex gap-2.5"><span className="ai-gradient grid size-7 shrink-0 place-items-center rounded-full text-white"><Bot className="size-4" /></span><div className="flex items-center gap-1 rounded-2xl bg-surface-2 px-3.5 py-3">{[0, 1, 2].map((k) => <span key={k} className="size-1.5 animate-pulse-dot rounded-full bg-text-3" style={{ animationDelay: `${k * 150}ms` }} />)}</div></div>}
        <div ref={end} />
      </div>
      {msgs.length === 0 && (
        <div className={cn("flex flex-wrap gap-1.5 px-4 pb-2", compact && "max-h-24 overflow-hidden")}>
          {SUGGESTIONS.map((s) => <button key={s} onClick={() => send(s)} className="rounded-full border border-border bg-surface px-3 py-1.5 text-[12px] text-text-2 transition-colors hover:border-brand hover:text-brand">{s}</button>)}
        </div>
      )}
      <form onSubmit={(e) => { e.preventDefault(); send(q); setQ(""); }} className="flex items-end gap-2 border-t border-border p-3">
        <label className="sr-only" htmlFor="assistant-q">Votre question</label>
        <textarea id="assistant-q" value={q} onChange={(e) => setQ(e.target.value)} rows={1} maxLength={500} placeholder="Ex. : analyse PSG – Lille"
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(q); setQ(""); } }}
          className="max-h-32 min-h-10 flex-1 resize-none rounded-xl border border-border bg-surface px-3 py-2.5 text-[14px] outline-none transition-colors focus:border-brand" />
        <button type="submit" disabled={busy || !q.trim()} aria-label="Envoyer" className="grid size-10 shrink-0 place-items-center rounded-xl bg-brand text-white transition-opacity disabled:opacity-40"><ArrowUp className="size-4" /></button>
      </form>
      <p className="px-4 pb-3 text-center text-[10px] text-text-3">Réponses statistiques, jamais des certitudes ni des conseils de pari.</p>
    </div>
  );
}

function AssistantSheet() {
  const { open, setOpen } = useAssistant();
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/30 backdrop-blur-[1px]" />
        <Dialog.Content className="fixed inset-x-0 bottom-0 z-50 flex h-[85dvh] flex-col rounded-t-2xl border border-border bg-surface shadow-pop animate-fade-in sm:inset-y-3 sm:left-auto sm:right-3 sm:h-auto sm:w-[420px] sm:rounded-2xl">
          <div className="flex items-center gap-2 border-b border-border px-4 py-3">
            <span className="ai-gradient grid size-8 place-items-center rounded-lg text-white"><Sparkles className="size-4" /></span>
            <div className="min-w-0 flex-1">
              <Dialog.Title className="text-[14px] font-semibold">Assistant statistique</Dialog.Title>
              <Dialog.Description className="text-[11px] text-text-3">Répond à partir des données du site</Dialog.Description>
            </div>
            <Link href="/assistant" onClick={() => setOpen(false)} className="hidden text-[12px] font-medium text-brand hover:underline sm:block">Plein écran</Link>
            <Dialog.Close className="grid size-8 place-items-center rounded-md text-text-3 hover:bg-surface-2" aria-label="Fermer"><X className="size-4" /></Dialog.Close>
          </div>
          <Chat className="flex-1" compact />
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/** Bouton d'ouverture (en-tête). */
export function AssistantButton({ className }: { className?: string }) {
  const { setOpen } = useAssistant();
  return (
    <button onClick={() => setOpen(true)} aria-label="Ouvrir l'assistant statistique" title="Assistant statistique"
      className={cn("inline-flex h-9 items-center gap-1.5 rounded-lg px-2 text-[13px] font-medium text-brand transition-colors hover:bg-brand-soft sm:px-2.5", className)}>
      <Sparkles className="size-[18px]" /><span className="hidden xl:inline">Assistant</span>
    </button>
  );
}
