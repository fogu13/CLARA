"""Jev (TypeSafe System One) as a sixth predictor for the thesis harness.

Jev returns typed judgments with probabilities instead of text: a Choice over the
label set, a Score over ordered levels, a Noul (yes/no probability). That makes it a
natural fit for the harness's closed-set tasks and, unlike the generation-based
predictors, it exposes a probability per answer, so abstention and calibration can
be studied on the same run (calibration.py).

    TYPESAFE_API_KEY=... python3 predict_jev.py                    # the 188-signal thesis corpus (THESIS_DATA_DIR)
    TYPESAFE_API_KEY=... python3 predict_jev.py --golden           # the product's 100-item golden set
    python3 predict_jev.py --client fake                           # TEST DOUBLE: hashed distributions, not a model
    python3 predict_jev.py --materialise results/jev_probabilities.json --abstain-threshold 0.6
                                                                  # rewrite the label files from a saved run, no calls

One request per signal carries every question (they are answered in parallel, so a
request costs about the same time as one question):

    corpus: sentiment (Choice), risk (Choice, the primary label), risk_level (Score over
            the same four levels, kept for the calibration read), escalate (Noul on the
            high-or-critical boundary), journey_stage and owner (Choice over the gold
            inventory, the closed-set design of §3.5.2 that predict_llm.py --constrained
            uses)
    golden: sentiment (four classes, "mixed" included), urgency (Choice) and category

Writes into THESIS_RESULTS_DIR (or --out; a trial run must never overwrite the
reported files):

    predictions_jev.json            [{id, sentiment, risk}]          the compare_runs.py shape
    predictions_jev_taxonomy.json   [{id, journey_stage, owner}]     the score_taxonomy shape
    jev_probabilities.json          per item: every answer with its distribution, confidence,
                                    the gold label where the harness knows it, language,
                                    latency and token usage (the input of calibration.py)
    predictions_jev.meta.json       model, host, question texts, counts, usage, cost estimate
    (golden mode: predictions_jev_golden.json, jev_probabilities_golden.json, ...meta.json)

Score with:  python3 compare_runs.py floor ml=results/predictions_ml.json jev=<out>/predictions_jev.json
Then:        python3 calibration.py --sidecar <out>/jev_probabilities.json --out <out>

Abstention: a Choice answer whose confidence (its top probability) is below
--abstain-threshold is written as null. compare_runs.py counts it as invalid, so it is
wrong end-to-end and absent from the coverage-conditioned view; nothing is defaulted.
The default threshold is 0 (never abstain); --materialise re-cuts a saved run at any
threshold without a call, so one paid run serves every threshold.

Failures are counted, never filled: a signal whose request fails three times has no
row (missing in compare_runs.py). A run that scores fewer than half of the items is not
written, so a bad key or a blocked network cannot leave a thin file behind that looks
like a result.

Data handling: the thesis corpus is public, paraphrased and de-identified and the golden
set is synthetic, so sending them to the vendor raises no personal-data concern. The
endpoint is hosted in the United States only; this script is evaluation tooling and is
not wired into the product, whose EU residency gate (CLARA_AI_REQUIRE_EU) would refuse
the host. The key is read from the environment and never written to any output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.environ.get("THESIS_RESULTS_DIR") or os.path.join(HERE, "results")
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import baseline as bl
from load_datasets import load

DEFAULT_BASE_URL = "https://api.typesafe.ai"
SYSTEMONE_PATH = "/v1/systemone"
DEFAULT_MODEL = "jev-latest"
USD_PER_MILLION_INPUT_TOKENS = 0.042  # the vendor's published input price; output is free
MAX_QUESTIONS_PER_REQUEST = 32
MAX_CHOICE_OPTIONS = 255
TIMEOUT_S = float(os.environ.get("TYPESAFE_TIMEOUT_S") or 30)
GOLDEN_SET = os.path.normpath(os.path.join(HERE, "..", "..", "apps", "api", "app", "evals", "golden_set.json"))

SENT_LABELS = ["negative", "neutral", "positive"]
RISK_LABELS = ["low", "medium", "high", "critical"]
GOLDEN_SENT_LABELS = ["negative", "neutral", "positive", "mixed"]
GOLDEN_CATEGORIES = ["product_issue", "positive_trend", "churn_risk", "compliance_concern",
                     "content_clarity", "ux_friction", "campaign_performance"]
ESCALATE_FROM = {"high", "critical"}

# ---------------------------------------------------------------------------
# Question texts. They are the whole "prompt": Jev sees the state, the
# instructions and the criteria, nothing else. Kept as module constants so the
# meta file can record exactly what was asked.
# ---------------------------------------------------------------------------
SENTIMENT_Q = {
    "type": "choice",
    "instructions": ("What overall sentiment does the customer express in `feedback` about the "
                     "product or service? Judge the customer's own overall evaluation, not the "
                     "topic."),
    "criteria": {
        "negative": "Dissatisfied, complaining, frustrated or disappointed overall.",
        "neutral": ("Neither clearly satisfied nor clearly dissatisfied: factual, lukewarm, or "
                    "mixed with no dominant side."),
        "positive": "Satisfied, praising or recommending overall.",
    },
}
RISK_CRITERIA = {
    "low": ("No material problem for the customer: praise, a minor remark, a wish or a "
            "question, with no cost or harm."),
    "medium": ("A friction or annoyance the customer can work around: slow, confusing, "
               "unclear, a small inconvenience."),
    "high": ("A concrete failure with a cost to the customer that needs a fix: money wrongly "
             "charged, a refund not paid, an order failed or not delivered, a feature broken, "
             "repeated errors."),
    "critical": ("Severe harm or exposure needing immediate escalation: fraud or scam, "
                 "unauthorised access or transactions, an account blocked with money out of "
                 "reach, a safety, legal or regulatory exposure, or a public threat to leave."),
}
RISK_Q = {
    "type": "choice",
    "instructions": ("How severe is the business risk carried by `feedback` for the company's "
                     "relationship with this customer? Pick the one level that fits best."),
    "criteria": RISK_CRITERIA,
}
RISK_LEVEL_Q = {
    "type": "score",
    "instructions": ("How severe is the business risk carried by `feedback` for the company's "
                     "relationship with this customer? The levels are ordered from no problem "
                     "to severe harm."),
    "criteria": [f"{label}: {RISK_CRITERIA[label]}" for label in RISK_LABELS],
}
ESCALATE_Q = {
    "type": "noul",
    "instructions": ("Does `feedback` describe a problem serious enough that a customer-operations "
                     "lead must be alerted today? Yes when there is a concrete failure with a cost "
                     "to the customer, or worse (fraud, lost access to money, legal exposure). No "
                     "for praise, wishes, questions and frictions the customer can work around."),
    "criteria": {
        "true": "A concrete failure with a cost to the customer, or severe harm or exposure.",
        "false": "Praise, a wish, a question, or a friction the customer can work around.",
    },
}
URGENCY_Q = {
    "type": "choice",
    "instructions": ("How urgently must the company act on `feedback`? Pick the one level that "
                     "fits best."),
    "criteria": {
        "low": "No action needed soon: praise, a wish, a general remark.",
        "medium": "Worth acting on in the normal course of work: a friction or a clear request.",
        "high": ("Needs prompt action: a concrete failure that costs the customer money, time or "
                 "trust, or a customer at risk of leaving."),
        "critical": ("Needs action now: an outage, data loss, a security or compliance exposure, "
                     "or harm to many customers."),
    },
}
GOLDEN_SENTIMENT_Q = {
    "type": "choice",
    "instructions": ("What overall sentiment does the customer express in `feedback`? Judge the "
                     "customer's own evaluation, not the topic."),
    "criteria": {
        "negative": "Dissatisfied, complaining, frustrated or disappointed overall.",
        "neutral": "Neither satisfied nor dissatisfied: factual, lukewarm, a plain question.",
        "positive": "Satisfied, praising or recommending overall.",
        "mixed": "Clearly both: real praise and a real complaint in the same feedback.",
    },
}
CATEGORY_Q = {
    "type": "choice",
    "instructions": "Which one category best describes what `feedback` is about?",
    "criteria": {
        "product_issue": "Something is broken, failing, wrong or lost in the product or service.",
        "positive_trend": "Praise for something that works well or improved.",
        "churn_risk": "The customer signals they may leave, cancel or switch.",
        "compliance_concern": "Privacy, data protection, legal, regulatory or security worries.",
        "content_clarity": "Documentation, instructions, wording or communication is unclear or missing.",
        "ux_friction": "The product works but is hard, slow or confusing to use.",
        "campaign_performance": "Marketing, campaigns, offers or messaging and their relevance.",
    },
}


def _humanise(value: str) -> str:
    return value.replace("_", " ")


def inventory_question(field: str, values: list[str]) -> dict[str, Any]:
    """A Choice over the workspace inventory for a routing field (closed set)."""
    if not 2 <= len(values) <= MAX_CHOICE_OPTIONS:
        raise SystemExit(f"{field}: a choice takes 2 to {MAX_CHOICE_OPTIONS} options, got {len(values)}")
    what = {
        "journey_stage": ("At which stage of the customer journey does `feedback` arise? Choose "
                          "the one inventory entry that fits best."),
        "owner": ("Which team in the inventory should own the follow-up to `feedback`? Choose "
                  "the one entry that fits best."),
    }[field]
    return {"type": "choice", "instructions": what, "criteria": {v: _humanise(v) for v in values}}


# ---------------------------------------------------------------------------
# Clients. A client is a callable (state, questions) -> answers dict, the
# `answers` object of the response plus "_usage" and "_latency_ms".
# ---------------------------------------------------------------------------
class JevError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, retry_after: float | None = None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


class JevHttpClient:
    """Plain-stdlib client for POST {base_url}/v1/systemone (Bearer key)."""

    def __init__(self, api_key: str, *, base_url: str = DEFAULT_BASE_URL, model: str = DEFAULT_MODEL,
                 timeout_s: float = TIMEOUT_S, opener: Callable[..., Any] | None = None):
        if not api_key:
            raise SystemExit("set TYPESAFE_API_KEY (from the vendor console) to call the model")
        self._key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self._open = opener or urllib.request.urlopen
        self.label = f"{model} at {self.base_url}"

    def __call__(self, state: Any, questions: dict[str, dict]) -> dict[str, Any]:
        if not 1 <= len(questions) <= MAX_QUESTIONS_PER_REQUEST:
            raise JevError(f"a request takes 1 to {MAX_QUESTIONS_PER_REQUEST} questions, got {len(questions)}")
        body = json.dumps({"state": state, "model": self.model, "questions": questions}).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + SYSTEMONE_PATH, data=body, method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self._key}"},
        )
        started = time.monotonic()
        try:
            with self._open(req, timeout=self.timeout_s) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", "replace")[:400]
            retry_after = err.headers.get("Retry-After") if err.headers else None
            raise JevError(f"HTTP {err.code}: {detail}", status=err.code,
                           retry_after=float(retry_after) if retry_after else None) from err
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            raise JevError(f"request to {self.base_url} failed: {err}") from err
        latency_ms = (time.monotonic() - started) * 1000
        data = json.loads(raw)
        answers = data.get("answers") if isinstance(data, dict) else None
        if not isinstance(answers, dict):
            raise JevError("the reply carries no answers object")
        usage = data.get("usage") or {}
        return {**answers, "_usage": {"input_tokens": int(usage.get("input_tokens", 0)),
                                       "output_tokens": int(usage.get("output_tokens", 0))},
                "_latency_ms": round(latency_ms, 1), "_model": str(data.get("model", ""))}


def _unit(seed: str) -> float:
    digest = hashlib.blake2b(seed.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") / float(1 << 64)


class FakeJev:
    """TEST DOUBLE: deterministic distributions from a hash of (state, question). It carries
    no intelligence and exists so the pipeline, the sidecar and the calibration read can be
    tested without a key. Never report its output.

    `fail_ids` makes every request whose state contains one of those strings raise;
    `rate_limit_first` raises one 429 (with Retry-After 0) before the first success, so the
    retry path is exercised.
    """

    label = "fake (test double: hashed distributions; not a model; never report)"

    def __init__(self, *, fail_ids: set[str] | None = None, rate_limit_first: bool = False):
        self.fail_ids = fail_ids or set()
        self.rate_limit_first = rate_limit_first
        self.calls = 0

    def __call__(self, state: Any, questions: dict[str, dict]) -> dict[str, Any]:
        self.calls += 1
        text = json.dumps(state, sort_keys=True)
        if self.rate_limit_first:
            self.rate_limit_first = False
            raise JevError("HTTP 429: rate limited", status=429, retry_after=0.0)
        if any(marker in text for marker in self.fail_ids):
            raise JevError("HTTP 529: overloaded", status=529)
        out: dict[str, Any] = {}
        for name, q in questions.items():
            kind = q["type"]
            if kind == "noul":
                out[name] = {"type": "noul", "noul": round(_unit(f"{text}|{name}|noul"), 4)}
                continue
            keys = list(q["criteria"]) if kind == "choice" else [str(i) for i in range(len(q["criteria"]))]
            weights = [math.exp(4 * _unit(f"{text}|{name}|{k}")) for k in keys]
            total = sum(weights)
            probs = {k: w / total for k, w in zip(keys, weights)}
            top = max(probs, key=probs.get)
            if kind == "choice":
                out[name] = {"type": "choice", "choice": top, "probabilities": probs, "confidence": probs[top]}
            else:
                score = sum(int(k) * p for k, p in probs.items())
                out[name] = {"type": "score", "score": round(score, 4),
                             "legend": {str(i): lvl for i, lvl in enumerate(q["criteria"])},
                             "probabilities": probs, "confidence": probs[top]}
        n_tokens = 40 * len(questions) + len(text) // 4
        return {**out, "_usage": {"input_tokens": n_tokens, "output_tokens": 0}, "_latency_ms": 1.0,
                "_model": "fake"}


def resolve_client(name: str, *, api_key: str | None = None, base_url: str | None = None,
                   model: str | None = None):
    if name == "fake":
        return FakeJev()
    if name == "api":
        return JevHttpClient(api_key or os.environ.get("TYPESAFE_API_KEY", ""),
                             base_url=base_url or os.environ.get("TYPESAFE_BASE_URL") or DEFAULT_BASE_URL,
                             model=model or os.environ.get("TYPESAFE_MODEL") or DEFAULT_MODEL)
    raise SystemExit(f"unknown client {name!r}: use api or fake")


def ask_with_retry(client, state: Any, questions: dict[str, dict], *, attempts: int = 3,
                   sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    """Three attempts: 429 honours Retry-After (capped at 30 s), 529 and transport errors back
    off exponentially, 401/422 stop at once because retrying cannot fix them."""
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            return client(state, questions)
        except JevError as err:
            last = err
            if err.status in (401, 422):
                raise
            if attempt == attempts - 1:
                break
            wait = min(err.retry_after, 30.0) if err.retry_after is not None else float(2 ** attempt)
            sleep(wait)
    assert last is not None
    raise last


# ---------------------------------------------------------------------------
# Items: the harness corpus or the golden set, each item as a plain dict with
# the gold the harness knows so the sidecar can carry it.
# ---------------------------------------------------------------------------
def corpus_items(sigs) -> tuple[list[dict], dict[str, dict]]:
    sigs = [s for s in sigs if s.text]
    stages = sorted({s.journey_stage for s in sigs if s.journey_stage})
    owners = sorted({s.owner for s in sigs if s.owner})
    questions = {"sentiment": SENTIMENT_Q, "risk": RISK_Q, "risk_level": RISK_LEVEL_Q, "escalate": ESCALATE_Q}
    if len(stages) >= 2:
        questions["journey_stage"] = inventory_question("journey_stage", stages)
    if len(owners) >= 2:
        questions["owner"] = inventory_question("owner", owners)
    items = []
    for s in sigs:
        gold = {
            "sentiment": bl.gold_sentiment_from_stars(s.star_rating),
            "risk": s.risk if s.risk in RISK_LABELS else None,
            "journey_stage": s.journey_stage or None,
            "owner": s.owner or None,
        }
        gold["risk_level"] = gold["risk"]
        gold["escalate"] = (s.risk in ESCALATE_FROM) if gold["risk"] else None
        items.append({"id": s.id, "text": s.text, "language": s.language, "gold": gold})
    return items, questions


def golden_items(path: str = GOLDEN_SET, split: str = "all") -> tuple[list[dict], dict[str, dict]]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    questions = {"sentiment": GOLDEN_SENTIMENT_Q, "urgency": URGENCY_Q, "category": CATEGORY_Q}
    items = []
    for row in data:
        if split != "all" and row.get("split") != split:
            continue
        exp = row.get("expected") or {}
        items.append({"id": row["id"], "text": row["text"], "language": row.get("language", ""),
                      "split": row.get("split"),
                      "gold": {"sentiment": exp.get("sentiment"), "urgency": exp.get("urgency"),
                               "category": exp.get("category")}})
    return items, questions


# ---------------------------------------------------------------------------
# The run: one request per item, every question in it.
# ---------------------------------------------------------------------------
def run(items: list[dict], questions: dict[str, dict], client, *, sleep=time.sleep,
        progress: Callable[[str], None] = print) -> tuple[list[dict], dict]:
    started = time.monotonic()
    records, failures = [], []
    usage = {"input_tokens": 0, "output_tokens": 0}
    for i, item in enumerate(items, 1):
        state = {"feedback": item["text"]}
        try:
            answers = ask_with_retry(client, state, questions, sleep=sleep)
        except JevError as err:
            if err.status in (401, 422):
                raise SystemExit(f"stopping: {err}")
            failures.append({"id": item["id"], "error": str(err)[:200]})
            continue
        record = {"id": item["id"], "language": item.get("language", ""), "gold": item["gold"],
                  "answers": {name: answers.get(name) for name in questions},
                  "model": answers.get("_model"),
                  "latency_ms": answers.get("_latency_ms"), "usage": answers.get("_usage")}
        if "split" in item:
            record["split"] = item["split"]
        for key in ("input_tokens", "output_tokens"):
            usage[key] += int((answers.get("_usage") or {}).get(key, 0))
        records.append(record)
        if i % 20 == 0:
            progress(f"  answered {i}/{len(items)}")
    elapsed = round(time.monotonic() - started, 1)
    meta = {
        "written_at": datetime.now(UTC).isoformat(),
        "predictor": "jev",
        "client": getattr(client, "label", str(client)),
        "state_shape": "{feedback: <text>}",
        "questions": questions,
        "models_seen": sorted({str(r.get("model")) for r in records if r.get("model")}),
        "n_items": len(items), "n_answered": len(records), "n_failed": len(failures),
        "failures": failures[:50],
        "elapsed_s": elapsed,
        "usage": usage,
        "estimated_cost_usd": round(usage["input_tokens"] / 1e6 * USD_PER_MILLION_INPUT_TOKENS, 4),
        "sentiment_rule": "choice label as returned; no mixed class in the corpus questions",
        "risk_rule": "the risk Choice is the primary label; risk_level (Score) and escalate (Noul) are calibration reads",
    }
    return records, meta


# ---------------------------------------------------------------------------
# Materialising label files from a saved run (no calls).
# ---------------------------------------------------------------------------
def label_from_answer(answer: dict | None, *, threshold: float) -> str | None:
    """The Choice label, or None when the answer is absent, malformed, or its confidence is
    below the abstention threshold. A Score answer is mapped to its nearest level index name
    through the legend; a Noul answer has no label."""
    if not isinstance(answer, dict):
        return None
    kind = answer.get("type")
    try:
        if kind == "choice":
            probs = answer.get("probabilities") or {}
            choice = answer.get("choice")
            conf = float(answer.get("confidence", probs.get(choice, 0.0)))
            if choice is None or conf < threshold:
                return None
            return str(choice)
        if kind == "score":
            probs = {str(k): float(v) for k, v in (answer.get("probabilities") or {}).items()}
            if not probs:
                return None
            top = max(probs, key=probs.get)
            if probs[top] < threshold:
                return None
            legend = answer.get("legend") or {}
            return str(legend.get(top, top)).split(":")[0]
    except (TypeError, ValueError):
        return None
    return None


def materialise(records: list[dict], *, threshold: float) -> tuple[list[dict], list[dict], dict]:
    """(label rows, taxonomy rows, abstention counts) at one confidence threshold."""
    rows, tax_rows = [], []
    abstained = {}
    for rec in records:
        ans = rec.get("answers") or {}
        row = {"id": rec["id"]}
        for field in ("sentiment", "risk", "urgency", "category"):
            if field in ans:
                label = label_from_answer(ans[field], threshold=threshold)
                row[field] = label
                if label is None and isinstance(ans[field], dict):
                    abstained[field] = abstained.get(field, 0) + 1
        rows.append(row)
        if "journey_stage" in ans or "owner" in ans:
            tax = {"id": rec["id"]}
            for field in ("journey_stage", "owner"):
                if field in ans:
                    label = label_from_answer(ans[field], threshold=threshold)
                    tax[field] = label
                    if label is None and isinstance(ans[field], dict):
                        abstained[field] = abstained.get(field, 0) + 1
            tax_rows.append(tax)
    return rows, tax_rows, abstained


def write_outputs(out_dir: str, records: list[dict], meta: dict, *, threshold: float,
                  suffix: str = "") -> dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    rows, tax_rows, abstained = materialise(records, threshold=threshold)
    meta = {**meta, "abstain_threshold": threshold, "n_abstained": abstained}
    paths = {
        "predictions": os.path.join(out_dir, f"predictions_jev{suffix}.json"),
        "sidecar": os.path.join(out_dir, f"jev_probabilities{suffix}.json"),
        "meta": os.path.join(out_dir, f"predictions_jev{suffix}.meta.json"),
    }
    with open(paths["predictions"], "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1, ensure_ascii=False)
    if tax_rows:
        paths["taxonomy"] = os.path.join(out_dir, f"predictions_jev{suffix}_taxonomy.json")
        with open(paths["taxonomy"], "w", encoding="utf-8") as fh:
            json.dump(tax_rows, fh, indent=1, ensure_ascii=False)
    with open(paths["sidecar"], "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "records": records}, fh, indent=1, ensure_ascii=False)
    with open(paths["meta"], "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)
    return paths


def load_sidecar(path: str) -> tuple[list[dict], dict]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data["records"], data.get("meta") or {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--client", default="api", help="api | fake (test double)")
    parser.add_argument("--golden", action="store_true", help="score the product golden set instead of the corpus")
    parser.add_argument("--split", default="all", help="golden mode: all | optimization | held_out")
    parser.add_argument("--abstain-threshold", type=float, default=0.0,
                        help="write null for a Choice whose confidence is below this (default 0: never)")
    parser.add_argument("--materialise", metavar="SIDECAR",
                        help="rewrite the label files from a saved jev_probabilities*.json, no calls")
    parser.add_argument("--out", default=RESULTS)
    args = parser.parse_args(argv)
    if not 0.0 <= args.abstain_threshold <= 1.0:
        raise SystemExit("--abstain-threshold must be between 0 and 1")

    if args.materialise:
        records, meta = load_sidecar(args.materialise)
        suffix = "_golden" if meta.get("mode") == "golden" else ""
        paths = write_outputs(args.out, records, meta, threshold=args.abstain_threshold, suffix=suffix)
        print(f"re-cut {len(records)} saved answers at threshold {args.abstain_threshold} -> {paths['predictions']}")
        return 0

    client = resolve_client(args.client)
    if args.golden:
        items, questions = golden_items(split=args.split)
        suffix, mode = "_golden", "golden"
    else:
        items, questions = corpus_items(load())
        suffix, mode = "", "corpus"
    if not items:
        raise SystemExit("no items to score")
    print(f"{mode}: {len(items)} items, {len(questions)} questions per request, client {client.label}")
    records, meta = run(items, questions, client)
    meta["mode"] = mode
    if args.golden:
        meta["split"] = args.split
    if len(records) < max(1, len(items) // 2):
        print(f"ABORT: only {len(records)}/{len(items)} items answered; not writing predictions. "
              f"First failure: {meta['failures'][:1]}")
        return 1
    paths = write_outputs(args.out, records, meta, threshold=args.abstain_threshold, suffix=suffix)
    print(f"wrote {len(records)}/{len(items)} Jev answers ({client.label}); {meta['n_failed']} failed; "
          f"{meta['usage']['input_tokens']} input tokens, about ${meta['estimated_cost_usd']}; "
          f"{meta['elapsed_s']} s -> {paths['predictions']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
