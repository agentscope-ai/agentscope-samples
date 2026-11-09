# -*- coding: utf-8 -*-
"""Index and retrieve column representations by metadata or content."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from numbers import Integral
from typing import TYPE_CHECKING, Literal

import numpy as np

from .column_formatter import ColumnRepresentation
from .embedding import ColumnEncoder

if TYPE_CHECKING:
    from faiss import IndexHNSWFlat


@dataclass(frozen=True)
class ColumnMatch:
    """A column and its inner-product score for a query."""

    table_id: str
    column_name: str
    column_type: str
    score: float


def _build_index(vectors: np.ndarray) -> IndexHNSWFlat:
    from faiss import METRIC_INNER_PRODUCT, IndexHNSWFlat

    index = IndexHNSWFlat(vectors.shape[1], 32, METRIC_INNER_PRODUCT)
    index.hnsw.efConstruction = 256
    index.hnsw.efSearch = 1024
    index.add(vectors)
    return index


class ColumnIndex:
    """Keep separate HNSW indexes over the same ordered set of columns."""

    def __init__(
        self, columns: Sequence[ColumnRepresentation], encoder: ColumnEncoder
    ) -> None:
        self._columns = tuple(columns)
        if not self._columns:
            raise ValueError("at least one column representation is required")

        self._encoder = encoder
        self._indexes = {
            "metadata": _build_index(
                self._encode([column.metadata for column in self._columns])
            ),
            "content": _build_index(
                self._encode([column.content for column in self._columns])
            ),
        }

    def _encode(self, texts: Sequence[str]) -> np.ndarray:
        vectors = np.asarray(self._encoder.encode(texts), dtype=np.float32)
        if (
            vectors.ndim != 2
            or vectors.shape[0] != len(texts)
            or vectors.shape[1] == 0
        ):
            raise ValueError("encoder must return one vector per input text")
        if not np.isfinite(vectors).all():
            raise ValueError("embeddings must contain only finite values")
        return np.ascontiguousarray(vectors)

    def search(
        self,
        query: str,
        channel: Literal["metadata", "content"] = "metadata",
        top_k: int = 5,
    ) -> tuple[ColumnMatch, ...]:
        """Return up to top_k matches in the selected channel."""
        if not query.strip():
            raise ValueError("query must contain non-whitespace text")
        if channel not in self._indexes:
            raise ValueError("channel must be 'metadata' or 'content'")
        if (
            isinstance(top_k, bool)
            or not isinstance(top_k, Integral)
            or top_k <= 0
        ):
            raise ValueError("top_k must be a positive integer")

        index = self._indexes[channel]
        query_vector = self._encode([query])
        if query_vector.shape[1] != index.d:
            raise ValueError("query embedding dimension must match the index")
        limit = min(int(top_k), len(self._columns))
        scores, positions = index.search(query_vector, limit)

        matches = []
        for score, position in zip(scores[0], positions[0]):
            if position == -1:
                continue
            column = self._columns[position]
            matches.append(
                ColumnMatch(
                    table_id=column.table_id,
                    column_name=column.column_name,
                    column_type=column.column_type,
                    score=float(score),
                )
            )
        return tuple(matches)
