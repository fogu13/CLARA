import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { callTool } from "../_shared/ai.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

const SYSTEM_PROMPT = `You are an experimentation analyst. You read raw A/B test result records and distil them into reusable, generalisable learnings for marketers.
For each distinct pattern you can support with evidence, produce a learning with:
- topic: short snake_case theme (e.g. subject_lines, cta_text, send_time, layout, personalization, pricing, checkout, onboarding)
- pattern: one-sentence, generalisable takeaway (not test-specific)
- evidence: tests_count, avg_lift_pct, confidence (0-1), sample_size, winning_examples[], losing_examples[]
- is_validated: true only if multiple tests agree with solid sample sizes
Only output learnings genuinely supported by the data. If the data is too thin, return an empty array.`;

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  try {
    const { workspace_id } = await req.json();
    if (!workspace_id) {
      return new Response(JSON.stringify({ error: "workspace_id is required" }), {
        status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

    // Pull recent A/B test result signals to learn from.
    const { data: signals, error: sigErr } = await db
      .from("signals")
      .select("text_content, metric_name, metric_value, metric_delta_pct, tags, metadata, recorded_at")
      .eq("workspace_id", workspace_id)
      .eq("source", "ab_test_result")
      .order("recorded_at", { ascending: false })
      .limit(50);
    if (sigErr) throw sigErr;

    if (!signals?.length) {
      return new Response(JSON.stringify({ created: 0, reason: "No A/B test result signals to analyse" }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const userPrompt = "Derive reusable learnings from these A/B test result records:\n\n" +
      JSON.stringify(signals, null, 2);

    const tools = [{
      type: "function",
      function: {
        name: "submit_learnings",
        description: "Submit distilled, reusable A/B test learnings",
        parameters: {
          type: "object",
          properties: {
            learnings: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  topic: { type: "string" },
                  pattern: { type: "string" },
                  is_validated: { type: "boolean" },
                  evidence: {
                    type: "object",
                    properties: {
                      tests_count: { type: "integer" },
                      avg_lift_pct: { type: "number" },
                      confidence: { type: "number" },
                      sample_size: { type: "integer" },
                      winning_examples: { type: "array", items: { type: "string" } },
                      losing_examples: { type: "array", items: { type: "string" } },
                    },
                    required: ["tests_count", "avg_lift_pct", "confidence", "sample_size", "winning_examples", "losing_examples"],
                  },
                },
                required: ["topic", "pattern", "is_validated", "evidence"],
              },
            },
          },
          required: ["learnings"],
        },
      },
    }];

    const result = await callTool({
      system: SYSTEM_PROMPT,
      user: userPrompt,
      tool: tools[0],
      toolName: "submit_learnings",
    });
    const { learnings } = result as {
      learnings: { topic: string; pattern: string; is_validated: boolean; evidence: Record<string, unknown> }[];
    };

    if (!learnings?.length) {
      return new Response(JSON.stringify({ created: 0, reason: "No learnings derived" }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // Skip patterns we already have (avoid duplicates on re-run).
    const { data: existing } = await db
      .from("ab_learnings")
      .select("pattern")
      .eq("workspace_id", workspace_id);
    const seen = new Set((existing ?? []).map((e: { pattern: string }) => e.pattern.trim().toLowerCase()));

    const rows = learnings
      .filter((l) => !seen.has(l.pattern.trim().toLowerCase()))
      .map((l) => ({
        workspace_id,
        topic: l.topic,
        pattern: l.pattern,
        evidence: l.evidence,
        is_validated: l.is_validated,
        test_ids: [],
        last_validated_at: new Date().toISOString(),
      }));

    if (rows.length) {
      const { error: insErr } = await db.from("ab_learnings").insert(rows);
      if (insErr) throw insErr;
    }

    return new Response(JSON.stringify({ created: rows.length }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("extract-learnings error:", e);
    const status = (e as { status?: number })?.status ?? 500;
    return new Response(JSON.stringify({ error: e instanceof Error ? e.message : "Unknown error" }), {
      status, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
