/* Assistant statistique. Sans clé : moteur local (lib/assistant.ts), gratuit, répond uniquement à partir des données publiées.
   Avec ANTHROPIC_API_KEY (variable Vercel, côté serveur) : Claude reformule et approfondit la réponse, à partir des mêmes données. */
import { NextResponse } from "next/server";
import { answer, globalContext } from "@/lib/assistant";

export const dynamic = "force-dynamic";

type Msg = { role: "user" | "assistant"; content: string };
const MODEL = process.env.ANTHROPIC_MODEL ?? "claude-sonnet-4-5";
const SYSTEM = `Tu es l'assistant statistique de Goalgebra, une plateforme académique d'analyse du football.
Règles :
- Réponds en français, en 2 à 8 phrases ou une courte liste, sans titre.
- Utilise UNIQUEMENT les données fournies dans <donnees>. Si une information manque, dis-le simplement. N'invente aucun chiffre, joueur, blessure ou actualité.
- Présente des probabilités et des statistiques, jamais des certitudes : n'écris jamais « garanti », « sûr », « 100 % ».
- Ne donne aucun conseil de pari ni de mise. Si on te demande quoi parier, explique le niveau de risque statistique et rappelle que le modèle ne bat pas les cotes en moyenne.`;

// limitation simple par adresse (protège la clé API) : 20 questions / 10 minutes
const hits = new Map<string, number[]>();
function limited(ip: string) {
  const t = Date.now(), w = (hits.get(ip) ?? []).filter((x) => t - x < 600_000);
  w.push(t); hits.set(ip, w);
  return w.length > 20;
}

/** Historique valide pour l'API : commence par l'utilisateur, rôles alternés. */
function history(h: Msg[]): Msg[] {
  const out: Msg[] = [];
  for (const m of h) {
    if (!out.length && m.role !== "user") continue;
    if (out.length && out[out.length - 1].role === m.role) out[out.length - 1] = m; else out.push(m);
  }
  if (out.length && out[out.length - 1].role === "user") out.pop();
  return out;
}

export async function POST(req: Request) {
  let messages: Msg[] = [];
  try {
    const body = await req.json();
    messages = (Array.isArray(body?.messages) ? body.messages : []).filter((m: Msg) => (m.role === "user" || m.role === "assistant") && typeof m.content === "string")
      .slice(-6).map((m: Msg) => ({ role: m.role, content: m.content.slice(0, 600) }));
  } catch { /* corps invalide */ }
  const last = [...messages].reverse().find((m) => m.role === "user");
  if (!last?.content.trim()) return NextResponse.json({ error: "Question vide" }, { status: 400 });

  const local = answer(last.content);
  const key = process.env.ANTHROPIC_API_KEY;
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "local";
  if (!key || limited(ip)) return NextResponse.json({ reply: local.text, links: local.links, engine: "local" });

  try {
    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01" },
      body: JSON.stringify({
        model: MODEL, max_tokens: 600, system: SYSTEM,
        messages: [
          ...history(messages.slice(0, -1)),
          { role: "user", content: `<donnees>\n${globalContext()}\n${local.context || local.text}\n</donnees>\n\nQuestion : ${last.content}` },
        ],
      }),
      signal: AbortSignal.timeout(20_000),
    });
    if (!r.ok) throw new Error(String(r.status));
    const j = await r.json();
    const text = (j.content ?? []).filter((c: { type: string }) => c.type === "text").map((c: { text: string }) => c.text).join("\n").trim();
    if (!text) throw new Error("vide");
    return NextResponse.json({ reply: text, links: local.links, engine: "llm" });
  } catch {
    return NextResponse.json({ reply: local.text, links: local.links, engine: "local" });
  }
}
