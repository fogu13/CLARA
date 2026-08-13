"""R8: deterministic clustering + stability metric (science review F8)."""

from __future__ import annotations

from app.evals.harness import adjusted_rand_index, cluster_stability_ari
from app.services.semantic_taxonomy import cluster_by_threshold


def _vec(*xs: float) -> list[float]:
    return list(xs)


class TestAgglomerative:
    def test_order_independent(self) -> None:
        # The greedy variant this replaces anchored on the first unused vector,
        # so permuting the input changed the partition. Average linkage must not.
        a, b = _vec(1.0, 0.0, 0.0), _vec(0.98, 0.2, 0.0)
        c, d = _vec(0.0, 1.0, 0.0), _vec(0.1, 0.99, 0.0)
        e = _vec(0.0, 0.0, 1.0)
        forward = cluster_by_threshold([a, b, c, d, e], 0.9, 2)
        reversed_in = cluster_by_threshold([e, d, c, b, a], 0.9, 2)
        as_sets_fwd = {frozenset(g) for g in forward}
        # Map reversed indices back: item k in reversed input is item 4-k originally.
        as_sets_rev = {frozenset(4 - i for i in g) for g in reversed_in}
        assert as_sets_fwd == as_sets_rev == {frozenset({0, 1}), frozenset({2, 3})}

    def test_no_single_link_chaining(self) -> None:
        # A~B and B~C but A!~C: average linkage keeps the pair whose AVERAGE
        # clears the threshold instead of chaining all three.
        import math

        def unit(angle: float) -> list[float]:
            return [math.cos(angle), math.sin(angle)]

        a, b, c = unit(0.0), unit(0.45), unit(0.9)  # cos(0.45)~0.90, cos(0.9)~0.62
        clusters = cluster_by_threshold([a, b, c], 0.85, 2)
        assert all(len(g) == 2 for g in clusters)
        assert len(clusters) == 1  # one pair merged, the far item left out

    def test_min_size_filter(self) -> None:
        vectors = [_vec(1.0, 0.0), _vec(0.99, 0.1), _vec(0.0, 1.0)]
        clusters = cluster_by_threshold(vectors, 0.9, 3)
        assert clusters == []


class TestARI:
    def test_identical_partitions(self) -> None:
        assert adjusted_rand_index([0, 0, 1, 1], [1, 1, 0, 0]) == 1.0

    def test_orthogonal_partitions_near_zero(self) -> None:
        value = adjusted_rand_index([0, 0, 1, 1], [0, 1, 0, 1])
        assert abs(value) < 0.5  # chance-level, far from 1

    def test_stability_of_clean_tags_is_high(self) -> None:
        signals = (
            [{"id": f"a{i}", "tags": ["checkout_failure", "payment_error"]} for i in range(6)]
            + [{"id": f"b{i}", "tags": ["support_delay", "ticket_backlog"]} for i in range(6)]
        )
        result = cluster_stability_ari(signals, n_resamples=10)
        assert result["mean_ari"] > 0.9
        assert result["n_resamples"] > 0
