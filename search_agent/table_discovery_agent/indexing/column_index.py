# -*- coding: utf-8 -*-
"""Index and retrieve column representations by metadata or content."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass, fields
from numbers import Integral
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import numpy as np

from .column_formatter import ColumnRepresentation
from .embedding import ColumnEncoder

if TYPE_CHECKING:
    from faiss import IndexHNSWFlat


_Channel = Literal["metadata", "content"]
_CHANNELS: tuple[_Channel, ...] = ("metadata", "content")


@dataclass(frozen=True)
class ColumnMatch:
    """A column and its inner-product score for a query."""

    table_id: str
    column_name: str
    column_type: str
    score: float


def _new_index(dimension: int) -> IndexHNSWFlat:
    from faiss import METRIC_INNER_PRODUCT, IndexHNSWFlat

    index = IndexHNSWFlat(dimension, 32, METRIC_INNER_PRODUCT)
    index.hnsw.efConstruction = 256
    index.hnsw.efSearch = 1024
    return index


class ColumnIndex:
    """Keep separate HNSW indexes over the same ordered set of columns."""

    def __init__(
        self,
        columns: Sequence[ColumnRepresentation],
        encoder: ColumnEncoder,
        *,
        batch_size: int | None = None,
    ) -> None:
        if batch_size is not None and (
            isinstance(batch_size, bool)
            or not isinstance(batch_size, Integral)
            or batch_size <= 0
        ):
            raise ValueError("batch_size must be a positive integer")

        self._set_columns(columns)
        self._encoder = encoder
        size = len(self._columns) if batch_size is None else batch_size
        self._indexes = {
            channel: self._build_channel(channel, size)
            for channel in _CHANNELS
        }
        if self._indexes["metadata"].d != self._indexes["content"].d:
            raise ValueError("encoder must return vectors of fixed dimension")

    @property
    def dimension(self) -> int:
        """Return the shared embedding dimension."""
        return next(iter(self._indexes.values())).d

    def _set_columns(self, columns: Sequence[ColumnRepresentation]) -> None:
        self._columns = tuple(columns)
        if not self._columns:
            raise ValueError("at least one column representation is required")

        self._by_column = {
            (column.table_id, column.column_name): column
            for column in self._columns
        }

    def _build_channel(
        self, channel: _Channel, batch_size: int
    ) -> IndexHNSWFlat:
        index = None
        for start in range(0, len(self._columns), batch_size):
            batch = self._columns[start : start + batch_size]
            vectors = self._encode(
                [getattr(column, channel) for column in batch]
            )
            if index is None:
                index = _new_index(vectors.shape[1])
            elif vectors.shape[1] != index.d:
                raise ValueError(
                    "encoder must return vectors of fixed dimension"
                )
            index.add(vectors)
            del vectors

        assert index is not None
        return index

    def save(self, directory: Path) -> None:
        """Write both indexes and their ordered column records."""
        from faiss import write_index

        if any(channel not in self._indexes for channel in _CHANNELS):
            raise ValueError("saving requires both index channels")
        for channel in _CHANNELS:
            write_index(
                self._indexes[channel], str(directory / f"{channel}.index")
            )
        with (directory / "columns.json").open(
            "w", encoding="utf-8"
        ) as stream:
            stream.write("[\n")
            for position, column in enumerate(self._columns):
                if position:
                    stream.write(",\n")
                stream.write(json.dumps(asdict(column)))
            stream.write("\n]\n")

    @classmethod
    def load(
        cls,
        directory: Path,
        encoder: ColumnEncoder,
        *,
        channels: Sequence[_Channel] = _CHANNELS,
    ) -> ColumnIndex:
        """Restore selected native indexes without encoding any stored text."""
        from faiss import METRIC_INNER_PRODUCT, IndexHNSWFlat, read_index

        selected = tuple(channels)
        if not selected or any(
            channel not in _CHANNELS for channel in selected
        ):
            raise ValueError(
                "channels must select 'metadata' and/or 'content'"
            )
        if len(set(selected)) != len(selected):
            raise ValueError(
                "each index channel must be selected at most once"
            )

        with (directory / "columns.json").open(encoding="utf-8") as stream:
            records = json.load(stream)
        if not isinstance(records, list):
            raise ValueError("columns.json must contain an ordered array")

        column_fields = {field.name for field in fields(ColumnRepresentation)}
        columns = []
        for record in records:
            if (
                not isinstance(record, dict)
                or record.keys() != column_fields
                or not all(isinstance(value, str) for value in record.values())
            ):
                raise ValueError(
                    "columns.json contains an invalid column record"
                )
            columns.append(ColumnRepresentation(**record))

        result = cls.__new__(cls)
        result._set_columns(columns)
        result._encoder = encoder
        result._indexes = {}
        dimensions = set()
        for channel in selected:
            index = read_index(str(directory / f"{channel}.index"))
            if (
                not isinstance(index, IndexHNSWFlat)
                or index.metric_type != METRIC_INNER_PRODUCT
                or not index.is_trained
                or index.d <= 0
            ):
                raise ValueError(f"incompatible {channel} index")
            if index.ntotal != len(columns):
                raise ValueError(
                    f"{channel} index and column counts must match"
                )
            dimensions.add(index.d)
            result._indexes[channel] = index
        if len(dimensions) > 1:
            raise ValueError("index channel dimensions must match")
        return result

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

    def get_column(
        self, table_id: str, column_name: str
    ) -> ColumnRepresentation:
        """Return the indexed representation of a known column."""
        column = self._by_column.get((table_id, column_name))
        if column is None:
            raise ValueError(f"Unknown column: {table_id}.{column_name}")
        return column

    def search(
        self,
        query: str,
        channel: _Channel = "metadata",
        top_k: int = 5,
    ) -> tuple[ColumnMatch, ...]:
        """Return up to top_k matches in the selected channel."""
        if not query.strip():
            raise ValueError("query must contain non-whitespace text")
        if channel not in _CHANNELS:
            raise ValueError("channel must be 'metadata' or 'content'")
        if channel not in self._indexes:
            raise ValueError(f"channel {channel!r} is unavailable")
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
