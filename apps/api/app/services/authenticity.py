"""Ingestion-time authenticity review for incoming signals.

WHAT THIS IS FOR
Customers ask a reasonable question: "some of this feedback may be AI-generated —
can you flag it before it gets triaged and merged into insights?" This module
answers the honest version of that question.

WHAT IT DELIBERATELY DOES NOT DO
It does not claim, per comment, that a language model wrote it. That claim cannot
be made honestly on customer verbatims, and we measured it rather than assuming it.
On a corpus of 6,740 real feedback texts (6,154 platform-published reviews from
Apple/Trustpilot/Reddit feeds vs 586 texts we know a language model produced):

  * A conventional stylometric detector (no emoji, no typos, even sentence
    lengths, impersonal register), tuned to catch 81% of the known machine text,
    flagged 15.0% of REAL customer reviews. At a 1% AI base rate that is 5%
    precision: 95 of every 100 flags would be a real customer. At 5%, 78 of 100.
  * Those false flags skewed to ANGRIER reviews (mean 2.21 stars vs 2.70) — the
    filter preferentially silences serious complaints, which for a
    feedback-intelligence product is the worst possible failure direction.
  * Flag rates diverged 3.0x across languages (Greek 44.4%, Hungarian 41.7% vs
    Polish 14.8%, English 15.0%) — largely because the feature lexicon covered
    English/German cues and not the others. Coverage gaps become a systematic
    penalty against the languages the builder did not think about.
  * A Binoculars-style cross-perplexity detector (Hans et al. 2024, the strongest
    open zero-shot method) scored AUROC 0.326 on our English stratum: WORSE THAN
    CHANCE, and 0.512 (a coin flip) on German. At an 80%-recall operating point it
    flagged 89.8% of real reviews. The mechanism is structural: complaint text is
    formulaic and highly predictable, so genuine feedback sits at the
    low-perplexity end where these methods expect machine text. The sign of the
    signal even flips by language (EN real text 4.52 vs LLM 4.87 log-ppl; DE 3.82
    vs 3.48), so no single global threshold can be right in both.
  * 23% of real feedback texts are under 10 words. Nothing can classify those.

So: per-comment authorship attribution from text is refused, the way
outcome_engine refuses to fit an interrupted time series it cannot support.
What we ship instead are the things we can actually establish, and the human
decides what to exclude.

THE THREE TIERS
  Tier 1 KNOWN       declared/marked AI provenance, exact duplicates, channel facts.
  Tier 2 STRUCTURAL  duplication, template families, bursts, rating/text conflict,
                     batch-level uniformity. Cohort statistics with visible evidence.
  Tier 3 REFUSED     per-comment "this was written by AI". Not shipped; see above.

Nothing here removes a signal. Like annotate_near_duplicates, findings are stamped
into metadata and surfaced for a human decision, because silently dropping customer
feedback trades an inflation bias for a deletion bias.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.models import SignalRecord
from app.services.common import normalize_timestamp

# --------------------------------------------------------------------------- #
# Channel trust. What we know about HOW a signal arrived is worth more than any
# guess about who wrote it: platform connectors pull from sources that run their
# own fraud enforcement, while a pasted CSV carries no upstream verification at
# all. Measured support: across 6,154 platform-pulled reviews we found ZERO
# near-duplicate pairs at the shipped Jaccard 0.85 threshold and only 5 exact
# repeats — the upstream platforms had already removed coordinated content.
# Untrusted channels are therefore where this review is worth running.
# --------------------------------------------------------------------------- #
TRUSTED_CHANNELS = frozenset({"zendesk", "trustpilot", "app_store", "apple_app_store",
                              "google_play", "google_business", "connector"})
SEMI_TRUSTED_CHANNELS = frozenset({"webhook", "ingest_webhook", "api"})

# Below this, no structural statistic about a single text means anything. 23% of
# a real corpus falls here; we say so rather than guessing.
MIN_ASSESSABLE_WORDS = 10
# Signals this short carry almost no information for synthesis regardless of who
# wrote them (14.7% of the measured corpus). Surfaced as a quality note, never as
# an authenticity accusation.
LOW_INFORMATION_WORDS = 6
# A batch must be at least this large before batch-level uniformity is computed:
# variance estimates on a handful of texts are noise, and this is the whole reason
# the uniformity claim is made about cohorts rather than individual comments.
MIN_BATCH_FOR_UNIFORMITY = 25
# Coefficient of variation of text length across a batch. Human feedback batches
# in the measured corpus sit well above this; a batch of near-identical-length
# texts from an unverified channel is worth a human look.
UNIFORM_LENGTH_CV = 0.25
# Volume on one day this many times the trailing median for the same source is a
# question, not a verdict: the measured corpus shows genuine 21x launch-day spikes
# (Chase, 42 reviews on 2026-08-05). The UI must phrase it as a question.
BURST_MULTIPLE = 8.0
MIN_BURST_COUNT = 12
# Equity guardrail. If the highest-flagged language stratum exceeds the lowest by
# this ratio, we warn IN the review queue before anyone excludes anything. Our own
# naive-filter measurement produced a 3.0x disparity, which is exactly the kind of
# quiet harm this product's evaluation methodology exists to catch.
DISPARITY_WARN_RATIO = 2.0
MIN_STRATUM_FOR_DISPARITY = 50
# and at least this many actual flags in the top stratum, so a 5-of-30 blip does
# not cry wolf and train people to ignore the guardrail.
MIN_FLAGS_FOR_DISPARITY = 5

_WORD = re.compile(r"[a-zà-ÿäöüßα-ωа-я0-9']+", re.IGNORECASE)

# Explicit declarations of machine generation. This is the ONLY per-signal
# AI-authorship determination we make, because it is a fact carried with the
# content rather than an inference from style. EU AI Act Art 50(2) machine-readable
# marking makes this class of evidence more common over time, not less.
#
# The naive version of this pattern is a trap in THIS domain specifically, and we
# caught it by running against 6,154 real reviews: customers constantly complain
# about the company's AI. The single false positive it produced was a long, careful
# complaint containing "I don't know if the reply to my review was generated by AI
# or written by real person" — the reviewer was criticising the vendor's chatbot,
# and a keyword match would have flagged their genuine complaint as machine-written.
# So a declaration must be SELF-referential, and anything pointing at a reply, bot
# or support agent disqualifies the match.
_MODEL_BOILERPLATE = re.compile(
    r"\bas an (?:ai|artificial intelligence) language model\b"
    r"|\bi (?:cannot|can't) (?:browse|access) the internet\b"
    r"|\bi'?m sorry,? but as an ai\b",
    re.IGNORECASE,
)
_SELF_DECLARED = re.compile(
    r"\b(?:this|my|the above|der obige|dieser|diese|meine)\s+"
    r"(?:review|comment|text|feedback|post|bewertung|rezension|kommentar)\b"
    r"[^.!?]{0,60}?\b(?:ai[- ]generated|generated (?:by|with) (?:ai|chatgpt|gpt|claude|gemini)"
    r"|written (?:by|with) (?:ai|chatgpt)|ki[- ]generiert|mit ki (?:erstellt|geschrieben)"
    r"|automatisch erstellt)\b",
    re.IGNORECASE,
)
# If the AI mention sits near any of these, it is about the COMPANY's automation,
# not about the reviewer's own text.
_ABOUT_THEIR_AI = re.compile(
    r"\b(reply|replies|response|responded|answer|support|chat|chatbot|bot|assistant|agent"
    r"|antwort|antworten|support|kundenservice|chatbot|assistent)\b",
    re.IGNORECASE,
)


def _declares_ai_authorship(text: str) -> str | None:
    """Return the matched declaration, or None. Self-referential matches only."""
    m = _MODEL_BOILERPLATE.search(text)
    if m:
        return m.group(0)
    m = _SELF_DECLARED.search(text)
    if not m:
        return None
    lo = max(0, m.start() - 80)
    hi = min(len(text), m.end() + 80)
    if _ABOUT_THEIR_AI.search(text[lo:hi]):
        return None
    return m.group(0)


@dataclass(frozen=True)
class Reason:
    """One finding, in the product's own idiom: a code, a sentence a human can
    act on, and the evidence behind it. No probability is attached anywhere,
    because we have none that would survive being called one."""

    code: str
    message: str
    evidence: str = ""
    scope: str = "signal"  # "signal" | "batch"


@dataclass
class SignalVerdict:
    signal_id: str
    state: str  # "assessable" | "insufficient_text"
    band: str  # "routine" | "review_suggested"
    reasons: list[Reason] = field(default_factory=list)

    @property
    def codes(self) -> list[str]:
        return [r.code for r in self.reasons]


@dataclass
class BatchAssessment:
    verdicts: dict[str, SignalVerdict] = field(default_factory=dict)
    batch_reasons: list[Reason] = field(default_factory=list)
    channel: str = "unknown"
    channel_trust: str = "unverified"
    assessed: int = 0
    abstained: int = 0
    flagged: int = 0
    flag_rate_by_language: dict[str, float] = field(default_factory=dict)
    disparity_warning: str | None = None

    def summary(self) -> dict[str, object]:
        return {
            "channel": self.channel,
            "channel_trust": self.channel_trust,
            "assessed": self.assessed,
            "abstained_insufficient_text": self.abstained,
            "review_suggested": self.flagged,
            "batch_reasons": [r.code for r in self.batch_reasons],
            "flag_rate_by_language": self.flag_rate_by_language,
            "disparity_warning": self.disparity_warning,
        }


def _words(text: str) -> list[str]:
    return _WORD.findall(text.casefold())


def channel_trust(source: str) -> str:
    s = (source or "").strip().casefold()
    if s in TRUSTED_CHANNELS or any(s.startswith(c) for c in TRUSTED_CHANNELS):
        return "platform_verified"
    if s in SEMI_TRUSTED_CHANNELS:
        return "authenticated_channel"
    return "unverified"


def _day(record: SignalRecord) -> str:
    # normalize_timestamp returns (iso_string, was_coerced) — take the string.
    try:
        return normalize_timestamp(record.timestamp)[0][:10]
    except Exception:
        return (record.timestamp or "")[:10]


def _burst_reason(new_records: list[SignalRecord], existing: list[SignalRecord]) -> Reason | None:
    """Volume spike for the same source, relative to its own trailing median.

    Deliberately a batch-level question. The measured corpus contains genuine
    21x spikes on product-launch days, so this can never be an accusation."""
    if len(new_records) < MIN_BURST_COUNT:
        return None
    sources = Counter(r.source for r in new_records)
    source, count = sources.most_common(1)[0]
    history: Counter[str] = Counter()
    for r in existing:
        if r.source == source:
            day = _day(r)
            if day:
                history[day] += 1
    if len(history) < 5:
        return None
    median = statistics.median(history.values()) or 1
    ratio = count / median
    if ratio < BURST_MULTIPLE:
        return None
    return Reason(
        code="volume_burst",
        message=f"This batch is {ratio:.0f}x the usual daily volume for {source}.",
        evidence=f"{count} signals in this batch vs a median of {median:g}/day across "
                 f"{len(history)} prior days. Product launches and incidents do this too — "
                 f"check whether something happened before treating it as suspicious.",
        scope="batch",
    )


def _uniformity_reason(records: list[SignalRecord], trust: str) -> Reason | None:
    """Batch-level structural uniformity.

    This is the closest thing here to an 'AI-likeness' signal, and it is
    deliberately only ever computed over a COHORT, never a comment. Per-comment
    style judgement measured 15% false positives with a 3x language disparity;
    a variance statistic over 25+ texts is a far more stable claim. Only applied
    to channels with no upstream verification."""
    if trust == "platform_verified" or len(records) < MIN_BATCH_FOR_UNIFORMITY:
        return None
    lengths = [len(_words(r.feedback_text)) for r in records]
    lengths = [n for n in lengths if n >= MIN_ASSESSABLE_WORDS]
    if len(lengths) < MIN_BATCH_FOR_UNIFORMITY:
        return None
    mean = statistics.mean(lengths)
    if mean <= 0:
        return None
    cv = statistics.pstdev(lengths) / mean
    if cv >= UNIFORM_LENGTH_CV:
        return None
    return Reason(
        code="uniform_batch_structure",
        message="Signals in this batch are unusually uniform in length and structure.",
        evidence=f"Length varies by only {cv:.0%} across {len(lengths)} signals "
                 f"(mean {mean:.0f} words). Bulk-generated or template-filled content "
                 f"looks like this; so does a fixed-format survey export. It says "
                 f"nothing about any individual comment.",
        scope="batch",
    )


def assess_batch(
    new_records: list[SignalRecord],
    existing: list[SignalRecord] | None = None,
    *,
    channel: str | None = None,
) -> BatchAssessment:
    """Review an incoming batch and stamp findings into each record's metadata.

    Mutates metadata (flat string keys, matching the near_duplicate_of
    precedent) and returns the assessment for the ingest response. Never drops,
    reorders or rewrites a signal."""
    existing = existing or []
    records = list(new_records)
    source = channel or (records[0].source if records else "unknown")
    trust = channel_trust(source)

    assessment = BatchAssessment(channel=source, channel_trust=trust)

    # ---- batch-level findings first: they attach to every signal in the batch
    for reason in (_burst_reason(records, existing), _uniformity_reason(records, trust)):
        if reason:
            assessment.batch_reasons.append(reason)

    seen_text: dict[str, str] = {}
    for r in existing:
        key = " ".join(_words(r.feedback_text))
        if key:
            seen_text.setdefault(key, r.signal_id)

    lang_totals: Counter[str] = Counter()
    lang_flagged: Counter[str] = Counter()

    for record in records:
        text = record.feedback_text or ""
        words = _words(text)
        reasons: list[Reason] = []

        # Tier 1: a fact carried with the content, not an inference about style.
        declaration = _declares_ai_authorship(text)
        if declaration:
            reasons.append(Reason(
                code="declared_ai_generated",
                message="This comment states that it was AI-generated.",
                evidence=f'The text itself declares machine authorship ("{declaration.strip()}"). '
                         f"Complaints about the company's own chatbot do not count.",
            ))

        # Tier 1: exact repetition. Distinct from the fuzzy near-duplicate pass,
        # which runs separately and stamps near_duplicate_of.
        key = " ".join(words)
        if key and key in seen_text:
            reasons.append(Reason(
                code="exact_duplicate",
                message="Identical text already exists in this workspace.",
                evidence=f"Same wording as signal {seen_text[key]}.",
            ))
        elif key:
            seen_text[key] = record.signal_id

        # Tier 2: quality note. Not an authenticity claim, and labelled as such.
        if 0 < len(words) < LOW_INFORMATION_WORDS:
            reasons.append(Reason(
                code="low_information",
                message="Too short to carry a theme into an insight.",
                evidence=f"{len(words)} words. This is a usefulness note, not a "
                         f"suspicion about who wrote it.",
            ))

        # Abstention. The honest state for most customer verbatims.
        if len(words) < MIN_ASSESSABLE_WORDS:
            state = "insufficient_text"
            assessment.abstained += 1
        else:
            state = "assessable"
            assessment.assessed += 1

        # Batch findings are deliberately NOT folded into a signal's band. A
        # uniform-looking batch is a question about the cohort; letting it mark
        # every comment inside as "review suggested" would (a) re-create the
        # per-comment accusation this design refuses to make, and (b) flatten the
        # per-language flag rates that the equity guardrail depends on.
        actionable = [r for r in reasons if r.code != "low_information"]
        band = "review_suggested" if actionable else "routine"
        verdict = SignalVerdict(record.signal_id, state, band, reasons)
        assessment.verdicts[record.signal_id] = verdict

        lang = (record.language or "unknown").casefold()
        lang_totals[lang] += 1
        if band == "review_suggested":
            lang_flagged[lang] += 1
            assessment.flagged += 1

        _stamp(record, verdict, trust, assessment.batch_reasons)

    # ---- equity guardrail: does this filter fall unevenly across languages?
    rates = {
        lang: lang_flagged[lang] / total
        for lang, total in lang_totals.items()
        if total >= MIN_STRATUM_FOR_DISPARITY
    }
    assessment.flag_rate_by_language = {k: round(v, 4) for k, v in sorted(rates.items())}
    if len(rates) >= 2:
        hi_lang = max(rates, key=rates.get)
        lo_lang = min(rates, key=rates.get)
        hi, lo = rates[hi_lang], rates[lo_lang]
        if (lang_flagged[hi_lang] >= MIN_FLAGS_FOR_DISPARITY
                and hi > 0 and (lo == 0 or hi / lo >= DISPARITY_WARN_RATIO)):
            assessment.disparity_warning = (
                f"This review is flagging {hi_lang} signals at {hi:.0%} versus "
                f"{lo_lang} at {lo:.0%}. Check the flagged {hi_lang} signals before "
                f"excluding anything — uneven filtering silences some customers more "
                f"than others."
            )
    return assessment


def _stamp(
    record: SignalRecord,
    verdict: SignalVerdict,
    trust: str,
    batch_reasons: list[Reason] | None = None,
) -> None:
    """Flat string keys only: SignalRecord.metadata is dict[str, str], and the
    near_duplicate_of precedent keeps annotations flat and greppable.

    Batch findings are stamped under a separate key so the UI can show them as
    cohort context without them reading as a verdict on this comment."""
    record.metadata["authenticity_state"] = verdict.state
    record.metadata["authenticity_band"] = verdict.band
    record.metadata["authenticity_channel_trust"] = trust
    if verdict.reasons:
        record.metadata["authenticity_reasons"] = ",".join(sorted({r.code for r in verdict.reasons}))
        record.metadata["authenticity_note"] = " ".join(r.message for r in verdict.reasons)[:400]
    if batch_reasons:
        record.metadata["authenticity_batch_flags"] = ",".join(sorted({r.code for r in batch_reasons}))


def flag_rate_by_language(records: list[SignalRecord]) -> dict[str, float]:
    """Standing equity metric over already-assessed signals, for the model card
    and for the works-council evidence pack."""
    totals: Counter[str] = Counter()
    flagged: Counter[str] = Counter()
    for r in records:
        lang = (r.language or "unknown").casefold()
        totals[lang] += 1
        if r.metadata.get("authenticity_band") == "review_suggested":
            flagged[lang] += 1
    return {
        lang: round(flagged[lang] / total, 4)
        for lang, total in sorted(totals.items())
        if total >= MIN_STRATUM_FOR_DISPARITY
    }
