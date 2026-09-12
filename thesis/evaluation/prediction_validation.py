"""Validate a prediction file against the gold ids BEFORE anything is scored.

Why this exists (evaluation review, defect E1): the scoring code used to build
``{row["id"]: row}`` (a duplicate id silently overwrote the earlier row),
iterate ``s.id in preds`` (rows for unknown ids vanished, gold items with no
row silently left the denominator) and read labels as
``row.get("sentiment") or "neutral"`` (a missing or empty label became the
majority class; an off-vocabulary string such as "mixed" or "Positive" went
into the macro average as an extra class). An id-only prediction file could
therefore score 100 % on a neutral/low item. Nothing here defaults a label.

The single entry point is a pure function so it can be tested without the
corpus: ``validate_predictions(rows, expected_ids=..., field=..., labels=...)``.
Ids are compared as ``str()`` so an integer id in the file matches the string
id of the gold record.

Vocabulary used by the counts (every gold id falls into exactly one bucket, so
``n_valid + n_invalid + n_missing == n_expected``):

  valid        a row for an expected id whose label is a string in ``labels``
               (or, with ``labels=None`` — an open vocabulary such as the
               taxonomy fields — any string that is non-empty after strip,
               stored stripped)
  invalid      a row for an expected id whose label is missing, empty or not in
               ``labels`` — an abstention or off-vocabulary answer
  missing      an expected id with no row at all (the model did not answer)
  invalid id   a row that is not a mapping, or whose id is absent, null or
               empty: it can never be matched to a gold item and is counted
               under ``n_invalid_ids`` (never scored, never "unknown")
  unknown      a row whose id is not in the corpus at all (``corpus_ids``
               given) — or, without ``corpus_ids``, not in the expected set
  outside task a row whose id is in the corpus but outside this task's
               expected set (e.g. an unrated item in the sentiment task);
               only distinguished when ``corpus_ids`` is given
  duplicate    a second or later row for an id already seen; the FIRST row wins
               and the later ones are only counted

``expected_ids`` is de-duplicated (first occurrence keeps its position) and the
number of dropped repeats is reported as ``n_expected_duplicates``; nothing in
here can assert on user input.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence


@dataclass
class ValidatedPredictions:
    by_id: dict[str, str]
    n_expected: int
    n_returned: int
    n_valid: int
    n_invalid: int
    n_missing: int
    n_unknown_ids: int
    n_duplicate_ids: int
    n_outside_task: int = 0
    n_invalid_ids: int = 0
    n_expected_duplicates: int = 0
    invalid_examples: list[tuple[str, Any]] = field(default_factory=list)
    duplicate_ids: list[str] = field(default_factory=list)
    unknown_ids: list[str] = field(default_factory=list)
    outside_task_ids: list[str] = field(default_factory=list)
    missing_ids: list[str] = field(default_factory=list)

    @property
    def coverage(self) -> float | None:
        """Share of gold items with a valid prediction (None when nothing is expected)."""
        return round(self.n_valid / self.n_expected, 4) if self.n_expected else None

    def counts(self) -> dict[str, Any]:
        """The denominator record every score built on ``by_id`` must carry."""
        return {
            "n_expected": self.n_expected,
            "n_expected_duplicates": self.n_expected_duplicates,
            "n_returned": self.n_returned,
            "n_valid": self.n_valid,
            "n_invalid": self.n_invalid,
            "n_missing": self.n_missing,
            "n_unknown_ids": self.n_unknown_ids,
            "n_outside_task": self.n_outside_task,
            "n_invalid_ids": self.n_invalid_ids,
            "n_duplicate_ids": self.n_duplicate_ids,
            "coverage": self.coverage,
        }

    def detail(self) -> dict[str, Any]:
        """counts() plus the ids and examples behind them (for summary.json)."""
        return {
            **self.counts(),
            "invalid_examples": [[sid, raw] for sid, raw in self.invalid_examples],
            "duplicate_ids": list(self.duplicate_ids),
            "unknown_ids": list(self.unknown_ids),
            "outside_task_ids": list(self.outside_task_ids),
            "missing_ids": list(self.missing_ids),
        }


def _dedupe_keep_order(values: Iterable[Any]) -> tuple[list[str], int]:
    out: list[str] = []
    seen: set[str] = set()
    dropped = 0
    for value in values:
        sid = str(value)
        if sid in seen:
            dropped += 1
            continue
        seen.add(sid)
        out.append(sid)
    return out, dropped


def validate_predictions(
    rows: Iterable[Any],
    *,
    expected_ids: Sequence[Any],
    field: str,
    labels: Sequence[str] | None,
    id_field: str = "id",
    corpus_ids: Iterable[Any] | None = None,
) -> ValidatedPredictions:
    """Partition ``rows`` against ``expected_ids`` for one label ``field``.

    ``rows`` is the prediction file as written (a list of per-item dicts; a
    row that is not a mapping is counted as an invalid id and skipped).
    ``expected_ids`` are the gold ids the task is scored on (the denominator;
    repeats are dropped and counted). ``labels`` is the closed label set;
    anything else is invalid. ``labels=None`` means an open vocabulary: any
    string non-empty after strip is valid and is stored stripped. No label is
    ever defaulted; an invalid or missing prediction stays out of ``by_id``.
    ``corpus_ids`` (optional) splits rows outside the expected set into
    unknown (not in the corpus) and outside-task (in the corpus).
    """
    expected, n_expected_duplicates = _dedupe_keep_order(expected_ids)
    expected_set = set(expected)
    label_set = None if labels is None else {str(lab) for lab in labels}
    corpus_set = None if corpus_ids is None else {str(x) for x in corpus_ids}

    by_id: dict[str, str] = {}
    seen: set[str] = set()
    invalid: set[str] = set()
    invalid_examples: list[tuple[str, Any]] = []
    duplicate_ids: list[str] = []
    unknown_ids: list[str] = []
    outside_task_ids: list[str] = []
    n_returned = n_unknown_rows = n_outside_rows = n_duplicate_rows = n_invalid_id_rows = 0

    for row in rows:
        n_returned += 1
        raw_id = row.get(id_field) if isinstance(row, Mapping) else None
        sid = "" if raw_id is None else str(raw_id)
        if not isinstance(row, Mapping) or not sid:
            n_invalid_id_rows += 1
            continue
        if sid not in expected_set:
            if corpus_set is not None and sid in corpus_set:
                n_outside_rows += 1
                if sid not in outside_task_ids:
                    outside_task_ids.append(sid)
            else:
                n_unknown_rows += 1
                if sid not in unknown_ids:
                    unknown_ids.append(sid)
            continue
        if sid in seen:
            n_duplicate_rows += 1
            if sid not in duplicate_ids:
                duplicate_ids.append(sid)
            continue  # first occurrence wins
        seen.add(sid)
        label = row.get(field)
        if label_set is None:
            ok = isinstance(label, str) and bool(label.strip())
            if ok:
                label = label.strip()
        else:
            ok = isinstance(label, str) and label in label_set
        if ok:
            by_id[sid] = label
        else:
            invalid.add(sid)
            if len(invalid_examples) < 5:
                invalid_examples.append((sid, label))

    missing_ids = [sid for sid in expected if sid not in seen]
    return ValidatedPredictions(
        by_id=by_id,
        n_expected=len(expected),
        n_returned=n_returned,
        n_valid=len(by_id),
        n_invalid=len(invalid),
        n_missing=len(missing_ids),
        n_unknown_ids=n_unknown_rows,
        n_duplicate_ids=n_duplicate_rows,
        n_outside_task=n_outside_rows,
        n_invalid_ids=n_invalid_id_rows,
        n_expected_duplicates=n_expected_duplicates,
        invalid_examples=invalid_examples,
        duplicate_ids=duplicate_ids,
        unknown_ids=unknown_ids,
        outside_task_ids=outside_task_ids,
        missing_ids=missing_ids,
    )
