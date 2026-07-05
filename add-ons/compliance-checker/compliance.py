"""EU AI Act + GDPR compliance checker.

Ported from Elvis_thesis_lovable/supabase/functions/check-compliance (Deno) to a
self-contained Python module so it can run standalone OR be folded into CLARA later
as an upsell feature.

The IP is the SYSTEM_PROMPT (a GDPR + EU AI Act knowledge base current to the mid-2026
Digital Omnibus) and the structured assessment schema. It assesses a marketing campaign
or AI use case and returns scored findings with article references and prohibited-practice
detection.

Standalone: uses its own minimal OpenAI-compatible caller (AI_BASE_URL / AI_API_KEY /
AI_MODEL). To fold into CLARA, delete `_call_tool` below and import
`app.services.ai.call_tool` instead — same (system, user, tool, tool_name) signature.

ponytail: no retry/tracing in the vendored caller — this is a demo/upsell surface; add
robustness (or swap to CLARA's ai.py) when it graduates.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

SYSTEM_PROMPT = """You are an expert EU regulatory compliance analyst specialising in the EU AI Act (Regulation 2024/1689) and the General Data Protection Regulation (GDPR, Regulation 2016/679). You assess marketing campaigns and use cases for compliance.

=== GDPR KNOWLEDGE BASE ===

LAWFUL BASES FOR PROCESSING (Art. 6):
- Consent: Must be freely given, specific, informed, unambiguous, and withdrawable at any time.
- Legitimate Interest: Must pass a three-part LIA test; cannot override individuals' rights.
- Contract: Only for processing strictly necessary to fulfill a contract.
- Legal Obligation, Vital Interests, Public Task: Specific conditions apply.

SPECIAL CATEGORIES OF DATA (Art. 9): Processing of racial/ethnic origin, political opinions, religious beliefs, trade union membership, genetic/biometric data, health data, sex life/sexual orientation data requires explicit consent or specific legal exception.

CONSENT REQUIREMENTS (Art. 7): Consent must be granular, as easy to withdraw as give, not bundled with other agreements, and documented.

KEY PRINCIPLES (Art. 5):
- Lawfulness, Fairness, Transparency
- Purpose Limitation: Data collected for specific, explicit, legitimate purposes; not further processed incompatibly
- Data Minimisation: Adequate, relevant, limited to what is necessary
- Accuracy: Kept accurate and up to date
- Storage Limitation: Not kept longer than necessary
- Integrity and Confidentiality: Appropriate security

TRANSPARENCY (Art. 13/14): At point of data collection, must provide identity of controller, purposes and legal basis, retention periods, data subject rights, right to withdraw consent, right to lodge complaint with DPA.

DATA SUBJECT RIGHTS (Art. 15-22):
- Art. 15: Right of Access
- Art. 16: Right to Rectification
- Art. 17: Right to Erasure ("Right to be Forgotten")
- Art. 18: Right to Restriction of Processing
- Art. 19: Right to Data Portability
- Art. 21: Right to Object — particularly strong for direct marketing; processing must stop without exception
- Art. 22: Rights related to Automated Decision-Making / Profiling

DIRECT MARKETING (Art. 21(2-3)): Individuals have an absolute right to object to direct marketing including profiling for direct marketing. No override possible.

PROFILING (Art. 4(4), 22): Any automated processing to evaluate personal aspects (personality, behaviour, location, interests, purchasing habits) requires explicit notice. Solely automated decisions with significant effects require explicit consent or legal basis.

PRIVACY BY DESIGN & DEFAULT (Art. 25): Controllers must implement appropriate technical and organisational measures.

DATA PROTECTION IMPACT ASSESSMENT (Art. 35): Mandatory before processing that is likely to result in high risk — including systematic profiling, large-scale processing of special categories, or systematic monitoring.

INTERNATIONAL DATA TRANSFERS (Ch. V, Art. 44-49): Transfers outside EEA require adequacy decision, Standard Contractual Clauses (SCCs), Binding Corporate Rules, or specific derogation.

ACCOUNTABILITY (Art. 5(2), 24): Controllers must demonstrate compliance. Maintain records of processing activities (Art. 30).

ePrivacy / PECR:
- Cookie consent required for non-essential cookies
- Email marketing requires prior opt-in consent (soft opt-in exception for existing customers with similar products)
- SMS marketing requires prior opt-in consent
- No unsolicited marketing by email/SMS to individuals without consent

=== EU AI ACT KNOWLEDGE BASE ===

APPLICATION TIMELINE (status mid-2026, including the Digital Omnibus on AI — political agreement 7 May 2026, pending formal Council/Parliament adoption):
- 2 Feb 2025: prohibited practices (Art. 5) and AI literacy (Art. 4) in force.
- 2 Aug 2025: GPAI model obligations (Ch. V), governance, and penalties in force.
- 2 Dec 2026: transparency obligations / AI-generated-content marking (Art. 50) apply (Digital Omnibus moved this from 2 Aug 2026).
- 2 Dec 2027: Annex III use-case high-risk obligations apply (Digital Omnibus deferred from 2 Aug 2026, a 16-month postponement).
- 2 Aug 2028: Annex I product-safety high-risk obligations apply (Digital Omnibus deferred from 2 Aug 2027).
- 2 Aug 2027: Member States must operate a regulatory sandbox (deferred from 2 Aug 2026).
The 2026 Digital Omnibus also: added a prohibition on generating non-consensual intimate imagery / CSAM; reinstated high-risk registration with reduced information requirements; extended simplified-documentation and proportionate-penalty relief from SMEs to small mid-cap companies; and tightened the justification required to process sensitive data for bias screening.

PROHIBITED AI PRACTICES (Art. 5 — BANNED):
1. Subliminal manipulation below the threshold of consciousness to distort behaviour causing harm
2. Exploiting vulnerabilities of specific groups (age, disability, social/economic situation) to distort behaviour causing harm
3. Social scoring by public authorities
4. Real-time remote biometric identification in public spaces (with narrow exceptions)
5. AI systems that infer emotions in workplace/education contexts
6. Biometric categorisation to deduce sensitive attributes (race, political views, religion, sexual orientation)
7. Predictive policing based solely on profiling
8. Untargeted scraping of facial images for recognition databases
9. Generating non-consensual sexually explicit/intimate imagery or child sexual abuse material (CSAM), e.g. deepfake-nude tools (added by the 2026 Digital Omnibus)

HIGH-RISK AI SYSTEMS (Annex III) — require conformity assessment, technical documentation, human oversight:
- Biometric identification and categorisation
- Critical infrastructure management
- Education and vocational training (access, assessment)
- Employment, HR decisions (recruitment, selection, promotion, termination, task allocation, monitoring performance)
- Access to essential private and public services (credit scoring, insurance, benefits assessment)
- Law enforcement uses
- Migration, asylum, border control
- Administration of justice

TRANSPARENCY OBLIGATIONS (Art. 50 — apply from 2 December 2026 per the Digital Omnibus):
- Providers of AI systems that interact with humans must disclose that the person is interacting with an AI (unless obvious)
- Providers of AI systems generating synthetic content must label it as AI-generated (deepfakes, AI text/images/audio/video)
- Emotion recognition systems must inform individuals
- Biometric categorisation systems must inform individuals

LIMITED-RISK AI SYSTEMS: Transparency obligations apply (chatbots, deepfakes, AI-generated content labelling).

GENERAL PURPOSE AI (GPAI) MODELS (Art. 51-56):
- Providers must maintain technical documentation, cooperate with authorities
- Systemic risk GPAI models have additional obligations (adversarial testing, incident reporting)

FUNDAMENTAL RIGHTS IMPACT ASSESSMENT: Deployers of high-risk AI systems must conduct before putting into use.

HUMAN OVERSIGHT (Art. 14): High-risk AI systems must allow human oversight; humans must be able to intervene, override, or switch off.

ACCURACY, ROBUSTNESS, CYBERSECURITY (Art. 15): High-risk AI systems must meet performance standards.

CONFORMITY ASSESSMENT: High-risk AI systems need CE marking and conformity assessment before deployment.

PROHIBITED MARKETING-SPECIFIC RISKS:
- Using AI to send personalised ads exploiting emotional vulnerabilities or psychological weaknesses
- AI systems that manipulate consumer choices through deceptive techniques
- Automated profiling for targeting vulnerable consumers (minors, people with mental health issues, financial distress)
- AI-generated content in ads without disclosure
- Predictive targeting based on inferred sensitive attributes

=== YOUR TASK ===
Analyse the provided marketing campaign or use case description against all applicable GDPR and EU AI Act requirements. Check also any additional local compliance documents provided. Return a comprehensive compliance assessment using the provided tool.

Scoring methodology:
- 90-100: Fully compliant, minimal risk
- 70-89: Largely compliant, minor gaps
- 50-69: Partial compliance, notable gaps requiring action
- 30-49: Poor compliance, significant violations
- 0-29: Critical violations, potential regulatory action

Assess each regulation area with a score and specific findings. Be specific about articles and requirements."""


ASSESSMENT_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "submit_compliance_assessment",
        "description": "Submit the structured compliance assessment result",
        "parameters": {
            "type": "object",
            "properties": {
                "overall_score": {"type": "integer", "description": "Overall compliance score 0-100"},
                "risk_level": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low", "minimal"],
                    "description": "Overall risk level",
                },
                "summary": {"type": "string", "description": "Executive summary (2-3 sentences)"},
                "gdpr_score": {"type": "integer", "description": "GDPR compliance score 0-100"},
                "eu_ai_act_score": {"type": "integer", "description": "EU AI Act compliance score 0-100"},
                "findings": {
                    "type": "array",
                    "description": "Detailed findings per regulation area",
                    "items": {
                        "type": "object",
                        "properties": {
                            "regulation": {"type": "string", "description": "GDPR or EU AI Act"},
                            "area": {"type": "string", "description": "Regulation area (e.g. Lawful Basis, Consent)"},
                            "article": {"type": "string", "description": "Article reference (e.g. Art. 6 GDPR)"},
                            "status": {"type": "string", "enum": ["pass", "fail", "warning", "not_applicable"]},
                            "score": {"type": "integer", "description": "Score for this area 0-100"},
                            "finding": {"type": "string", "description": "Specific finding about this area"},
                            "recommendation": {"type": "string", "description": "Action if status is fail/warning"},
                        },
                        "required": ["regulation", "area", "article", "status", "score", "finding"],
                    },
                },
                "required_actions": {
                    "type": "array",
                    "description": "Required actions to achieve compliance",
                    "items": {
                        "type": "object",
                        "properties": {
                            "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                            "action": {"type": "string", "description": "The specific action required"},
                            "regulation": {"type": "string", "description": "Which regulation this relates to"},
                            "deadline": {"type": "string", "description": "Timeline (e.g. Before launch, Within 30 days)"},
                        },
                        "required": ["priority", "action", "regulation", "deadline"],
                    },
                },
                "compliant_aspects": {
                    "type": "array",
                    "description": "Aspects already compliant",
                    "items": {"type": "string"},
                },
                "prohibited_practices_detected": {
                    "type": "array",
                    "description": "Prohibited practices detected (EU AI Act Art. 5 or GDPR violations)",
                    "items": {"type": "string"},
                },
            },
            "required": [
                "overall_score",
                "risk_level",
                "summary",
                "gdpr_score",
                "eu_ai_act_score",
                "findings",
                "required_actions",
                "compliant_aspects",
                "prohibited_practices_detected",
            ],
        },
    },
}


class ComplianceError(RuntimeError):
    """AI provider / structured-output failure. Carries .status."""

    def __init__(self, message: str, status: int = 500) -> None:
        super().__init__(message)
        self.status = status


def _call_tool(*, system: str, user: str, tool: dict[str, Any], tool_name: str, timeout: float = 120.0) -> dict[str, Any]:
    """Minimal OpenAI-compatible single-tool structured call (forced tool_choice).

    Swap this for `app.services.ai.call_tool` when folding into CLARA — identical
    signature, but with retry + Langfuse tracing.
    """
    base_url = (os.getenv("AI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("AI_MODEL") or "gpt-4o-mini"
    api_key = os.getenv("AI_API_KEY") or ""

    headers = {"Content-Type": "application/json"}
    if api_key:  # local servers (Ollama/vLLM) need no key
        headers["Authorization"] = f"Bearer {api_key}"

    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "tools": [tool],
        "tool_choice": {"type": "function", "function": {"name": tool_name}},
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(f"{base_url}/chat/completions", headers=headers, json=body)
    except httpx.RequestError as exc:
        raise ComplianceError(f"AI provider unreachable: {exc}") from exc

    if resp.status_code != 200:
        raise ComplianceError(f"AI provider error {resp.status_code}: {resp.text[:200]}", resp.status_code)

    tool_calls = (resp.json().get("choices") or [{}])[0].get("message", {}).get("tool_calls", [])
    if not tool_calls:
        raise ComplianceError("No structured response returned from AI")
    try:
        return json.loads(tool_calls[0]["function"]["arguments"])
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ComplianceError(f"Malformed tool-call arguments: {exc}") from exc


def assess_compliance(
    *,
    title: str,
    campaign_description: str,
    additional_documents: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Assess a campaign / AI use case against GDPR + the EU AI Act.

    additional_documents: optional [{"name": ..., "content": ...}] local policy docs
    (e.g. a German BDSG amendment) folded into the prompt.

    Returns the parsed `submit_compliance_assessment` payload (see ASSESSMENT_TOOL schema).
    """
    user = (
        "Please assess the following marketing campaign or use case for EU AI Act and "
        f"GDPR compliance:\n\n**Title:** {title}\n\n**Description:**\n{campaign_description}"
    )
    for doc in additional_documents or []:
        user += f"\n\n**Additional Local Compliance Documents:**\n\n--- Document: {doc.get('name', '')} ---\n{doc.get('content', '')}\n"

    return _call_tool(
        system=SYSTEM_PROMPT,
        user=user,
        tool=ASSESSMENT_TOOL,
        tool_name="submit_compliance_assessment",
    )
