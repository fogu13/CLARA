"""Plain-assert checks for run_matrix.py: the dry run prints a matched plan and never a secret.
Run: python3 thesis/evaluation/test_run_matrix.py   (exits non-zero on failure)
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import run_matrix as RM  # noqa: E402


def test_plan_is_matched_and_named() -> None:
    models = [RM.parse_model("glm=GLM_BASE_URL:GLM_API_KEY:glm-5.2"),
              RM.parse_model("mistral=MISTRAL_BASE_URL:MISTRAL_API_KEY:mistral-small-2603")]
    steps = RM.plan(models, batch_size=25, out_root="/tmp/matrix")
    assert [s["step"] for s in steps] == ["glm_generic", "glm_production", "mistral_generic", "mistral_production", "compare"]
    production = [s for s in steps if s.get("prompt") == "production"]
    assert {s["batch_size"] for s in production} == {25}
    assert all("--batch-size" in s["command"] and "25" in s["command"] for s in production)
    assert all("--exemplars" in s["command"] and "on" in s["command"] for s in production)
    compare = steps[-1]["command"]
    assert "floor" in compare and any(x.startswith("ml=") for x in compare)
    assert sum(1 for x in compare if x.endswith("predictions_llm.json")) == 2
    assert sum(1 for x in compare if x.endswith("predictions_llm_production.json")) == 2


def test_dry_run_prints_variable_names_never_values() -> None:
    os.environ["GLM_API_KEY"] = "sk-this-must-never-print"
    os.environ["MISTRAL_API_KEY"] = "mk-this-must-never-print"
    out = io.StringIO()
    with redirect_stdout(out):
        code = RM.main(["--model", "glm=GLM_BASE_URL:GLM_API_KEY:glm-5.2",
                        "--model", "mistral=MISTRAL_BASE_URL:MISTRAL_API_KEY:mistral-small-2603",
                        "--batch-size", "25", "--out-root", tempfile.mkdtemp(prefix="clara_matrix_")])
    text = out.getvalue()
    assert code == 0 and "dry run" in text
    assert "must-never-print" not in text
    assert "AI_API_KEY=$GLM_API_KEY" in text and "AI_API_KEY=$MISTRAL_API_KEY" in text
    assert text.count("predict_llm_production.py") == 2 and text.count("predict_llm.py") == 2


def test_bad_specs_are_refused() -> None:
    for argv in (["--model", "glm=only-two:parts", "--model", "m=A:B:c", "--out-root", "/tmp/x"],
                 ["--model", "glm=A:B:c", "--out-root", "/tmp/x"],
                 ["--model", "glm=A:B:c", "--model", "glm=A:B:d", "--out-root", "/tmp/x"]):
        try:
            RM.main(argv)
        except SystemExit as exc:
            assert exc.code not in (0, None)
        else:
            raise AssertionError(f"{argv} must be refused")


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
