"""Plain-assert checks for predict_jev.py with the fake client (no key, no corpus, no network).
Run: python3 thesis/evaluation/test_predict_jev.py   (exits non-zero on failure)

Covers: the request the HTTP client sends and how it reads a reply and an error; the
retry policy; the corpus run (label file in the compare_runs.py shape, taxonomy file,
sidecar with gold and language, meta without the key); failure accounting (a failed
item is missing, never filled); the abort when most items fail; abstention thresholds
and re-cutting a saved run without a client; the golden-set mode on the product's
real golden_set.json.
"""
from __future__ import annotations

import dataclasses
import email.message
import io
import json
import os
import sys
import tempfile
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import compare_runs as CR
import predict_jev as PJ
from test_run_eval_smoke import SIGS

# Twelve synthetic signals with two journey stages and two owners so the routing
# questions (an inventory needs at least two entries) are part of the run.
SIGS2 = [dataclasses.replace(s, journey_stage="onboarding" if i % 2 else "support",
                             owner="cx_product" if i % 3 else "customer_operations")
         for i, s in enumerate(SIGS)]
PJ.load = lambda: list(SIGS2)

STATE = {"feedback": "Konto gesperrt, schrecklich"}
QUESTIONS = {"sentiment": PJ.SENTIMENT_Q, "risk": PJ.RISK_Q, "risk_level": PJ.RISK_LEVEL_Q, "escalate": PJ.ESCALATE_Q}


def _json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class _Reply:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _reply_payload() -> dict:
    return {"model": "jev-1.13.0", "usage": {"input_tokens": 321, "output_tokens": 0}, "answers": {
        "sentiment": {"type": "choice", "choice": "negative",
                      "probabilities": {"negative": 0.9, "neutral": 0.07, "positive": 0.03}, "confidence": 0.9},
        "risk": {"type": "choice", "choice": "critical",
                 "probabilities": {"low": 0.01, "medium": 0.04, "high": 0.25, "critical": 0.7}, "confidence": 0.7},
        "risk_level": {"type": "score", "score": 2.6, "legend": {str(i): lvl for i, lvl in enumerate(PJ.RISK_LEVEL_Q["criteria"])},
                       "probabilities": {"0": 0.02, "1": 0.05, "2": 0.24, "3": 0.69}, "confidence": 0.69},
        "escalate": {"type": "noul", "noul": 0.93},
    }}


def test_http_client_sends_the_documented_request_and_reads_the_reply() -> None:
    seen = {}

    def opener(req, timeout):
        seen["url"] = req.full_url
        seen["headers"] = {k.lower(): v for k, v in req.header_items()}
        seen["body"] = json.loads(req.data.decode("utf-8"))
        seen["timeout"] = timeout
        return _Reply(_reply_payload())

    client = PJ.JevHttpClient("k-test", base_url="https://api.typesafe.ai/", opener=opener)
    answers = client(STATE, QUESTIONS)
    assert seen["url"] == "https://api.typesafe.ai/v1/systemone"
    assert seen["headers"]["authorization"] == "Bearer k-test"
    assert seen["headers"]["content-type"] == "application/json"
    assert seen["body"] == {"state": STATE, "model": "jev-latest", "questions": QUESTIONS}
    assert seen["body"]["questions"]["risk_level"]["criteria"][3].startswith("critical:")
    assert set(seen["body"]["questions"]["escalate"]["criteria"]) == {"true", "false"}
    assert answers["sentiment"]["choice"] == "negative" and answers["escalate"]["noul"] == 0.93
    assert answers["_usage"] == {"input_tokens": 321, "output_tokens": 0} and answers["_model"] == "jev-1.13.0"
    assert answers["_latency_ms"] >= 0
    assert "k-test" not in repr({k: v for k, v in vars(client).items() if k != "_key"})
    assert client.label == "jev-latest at https://api.typesafe.ai"


def test_http_client_maps_errors_and_refuses_without_key() -> None:
    def opener_429(req, timeout):
        headers = email.message.Message()
        headers["Retry-After"] = "2"
        raise urllib.error.HTTPError(req.full_url, 429, "rate limited", headers, io.BytesIO(b'{"error":"slow down"}'))

    client = PJ.JevHttpClient("k", opener=opener_429)
    try:
        client(STATE, QUESTIONS)
    except PJ.JevError as err:
        assert err.status == 429 and err.retry_after == 2.0 and "slow down" in str(err)
    else:
        raise AssertionError("must raise")

    def opener_no_answers(req, timeout):
        return _Reply({"model": "x"})

    try:
        PJ.JevHttpClient("k", opener=opener_no_answers)(STATE, QUESTIONS)
    except PJ.JevError as err:
        assert "no answers" in str(err)
    else:
        raise AssertionError("must raise")
    try:
        PJ.JevHttpClient("")
    except SystemExit as exc:
        assert "TYPESAFE_API_KEY" in str(exc)
    else:
        raise AssertionError("must refuse an empty key")
    try:
        PJ.JevHttpClient("k", opener=opener_no_answers)(STATE, {})
    except PJ.JevError as err:
        assert "1 to 32" in str(err)
    else:
        raise AssertionError("must refuse an empty question set")


def test_retry_policy() -> None:
    waits = []
    client = PJ.FakeJev(rate_limit_first=True)
    answers = PJ.ask_with_retry(client, STATE, QUESTIONS, sleep=waits.append)
    assert client.calls == 2 and waits == [0.0] and answers["risk"]["type"] == "choice"

    failing = PJ.FakeJev(fail_ids={"schrecklich"})
    try:
        PJ.ask_with_retry(failing, STATE, QUESTIONS, sleep=waits.append)
    except PJ.JevError as err:
        assert err.status == 529 and failing.calls == 3 and waits[-2:] == [1.0, 2.0]
    else:
        raise AssertionError("must give up after three attempts")

    class Unauthorised:
        calls = 0

        def __call__(self, state, questions):
            self.calls += 1
            raise PJ.JevError("HTTP 401", status=401)

    client = Unauthorised()
    try:
        PJ.ask_with_retry(client, STATE, QUESTIONS, sleep=waits.append)
    except PJ.JevError as err:
        assert err.status == 401 and client.calls == 1  # no retry on a rejected key
    else:
        raise AssertionError("must raise")


def test_fake_client_is_deterministic_and_well_formed() -> None:
    a = PJ.FakeJev()(STATE, QUESTIONS)
    b = PJ.FakeJev()(STATE, QUESTIONS)
    assert {k: v for k, v in a.items() if not k.startswith("_")} == {k: v for k, v in b.items() if not k.startswith("_")}
    for name in ("sentiment", "risk"):
        probs = a[name]["probabilities"]
        assert abs(sum(probs.values()) - 1.0) < 1e-6 and a[name]["confidence"] == max(probs.values())
        assert a[name]["choice"] == max(probs, key=probs.get)
    assert 0.0 <= a["risk_level"]["score"] <= 3.0 and set(a["risk_level"]["legend"]) == {"0", "1", "2", "3"}
    assert 0.0 <= a["escalate"]["noul"] <= 1.0 and "confidence" not in a["escalate"]
    assert PJ.FakeJev.label.startswith("fake") and "never report" in PJ.FakeJev.label


def test_corpus_run_writes_the_harness_shapes() -> None:
    out = tempfile.mkdtemp(prefix="clara_jev_")
    assert PJ.main(["--client", "fake", "--out", out]) == 0
    rows = _json(os.path.join(out, "predictions_jev.json"))
    tax = _json(os.path.join(out, "predictions_jev_taxonomy.json"))
    side = _json(os.path.join(out, "jev_probabilities.json"))
    meta = _json(os.path.join(out, "predictions_jev.meta.json"))
    assert len(rows) == 12 and all(set(r) == {"id", "sentiment", "risk"} for r in rows)
    assert all(r["sentiment"] in PJ.SENT_LABELS and r["risk"] in PJ.RISK_LABELS for r in rows)
    assert len(tax) == 12 and all(r["journey_stage"] in ("onboarding", "support") for r in tax)
    assert all(r["owner"] in ("cx_product", "customer_operations") for r in tax)
    rec = {r["id"]: r for r in side["records"]}
    assert rec["S-1"]["gold"] == {"sentiment": "negative", "risk": "high", "journey_stage": "support",
                                  "owner": "customer_operations", "risk_level": "high", "escalate": True}
    assert rec["S-2"]["gold"]["journey_stage"] == "onboarding" and rec["S-2"]["gold"]["owner"] == "cx_product"
    assert rec["S-6"]["gold"]["sentiment"] is None and rec["S-6"]["gold"]["escalate"] is False
    assert rec["S-7"]["language"] == "de" and set(rec["S-7"]["answers"]) == {
        "sentiment", "risk", "risk_level", "escalate", "journey_stage", "owner"}
    assert meta["n_items"] == 12 and meta["n_answered"] == 12 and meta["n_failed"] == 0
    assert meta["mode"] == "corpus" and meta["abstain_threshold"] == 0.0 and meta["n_abstained"] == {}
    assert meta["client"].startswith("fake") and meta["usage"]["input_tokens"] > 0
    assert meta["models_seen"] == ["fake"] and rec["S-1"]["model"] == "fake"
    assert meta["estimated_cost_usd"] == round(meta["usage"]["input_tokens"] / 1e6 * PJ.USD_PER_MILLION_INPUT_TOKENS, 4)
    assert set(meta["questions"]) == {"sentiment", "risk", "risk_level", "escalate", "journey_stage", "owner"}
    assert set(meta["questions"]["owner"]["criteria"]) == {"cx_product", "customer_operations"}
    assert "api_key" not in json.dumps(meta).lower() and "TYPESAFE" not in json.dumps(side)
    # The label file scores through compare_runs.py unchanged, next to the keyword floor.
    acc, pairs, _ = CR.compare(SIGS2, {"floor": CR.floor_run(SIGS2), "jev": CR.load_run(os.path.join(out, "predictions_jev.json"))})
    jev = {r["task"]: r for r in acc if r["run"] == "jev"}
    assert jev["sentiment"]["n_valid"] == 10 and jev["sentiment"]["n_missing"] == 0 and jev["sentiment"]["n_outside_task"] == 2
    assert jev["risk"]["n_valid"] == 12 and {p["pair"] for p in pairs} == {"floor_vs_jev"}


def test_failed_items_are_missing_never_filled() -> None:
    out = tempfile.mkdtemp(prefix="clara_jev_")
    items, questions = PJ.corpus_items(SIGS2)
    client = PJ.FakeJev(fail_ids={"nothing special"})  # S-3's text
    records, meta = PJ.run(items, questions, client, sleep=lambda s: None, progress=lambda m: None)
    assert meta["n_answered"] == 11 and meta["n_failed"] == 1 and meta["failures"][0]["id"] == "S-3"
    assert client.calls == 11 + 3  # three attempts for the failing item
    paths = PJ.write_outputs(out, records, meta, threshold=0.0)
    acc, _, _ = CR.compare(SIGS2, {"floor": CR.floor_run(SIGS2), "jev": CR.load_run(paths["predictions"])})
    jev = {r["task"]: r for r in acc if r["run"] == "jev"}
    assert jev["risk"]["n_missing"] == 1 and jev["risk"]["n_valid"] == 11 and jev["risk"]["n_invalid"] == 0


def test_abort_when_most_items_fail() -> None:
    out = tempfile.mkdtemp(prefix="clara_jev_")
    original = PJ.resolve_client
    PJ.resolve_client = lambda name, **kw: PJ.FakeJev(fail_ids={"Konto", "App", "Geht", "Kein", "Sehr", "Nur", "okay"})
    try:
        assert PJ.main(["--client", "fake", "--out", out]) == 1
    finally:
        PJ.resolve_client = original
    assert not os.path.exists(os.path.join(out, "predictions_jev.json"))


def test_abstention_threshold_and_recut_from_sidecar() -> None:
    out = tempfile.mkdtemp(prefix="clara_jev_")
    assert PJ.main(["--client", "fake", "--out", out]) == 0
    sidecar = os.path.join(out, "jev_probabilities.json")
    recut = tempfile.mkdtemp(prefix="clara_jev_recut_")
    os.environ.pop("TYPESAFE_API_KEY", None)
    assert PJ.main(["--materialise", sidecar, "--abstain-threshold", "1.0", "--out", recut]) == 0
    rows = _json(os.path.join(recut, "predictions_jev.json"))
    meta = _json(os.path.join(recut, "predictions_jev.meta.json"))
    assert all(r["sentiment"] is None and r["risk"] is None for r in rows)
    assert meta["abstain_threshold"] == 1.0 and meta["n_abstained"]["risk"] == 12 and meta["n_abstained"]["owner"] == 12
    acc, pairs, _ = CR.compare(SIGS2, {"floor": CR.floor_run(SIGS2), "jev": CR.load_run(os.path.join(recut, "predictions_jev.json"))})
    jev = {r["task"]: r for r in acc if r["run"] == "jev"}
    assert jev["risk"]["n_invalid"] == 12 and jev["risk"]["accuracy_end_to_end"] == 0.0 and jev["risk"]["note"] == CR.NO_VALID_ROW
    assert pairs[0]["note"] == CR.NO_PAIR
    # A middling threshold keeps the confident answers and drops the rest, per field.
    records, _ = PJ.load_sidecar(sidecar)
    confs = sorted(r["answers"]["risk"]["confidence"] for r in records)
    mid = confs[6]
    label_rows, _, abstained = PJ.materialise(records, threshold=mid)
    assert sum(1 for r in label_rows if r["risk"] is None) == 6 == abstained["risk"]
    assert all((r["risk"] is None) == (rec["answers"]["risk"]["confidence"] < mid)
               for r, rec in zip(label_rows, records))
    assert PJ.label_from_answer({"type": "score", "probabilities": {"0": 0.2, "1": 0.8},
                                 "legend": {"0": "low: a", "1": "medium: b"}}, threshold=0.0) == "medium"
    assert PJ.label_from_answer({"type": "noul", "noul": 0.9}, threshold=0.0) is None
    assert PJ.label_from_answer("garbage", threshold=0.0) is None


def test_golden_mode_reads_the_product_golden_set() -> None:
    out = tempfile.mkdtemp(prefix="clara_jev_golden_")
    assert os.path.exists(PJ.GOLDEN_SET)
    assert PJ.main(["--client", "fake", "--golden", "--split", "held_out", "--out", out]) == 0
    rows = _json(os.path.join(out, "predictions_jev_golden.json"))
    side = _json(os.path.join(out, "jev_probabilities_golden.json"))
    meta = _json(os.path.join(out, "predictions_jev_golden.meta.json"))
    assert len(rows) == 30 and all(set(r) == {"id", "sentiment", "urgency", "category"} for r in rows)
    assert all(r["sentiment"] in PJ.GOLDEN_SENT_LABELS and r["urgency"] in PJ.RISK_LABELS
               and r["category"] in PJ.GOLDEN_CATEGORIES for r in rows)
    assert all(r["split"] == "held_out" and r["gold"]["sentiment"] and r["language"] in ("en", "de") for r in side["records"])
    assert meta["mode"] == "golden" and meta["split"] == "held_out" and set(meta["questions"]) == {"sentiment", "urgency", "category"}
    assert not os.path.exists(os.path.join(out, "predictions_jev_golden_taxonomy.json"))
    # The golden sidecar re-cuts under its own suffix.
    recut = tempfile.mkdtemp(prefix="clara_jev_golden_recut_")
    assert PJ.main(["--materialise", os.path.join(out, "jev_probabilities_golden.json"), "--out", recut]) == 0
    assert os.path.exists(os.path.join(recut, "predictions_jev_golden.json"))


def test_inventory_question_bounds() -> None:
    q = PJ.inventory_question("owner", ["a_team", "b_team"])
    assert q["type"] == "choice" and q["criteria"] == {"a_team": "a team", "b_team": "b team"}
    try:
        PJ.inventory_question("owner", ["only_one"])
    except SystemExit as exc:
        assert "2 to 255" in str(exc)
    else:
        raise AssertionError("must refuse a one-entry inventory")
    try:
        PJ.resolve_client("magic")
    except SystemExit as exc:
        assert "unknown client" in str(exc)
    else:
        raise AssertionError("must refuse")


if __name__ == "__main__":
    failures = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"ok   {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    sys.exit(1 if failures else 0)
