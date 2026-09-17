"""Plain-assert checks for predict_embedding.py with the hash test double (no model, no corpus).
Run: python3 thesis/evaluation/test_predict_embedding.py   (exits non-zero on failure)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import predict_embedding as PE  # noqa: E402
from test_run_eval_smoke import SIGS  # noqa: E402

PE.load = lambda: list(SIGS) * 3  # 36 synthetic signals: enough for two classes per task at five each


def test_hash_embedder_is_deterministic_and_normalised() -> None:
    a = PE.hash_embed(["Transaction history cannot be exported", "works well"])
    b = PE.hash_embed(["Transaction history cannot be exported", "works well"])
    assert a == b and len(a[0]) == PE.HASH_DIMS
    assert abs(sum(v * v for v in a[0]) - 1.0) < 1e-9
    assert a[0] != a[1]


def test_predictions_are_written_in_the_compare_runs_shape() -> None:
    out = tempfile.mkdtemp(prefix="clara_embedding_")
    assert PE.main(["--embedder", "hash", "--out", out]) == 0
    rows = json.load(open(os.path.join(out, "predictions_embedding.json"), encoding="utf-8"))
    meta = json.load(open(os.path.join(out, "predictions_embedding.meta.json"), encoding="utf-8"))
    assert isinstance(rows, list) and all("id" in r for r in rows)
    assert all(r.get("sentiment") in (None, "negative", "neutral", "positive") for r in rows)
    assert all(r.get("risk") in (None, *PE.RISK) for r in rows)
    assert meta["embedder"].startswith("hash") and "not a learned embedding" in meta["embedder"]
    assert meta["tasks"]["sentiment"]["n_predicted"] > 0 and meta["tasks"]["risk"]["folds"] >= 2
    assert meta["dimensions"] == PE.HASH_DIMS


def test_unknown_embedder_is_refused() -> None:
    try:
        PE.resolve_embedder("magic")
    except SystemExit as exc:
        assert "unknown embedder" in str(exc)
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
