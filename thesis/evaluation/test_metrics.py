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


if __name__ == "__main__":
    test_perfect_and_known()
    test_baseline_polarity()
    test_baseline_risk_and_stars()
    print("OK: all metric/baseline self-checks passed")
