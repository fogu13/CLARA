"""Lexical tag canonicalization — pin LLM tag variants to the known vocabulary.

The model invents wording variants of tags it has already been taught or has
already emitted (`sync_error` vs `sync_failure`, `slow_loading` vs `slow_load`,
`mobile_app_freeze` vs `app_freeze`), which fragments clustering and tanks
exact-set agreement while fuzzy-F1 stays high — the measured gap is 80.2%
fuzzy vs 55.5% exact (run 2026-07-17). This module closes the *lexical* part
of that gap deterministically, with no embeddings and no extra LLM calls:

  match key = the tag's tokens, lightly stemmed ("loading"->"load",
  plural-s stripped), with failure-class synonyms (error/failure/issue/
  problem/bug) collapsed to one class token.

A predicted tag is replaced by a vocabulary tag when their keys are equal, or
when the keys differ by exactly one token and one contains the other (so
`mobile_app_freeze` -> `app_freeze`). First-registered vocabulary tag wins,
so exemplar-taught names outrank in-run inventions.

# ponytail: lexical-only by design — semantic merges (onboarding_friction vs
# setup_friction) need embeddings and stay with the taxonomy-hygiene flow.
"""

from __future__ import annotations

from collections.abc import Iterable

_FAILURE_CLASS = {
    "error", "errors", "failure", "failures", "issue", "issues",
    "problem", "problems", "bug", "bugs",
}
_CLASS_TOKEN = "‹fail›"  # cannot collide with a real snake_case token


def _stem(token: str) -> str:
    if len(token) > 5 and token.endswith("ing"):
        token = token[:-3]
    elif len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        token = token[:-1]
    return token


def _key(tag: str) -> frozenset[str]:
    return frozenset(
        _CLASS_TOKEN if token in _FAILURE_CLASS else _stem(token)
        for token in tag.lower().split("_")
        if token
    )


class TagCanonicalizer:
    """Vocabulary-anchored canonicalizer; register() order sets precedence."""

    # Bound in-run vocabulary growth so a large import stays O(M·cap), not
    # O(M²): once the cap is hit, canonicalize still works against the learned
    # set but stops adding new variants.
    _MAX_VOCAB = 2_000

    def __init__(self, vocabulary: Iterable[str] = ()) -> None:
        self._exact: set[str] = set()
        self._by_key: dict[frozenset[str], str] = {}
        for tag in vocabulary:
            self.register(tag)

    def register(self, tag: str) -> None:
        tag = tag.strip()
        if not tag or tag in self._exact or len(self._exact) >= self._MAX_VOCAB:
            return
        self._exact.add(tag)
        self._by_key.setdefault(_key(tag), tag)

    def canonicalize(self, tag: str) -> str:
        tag = tag.strip()
        if not tag or tag in self._exact:
            return tag
        key = _key(tag)
        hit = self._by_key.get(key)
        if hit is not None:
            return hit
        # Near-miss: one token added or removed, rest contained. Require the
        # smaller side to keep >=2 tokens, so a specific tag never collapses
        # onto a bare single-token vocab entry (checkout_crash -> checkout
        # would silently drop "crash"); mobile_app_freeze -> app_freeze, where
        # both sides are >=2 tokens, still normalizes.
        for vocab_key, vocab_tag in self._by_key.items():
            small, large = sorted((key, vocab_key), key=len)
            if len(small) >= 2 and small < large and len(large - small) == 1:
                return vocab_tag
        return tag

    def canonicalize_all(self, tags: list[str], *, learn: bool = True) -> list[str]:
        """Canonicalize a tag list; optionally add the results to the vocabulary
        so later signals in the same run converge on the same names."""
        out: list[str] = []
        for tag in tags:
            canonical = self.canonicalize(tag)
            if canonical and canonical not in out:  # dedup post-merge
                out.append(canonical)
                if learn:
                    self.register(canonical)
        return out
