"""Smallest runnable check that the metrics and baselines aren't silently broken.
Run: python evaluation/test_metrics.py   (exits non-zero on failure)
"""
import metrics as M
import baseline as bl


def test_perfect_and_known():
    # perfect prediction -> all 1.0
    s = M.score(["a", "b", "a"], ["a", "b", "a"])
    assert s["accuracy"] == 1.0 and s["f1_macro"] == 1.0, s
    # known 2/3 accuracy (metrics round to 4 dp)
    s = M.score(["a", "a", "b"], ["a", "b", "b"])
    assert abs(s["accuracy"] - 2 / 3) < 1e-3, s


def test_baseline_polarity():
    assert bl.predict_sentiment("This app is great and reliable") == "positive"
    assert bl.predict_sentiment("Account blocked, terrible, lost money") == "negative"
    assert bl.predict_sentiment("Die App ist schnell und zuverlässig") == "positive"
    # negation flips
    assert bl.predict_sentiment("not good at all") in ("negative", "neutral")


def test_baseline_risk_and_stars():
    assert bl.predict_risk("my account was blocked and funds frozen") == "critical"
    assert bl.predict_risk("the app is a bit slow") == "medium"
    assert bl.gold_sentiment_from_stars(1) == "negative"
    assert bl.gold_sentiment_from_stars(5) == "positive"
    assert bl.gold_sentiment_from_stars(None) is None


def test_mcnemar_exact():
    # no discordant pairs -> p = 1.0 by definition
    assert M.mcnemar_exact([True, False], [True, False]) == (0, 0, 1.0)
    # symmetric disagreement -> p = 1.0 (capped)
    b, c, p = M.mcnemar_exact([True, True, False, False], [False, False, True, True])
    assert (b, c) == (2, 2) and p == 1.0, (b, c, p)
    # one-sided sweep: b=0, c=8 -> p = 2 * C(8,0) / 2^8 = 2/256
    b, c, p = M.mcnemar_exact([False] * 8, [True] * 8)
    assert (b, c) == (0, 8) and abs(p - 2 / 256) < 1e-12, (b, c, p)
    # known asymmetric case: b=1, c=9 -> p = 2 * (C(10,0) + C(10,1)) / 2^10 = 22/1024
    a_ok = [True] + [False] * 9 + [True] * 5
    b_ok = [False] + [True] * 9 + [True] * 5
    b, c, p = M.mcnemar_exact(a_ok, b_ok)
    assert (b, c) == (1, 9) and abs(p - 22 / 1024) < 1e-12, (b, c, p)




def test_wilson_and_fisher():
    lo, hi = M.wilson_interval(66, 100)
    assert 0.56 < lo < 0.57 and 0.74 < hi < 0.75, (lo, hi)
    assert M.wilson_interval(10, 10) == (0.7225, 1.0)   # never a degenerate [1, 1]
    assert M.wilson_interval(0, 0) == (0.0, 0.0)
    # Fisher: checked against scipy.stats.fisher_exact on the same tables
    assert abs(M.fisher_exact(4, 6, 15, 3) - 0.034626) < 1e-5
    assert abs(M.fisher_exact(0, 5, 5, 0) - 0.007937) < 1e-5
    assert M.fisher_exact(7, 7, 7, 7) == 1.0
    assert M.fisher_exact(0, 0, 0, 0) == 1.0


def test_score_labels_restrict_the_macro_average():
    # A stray predicted label ("z") outside the restriction must not enter the macro.
    y_true = ["a", "a", "b", "b"]
    y_pred = ["a", "z", "b", "b"]
    unrestricted = M.score(y_true, y_pred)
    restricted = M.score(y_true, y_pred, labels=["a", "b"])
    assert restricted["f1_macro"] > unrestricted["f1_macro"], (restricted, unrestricted)
    assert restricted["accuracy"] == unrestricted["accuracy"] == 0.75
    assert restricted["accuracy_ci_low"] < 0.75 < restricted["accuracy_ci_high"]


def test_mcnemar_one_flip():
    # b=3, c=12 is significant; one pair moved toward the null is not.
    assert M.mcnemar_p_from_counts(3, 12) < 0.05 < M.mcnemar_one_flip_p(3, 12)
    assert M.mcnemar_one_flip_p(5, 5) == M.mcnemar_p_from_counts(5, 5) == 1.0
    assert M.mcnemar_one_flip_p(12, 3) == M.mcnemar_one_flip_p(3, 12)


def test_production_mapping():
    import predict_llm_production as P
    row = P.map_enrichment({"id": "TR-001", "sentiment": "mixed", "sentiment_score": 0.1,
                            "urgency": "high", "tags": ["checkout_failure"]})
    assert row["sentiment"] == "neutral" and row["sentiment_raw"] == "mixed"
    assert row["risk"] == "high" and row["urgency_raw"] == "high"
    none_row = P.map_enrichment({"id": "TR-002", "sentiment": None, "urgency": "medium", "tags": []})
    assert none_row["sentiment"] is None  # a rejected label is a miss, never coerced

if __name__ == "__main__":
    test_perfect_and_known()
    test_baseline_polarity()
    test_baseline_risk_and_stars()
    test_mcnemar_exact()
    test_wilson_and_fisher()
    test_score_labels_restrict_the_macro_average()
    test_mcnemar_one_flip()
    test_production_mapping()
    print("OK: all metric/baseline self-checks passed")
