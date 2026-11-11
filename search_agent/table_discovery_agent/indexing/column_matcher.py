# -*- coding: utf-8 -*-
"""Match column names by normalized text or embedding similarity."""

import re
from collections.abc import Iterable
from functools import cache, cached_property
from operator import itemgetter

import numpy as np

from indexing.embedding import ColumnEncoder

_NAME_BOUNDARY = re.compile(
    r"(?<=[a-z])(?=[A-Z])|(?<=[A-Za-z])(?=[0-9])|(?<=[0-9])(?=[A-Za-z])",
)


def _normalize_name(name: str) -> str:
    name = _NAME_BOUNDARY.sub(" ", name)
    return name.replace("_", " ").replace("-", " ").strip().lower()


class ColumnNameMatcher:
    """Match names against an ordered set of candidate columns."""

    def __init__(
        self,
        encoder: ColumnEncoder,
        names: Iterable[str] = (),
        *,
        threshold: float = 0.8,
    ) -> None:
        self._encoder = encoder
        self._threshold = threshold
        self._normalize = cache(_normalize_name)
        self._known_labels = list(dict.fromkeys(map(self._normalize, names)))

    @cached_property
    def _embeddings(self) -> dict[str, np.ndarray]:
        if not self._known_labels:
            return {}
        return dict(
            zip(self._known_labels, self._encoder.encode(self._known_labels)),
        )

    def find_match(self, name: str, candidates: Iterable[str]) -> str | None:
        """Return the first exact match or the best semantic match."""
        label = self._normalize(name)
        normalized: list[tuple[str, str]] = []
        for candidate in candidates:
            candidate_label = self._normalize(candidate)
            if label == candidate_label:
                return candidate
            normalized.append((candidate, candidate_label))
        if not normalized:
            return None

        embeddings = self._embeddings
        labels = dict.fromkeys([label, *(value for _, value in normalized)])
        missing = [value for value in labels if value not in embeddings]
        if missing:
            embeddings.update(zip(missing, self._encoder.encode(missing)))

        source = embeddings[label]
        best, score = max(
            (
                (candidate, float(source @ embeddings[value]))
                for candidate, value in normalized
            ),
            key=itemgetter(1),
        )
        return best if score >= self._threshold else None
