// Provider-agnostic AI config (any OpenAI-compatible endpoint, hosted or self-hosted).
// Works with any OpenAI-compatible Chat Completions endpoint:
//   - OpenAI:        AI_BASE_URL=https://api.openai.com/v1            AI_MODEL=gpt-4o-mini
//   - Google Gemini: AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai  AI_MODEL=gemini-2.5-flash
//   - Groq / OpenRouter / Together: set their base URL + model
//   - Local (Ollama): AI_BASE_URL=http://localhost:11434/v1          AI_MODEL=llama3.1   (AI_API_KEY optional)
//   - Local (vLLM):   AI_BASE_URL=http://localhost:8000/v1           AI_MODEL=<served-model>
// Set AI_BASE_URL, AI_API_KEY, AI_MODEL as edge-function secrets.

export const AI_BASE_URL = (Deno.env.get("AI_BASE_URL") ?? "https://api.openai.com/v1").replace(/\/+$/, "");
export const AI_API_KEY = Deno.env.get("AI_API_KEY") ?? "";
export const AI_MODEL = Deno.env.get("AI_MODEL") ?? "gpt-4o-mini";

export function aiHeaders(): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  // Local servers (Ollama/vLLM) usually need no key; only send one if configured.
  if (AI_API_KEY) h.Authorization = `Bearer ${AI_API_KEY}`;
  return h;
}

/**
 * Single-tool structured call against an OpenAI-compatible endpoint.
 * Returns the parsed tool-call arguments. Throws Error with `.status` on HTTP failure.
 */
export async function callTool(opts: {
  system: string;
  user: string;
  tool: unknown;
  toolName: string;
}): Promise<Record<string, unknown>> {
  const res = await fetch(`${AI_BASE_URL}/chat/completions`, {
    method: "POST",
    headers: aiHeaders(),
    body: JSON.stringify({
      model: AI_MODEL,
      messages: [
        { role: "system", content: opts.system },
        { role: "user", content: opts.user },
      ],
      tools: [opts.tool],
      tool_choice: { type: "function", function: { name: opts.toolName } },
    }),
  });

  if (!res.ok) {
    let detail = "";
    try { detail = await res.text(); } catch { /* ignore */ }
    if (res.status !== 429 && res.status !== 402) console.error("AI provider error:", res.status, detail);
    const err = new Error(
      res.status === 429 ? "Rate limit exceeded. Please try again shortly."
      : res.status === 402 ? "Usage credits/quota required for the configured AI provider."
      : "AI provider error",
    ) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }

  const data = await res.json();
  const toolCall = data.choices?.[0]?.message?.tool_calls?.[0];
  if (!toolCall) throw new Error("No structured response returned from AI");
  return JSON.parse(toolCall.function.arguments);
}

export const AI_EMBED_MODEL = Deno.env.get("AI_EMBED_MODEL") ?? "gemini-embedding-001";
// Must match the pgvector column dimension (taxonomy_nodes.embedding vector(768)).
// gemini-embedding-001 defaults to 3072; request 768. Cosine distance is scale-invariant
// so the reduced (un-normalised) vectors are fine for our nearest-neighbour matching.
export const AI_EMBED_DIM = Number(Deno.env.get("AI_EMBED_DIM") ?? "768");

/** Embed one or more strings via the OpenAI-compatible /embeddings endpoint. */
export async function embed(input: string | string[]): Promise<number[][]> {
  const res = await fetch(`${AI_BASE_URL}/embeddings`, {
    method: "POST",
    headers: aiHeaders(),
    body: JSON.stringify({ model: AI_EMBED_MODEL, input, dimensions: AI_EMBED_DIM }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    const err = new Error(`Embedding error ${res.status}: ${detail}`) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  const data = await res.json();
  return (data.data as { embedding: number[] }[]).map((d) => d.embedding);
}

/** pgvector accepts a string like "[0.1,0.2,...]". */
export function toVectorLiteral(v: number[]): string {
  return `[${v.join(",")}]`;
}
