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


if __name__ == "__main__":
    test_perfect_and_known()
    test_baseline_polarity()
    test_baseline_risk_and_stars()
    test_mcnemar_exact()
    print("OK: all metric/baseline self-checks passed")
