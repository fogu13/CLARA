"""Prompt-and-pipeline configuration x model rerun: {generic prompt, production stage} x
{model A, model B}, one day, one command (§5A.4.2; the rerun Chapter 6 lists as not run).
The two configurations are not batch-matched by design: the generic prompt scores one
item per call and the production stage batches items at the requested size, so the
contrast is the configuration as each is used, not the prompt alone. DESIGN below states
this and is written into the manifest and printed in the dry run.

    python3 thesis/evaluation/run_matrix.py \
        --model glm=GLM_BASE_URL:GLM_API_KEY:glm-5.2 \
        --model mistral=MISTRAL_BASE_URL:MISTRAL_API_KEY:mistral-small-2603 \
        --batch-size 25 --out-root thesis/evaluation/results_matrix_$(date +%F) [--execute]

Each --model names a label, the environment variable holding the provider's base URL,
the environment variable holding its API key, and the model id. The script reads the
key variables only at execution time, passes them to the child processes, and never
prints them; --dry-run (the default) prints the plan with the variable NAMES.

Plan, per model: predict_llm.py (the generic prompt, one call per signal) and
predict_llm_production.py --exemplars on --batch-size N (the artifact's own stage), each
into its own results folder under --out-root; then compare_runs.py over the floor, the
learned model and the four new runs, into --out-root. A MANIFEST.json records the date,
the batch size, the model ids, the git commit and each step's exit status and elapsed
time, so the run is citable as one matched design rather than four dated files.

Cost: four passes over the 188-signal corpus (two per-item passes and two batched
passes). The reported runs are never overwritten: nothing is written under results/.
Not executed at the time of writing.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import UTC, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGN = ("prompt-and-pipeline configuration × model, one day: generic prompt per item, "
          "production stage batched at the requested size")


def parse_model(spec: str) -> dict[str, str]:
    try:
        label, rest = spec.split("=", 1)
        base_env, key_env, model_id = rest.split(":", 2)
    except ValueError as exc:
        raise SystemExit(f"--model expects label=BASE_URL_ENV:API_KEY_ENV:model-id, got {spec!r}") from exc
    if not label or not base_env or not key_env or not model_id:
        raise SystemExit(f"--model expects label=BASE_URL_ENV:API_KEY_ENV:model-id, got {spec!r}")
    return {"label": label, "base_env": base_env, "key_env": key_env, "model": model_id}


def plan(models: list[dict[str, str]], *, batch_size: int, out_root: str, python: str = sys.executable) -> list[dict]:
    steps: list[dict] = []
    for m in models:
        for prompt in ("generic", "production"):
            results_dir = os.path.join(out_root, f"{m['label']}_{prompt}")
            if prompt == "generic":
                command = [python, os.path.join(HERE, "predict_llm.py")]
            else:
                command = [python, os.path.join(HERE, "predict_llm_production.py"),
                           "--exemplars", "on", "--batch-size", str(batch_size)]
            steps.append({
                "step": f"{m['label']}_{prompt}",
                "model": m["model"],
                "prompt": prompt,
                "batch_size": batch_size if prompt == "production" else 1,
                "env_names": {"AI_BASE_URL": m["base_env"], "AI_API_KEY": m["key_env"], "AI_MODEL": "(literal)"},
                "results_dir": results_dir,
                "command": command,
            })
    runs = ["floor", f"ml={os.path.join(HERE, 'results', 'predictions_ml.json')}"]
    for m in models:
        runs.append(f"{m['label']}_generic={os.path.join(out_root, m['label'] + '_generic', 'predictions_llm.json')}")
        runs.append(f"{m['label']}_production={os.path.join(out_root, m['label'] + '_production', 'predictions_llm_production.json')}")
    steps.append({
        "step": "compare",
        "command": [python, os.path.join(HERE, "compare_runs.py"), "--out-dir", out_root, *runs],
        "results_dir": out_root,
    })
    return steps


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=HERE, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def render(steps: list[dict]) -> str:
    lines = []
    for s in steps:
        env = ""
        if "env_names" in s:
            env = (f"AI_BASE_URL=${s['env_names']['AI_BASE_URL']} AI_API_KEY=${s['env_names']['AI_API_KEY']} "
                   f"AI_MODEL={s['model']} THESIS_RESULTS_DIR={s['results_dir']} ")
        lines.append(f"[{s['step']}] {env}{shlex.join(s['command'])}")
    return "\n".join(lines)


def execute(steps: list[dict], *, batch_size: int, out_root: str, models: list[dict[str, str]]) -> int:
    os.makedirs(out_root, exist_ok=True)
    manifest = {
        "design": DESIGN,
        "started_at": datetime.now(UTC).isoformat(),
        "batch_size": batch_size,
        "models": [{"label": m["label"], "model": m["model"], "base_url_env": m["base_env"]} for m in models],
        "harness_git_commit": _git_commit(),
        "steps": [],
    }
    for s in steps:
        env = dict(os.environ)
        if "env_names" in s:
            base = os.environ.get(s["env_names"]["AI_BASE_URL"])
            key = os.environ.get(s["env_names"]["AI_API_KEY"])
            if not base or not key:
                print(f"[{s['step']}] {s['env_names']['AI_BASE_URL']} or {s['env_names']['AI_API_KEY']} is unset; stopping")
                manifest["steps"].append({"step": s["step"], "status": "skipped: credentials unset"})
                break
            env.update({"AI_BASE_URL": base, "AI_API_KEY": key, "AI_MODEL": s["model"],
                        "THESIS_RESULTS_DIR": s["results_dir"]})
            os.makedirs(s["results_dir"], exist_ok=True)
        started = time.monotonic()
        print(f"[{s['step']}] running")
        proc = subprocess.run(s["command"], env=env, cwd=HERE)
        entry = {"step": s["step"], "exit_code": proc.returncode, "elapsed_s": round(time.monotonic() - started, 1),
                 "model": s.get("model"), "prompt": s.get("prompt"), "batch_size": s.get("batch_size")}
        manifest["steps"].append(entry)
        if proc.returncode != 0:
            print(f"[{s['step']}] failed with exit code {proc.returncode}; stopping")
            break
    manifest["finished_at"] = datetime.now(UTC).isoformat()
    with open(os.path.join(out_root, "MANIFEST.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    return 0 if all(e.get("exit_code") == 0 for e in manifest["steps"]) and len(manifest["steps"]) == len(steps) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", action="append", required=True, help="label=BASE_URL_ENV:API_KEY_ENV:model-id")
    parser.add_argument("--batch-size", type=int, default=25, help="production batch size for every model (default 25)")
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--execute", action="store_true", help="run the plan (default: print it)")
    args = parser.parse_args(argv)
    models = [parse_model(spec) for spec in args.model]
    if len(models) < 2:
        raise SystemExit("the matrix needs at least two --model entries")
    if len({m["label"] for m in models}) != len(models):
        raise SystemExit("model labels must be distinct")
    steps = plan(models, batch_size=args.batch_size, out_root=args.out_root)
    print(f"design: {DESIGN}")
    print(render(steps))
    if not args.execute:
        print("\ndry run: nothing executed (pass --execute to run; credentials are read from the named variables)")
        return 0
    return execute(steps, batch_size=args.batch_size, out_root=args.out_root, models=models)


if __name__ == "__main__":
    sys.exit(main())
