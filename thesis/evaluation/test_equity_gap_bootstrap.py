"""Plain-assert self-test for equity_gap_bootstrap.py on synthetic items (no corpus).

Run from the repository root:  python3 thesis/evaluation/test_equity_gap_bootstrap.py
The items are invented for the test and mirror only the corpus's SHAPE (8 DE-source and
41 EN-source gold-escalate items); no number here is a thesis result.
"""
from __future__ import annotations

import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import equity_gap_bootstrap as eg  # noqa: E402


def make_items(de_hits: dict[str, list[bool]], en_hits: dict[str, list[bool]]) -> list[dict]:
    items = []
    n_de = len(next(iter(de_hits.values())))
    n_en = len(next(iter(en_hits.values())))
    for i in range(n_de):
        items.append({"id": f"DE-{i}", "language": "de",
                      "hits": {p: v[i] for p, v in de_hits.items()}})
    for i in range(n_en):
        items.append({"id": f"EN-{i}", "language": "en",
                      "hits": {p: v[i] for p, v in en_hits.items()}})
    return items


def pattern(n: int, k: int) -> list[bool]:
    return [i < k for i in range(n)]


def brute_force_permutation_p(items, a, b) -> float:
    """Enumerate every within-item swap on discordant items; reference for the exact test."""
    p = eg._paired(items, a, b)
    disc = [it for it in p if it["hits"][a] != it["hits"][b]]
    d_obs = eg.diff_of_gaps(p, a, b)
    count = 0
    total = 0
    for flips in itertools.product([False, True], repeat=len(disc)):
        swapped = []
        for it in p:
            hits = dict(it["hits"])
            swapped.append({"id": it["id"], "language": it["language"], "hits": hits})
        for it, flip in zip(disc, flips):
            if flip:
                tgt = next(s for s in swapped if s["id"] == it["id"])
                tgt["hits"][a], tgt["hits"][b] = tgt["hits"][b], tgt["hits"][a]
        d = eg.diff_of_gaps(swapped, a, b)
        total += 1
        if abs(d) >= abs(d_obs) - 1e-12:
            count += 1
    return count / total


def main() -> None:
    # --- 1. recalls and gaps on a corpus-shaped synthetic set ------------------------
    # ml: 5/8 DE, 39/41 EN;  llm: 7/8 DE, 36/41 EN;  floor: 0/8, 8/41  (hit patterns are
    # invented; the pairing between predictors is whatever the patterns give).
    de = {"floor": pattern(8, 0), "ml": pattern(8, 5), "llm": pattern(8, 7)}
    en = {"floor": pattern(41, 8), "ml": pattern(41, 39), "llm": pattern(41, 36)}
    items = make_items(de, en)
    r = eg.stratum_recall(items, "ml")
    assert r["de"]["n"] == 8 and r["de"]["hits"] == 5 and r["de"]["recall"] == 0.625
    assert r["en"]["n"] == 41 and r["en"]["hits"] == 39 and abs(r["en"]["recall"] - 0.9512) < 1e-4
    assert r["de"]["ci_low"] < 0.625 < r["de"]["ci_high"]
    assert 0.0 <= r["de"]["ci_low"] and r["en"]["ci_high"] <= 1.0
    g_ml = eg.gap(items, "ml")
    g_llm = eg.gap(items, "llm")
    assert abs(g_ml - (39 / 41 - 5 / 8)) < 1e-12
    assert abs(g_llm - (36 / 41 - 7 / 8)) < 1e-12
    d = eg.diff_of_gaps(items, "ml", "llm")
    assert abs(d - (g_ml - g_llm)) < 1e-12

    # --- 2. bootstrap: reproducible, contains the point estimate, symmetric on identical -
    b1 = eg.bootstrap_diff(items, "ml", "llm", resamples=400, seed=7)
    b2 = eg.bootstrap_diff(items, "ml", "llm", resamples=400, seed=7)
    assert b1 == b2, "bootstrap must be reproducible under a fixed seed"
    assert b1["ci_low"] <= round(d, 4) <= b1["ci_high"]
    assert b1["n_resamples"] == 400
    same = make_items({"a": pattern(8, 5), "b": pattern(8, 5)},
                      {"a": pattern(41, 30), "b": pattern(41, 30)})
    bs = eg.bootstrap_diff(same, "a", "b", resamples=200, seed=1)
    assert bs["ci_low"] == 0.0 and bs["ci_high"] == 0.0
    assert eg.permutation_exact(same, "a", "b")["p_two_sided"] == 1.0

    # --- 3. exact permutation equals brute-force enumeration on small discordant sets ---
    small_de = {"a": [True, True, False, False, True, False, True, False],
                "b": [True, False, False, True, True, False, False, False]}
    small_en = {"a": pattern(10, 8), "b": [True] * 6 + [False, False, True, True]}
    small = make_items(small_de, small_en)
    exact = eg.permutation_exact(small, "a", "b")
    brute = brute_force_permutation_p(small, "a", "b")
    assert abs(exact["p_two_sided"] - brute) < 1e-9, (exact, brute)
    assert exact["n_discordant_de"] == 3 and exact["n_discordant_en"] == 4
    assert 0.0 <= exact["p_two_sided"] <= 1.0

    # --- 4. a large, one-sided difference should be rare under the null ---------------
    strong = make_items({"a": pattern(8, 8), "b": pattern(8, 0)},
                        {"a": pattern(41, 0), "b": pattern(41, 41)})
    p_strong = eg.permutation_exact(strong, "a", "b")["p_two_sided"]
    assert p_strong < 0.001, p_strong
    assert abs(eg.diff_of_gaps(strong, "a", "b") - (-2.0)) < 1e-12

    # --- 5. missing predictions are dropped from pairs and reported -------------------
    partial = make_items({"a": pattern(8, 4), "b": pattern(8, 4)},
                         {"a": pattern(41, 20), "b": pattern(41, 20)})
    del partial[0]["hits"]["b"]
    assert eg.stratum_recall(partial, "b")["de"]["n_missing"] == 1
    assert len(eg._paired(partial, "a", "b")) == 48

    # --- 6. compare_all wires everything and keeps every pair --------------------------
    res = eg.compare_all(items, ["floor", "ml", "llm"], resamples=100, seed=3)
    assert {(p["predictor_a"], p["predictor_b"]) for p in res["pairs"]} == {
        ("floor", "ml"), ("floor", "llm"), ("ml", "llm")}
    for row in res["pairs"]:
        assert row["boot_ci_low"] <= row["diff_of_gaps_a_minus_b"] <= row["boot_ci_high"]
        assert 0.0 <= row["perm_p_two_sided"] <= 1.0
    assert res["per_predictor"]["floor"]["gap_en_minus_de"] == round(8 / 41, 4)

    print("test_equity_gap_bootstrap: all assertions passed (synthetic items only; "
          "the module has not been run on the corpus)")


if __name__ == "__main__":
    main()
