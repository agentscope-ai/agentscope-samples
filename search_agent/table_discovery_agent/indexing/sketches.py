# -*- coding: utf-8 -*-
"""Build compact statistics for categorical and numerical columns."""

from bisect import bisect_left
from collections.abc import Iterator, Mapping
from hashlib import shake_128
from heapq import nsmallest
from math import inf, isnan
from struct import iter_unpack

import numpy as np
import pandas as pd
from pandas.api.types import is_float_dtype, is_integer_dtype, is_scalar


class CountMinSketch:
    """Estimate non-null category frequencies using string keys.

    The default 272 counters per row and five rows correspond to a
    Count-Min error parameter of 0.01 and confidence of 0.99.
    """

    def __init__(
        self, column: pd.Series, width: int = 272, depth: int = 5
    ) -> None:
        if width <= 0 or depth <= 0:
            raise ValueError("width and depth must be positive")
        self._counts = np.zeros((depth, width), dtype=np.int64)
        values = column.dropna()
        self._total = len(values)
        for value in values:
            for row, bucket in enumerate(self._buckets(value)):
                self._counts[row, bucket] += 1

    def _buckets(self, value: object) -> Iterator[int]:
        depth, width = self._counts.shape
        key = str(value).encode("utf-8", errors="surrogatepass")
        digest = shake_128(key).digest(8 * depth)
        for (hashed,) in iter_unpack(">Q", digest):
            yield hashed % width

    def frequency(self, value: object) -> float:
        """Return the estimated fraction for a value among non-null rows."""
        if not self._total or (is_scalar(value) and pd.isna(value)):
            return 0.0
        estimate = min(
            self._counts[row, bucket]
            for row, bucket in enumerate(self._buckets(value))
        )
        return int(estimate) / self._total


class QuantileHistogram:
    """Estimate range fractions using at most the requested number of bins.

    Edges are observed quantile values. Repeated edges share one entry,
    with separate counts below and at or below each edge. Queries through
    a bin's interior assume the mass between its edges is uniform.
    """

    def __init__(self, column: pd.Series, bins: int = 100) -> None:
        if bins <= 0:
            raise ValueError("bins must be positive")
        values = column.dropna().to_numpy()
        values = np.sort(values[np.isfinite(values)])
        self._total = len(values)
        ranks = np.linspace(
            0, self._total - 1, min(bins + 1, self._total), dtype=np.intp
        )
        edges = np.unique(values[ranks])
        self._edges = edges.tolist()
        self._below = np.searchsorted(values, edges, side="left").tolist()
        self._at_or_below = np.searchsorted(
            values, edges, side="right"
        ).tolist()

    def _cumulative_count(self, value: float, inclusive: bool) -> float:
        position = bisect_left(self._edges, value)
        if position == len(self._edges):
            return self._total
        right = self._edges[position]
        if value == right:
            counts = self._at_or_below if inclusive else self._below
            return counts[position]
        if position == 0:
            return 0

        left = self._edges[position - 1]
        width = right - left
        if width == inf:
            # Halve the endpoints before subtracting opposite extremes.
            fraction = (value / 2 - left / 2) / (right / 2 - left / 2)
        else:
            fraction = (value - left) / width
        left_count = self._at_or_below[position - 1]
        return left_count + fraction * (self._below[position] - left_count)

    def range_fraction(
        self, lower: float | None = None, upper: float | None = None
    ) -> float:
        """Estimate the fraction in an inclusive range with optional bounds."""
        if isinstance(lower, np.generic):
            lower = lower.item()
        if isinstance(upper, np.generic):
            upper = upper.item()
        lower = -inf if lower is None else lower
        upper = inf if upper is None else upper
        if not self._total or lower > upper or isnan(lower) or isnan(upper):
            return 0.0
        count = self._cumulative_count(
            upper, inclusive=True
        ) - self._cumulative_count(lower, inclusive=False)
        return float(count / self._total)


class KeySketch:
    """Sample join keys and summarize numeric columns for those keys.

    Non-null keys use their string representation as their identity. The
    sketch keeps up to k distinct keys ordered by a stable hash and then by
    key identity. Each selected key gets one mean per non-key numeric column,
    using only finite values.
    """

    def __init__(
        self, table: pd.DataFrame, key_column: str, k: int = 256
    ) -> None:
        """Build a sketch of the specified key column and its numeric data."""
        if k <= 0:
            raise ValueError("k must be positive")
        self._k = k
        keys = table[key_column].astype(object).map(str, na_action="ignore")
        ranks = (
            (shake_128(key.encode(errors="surrogatepass")).digest(16), key)
            for key in keys.dropna().unique()
        )
        self._ranks = set(nsmallest(k, ranks))

        selected = keys.isin(key for _, key in self._ranks)
        numeric_columns = [
            name
            for name, column in table.items()
            if name != key_column
            and (is_integer_dtype(column) or is_float_dtype(column))
        ]
        values = table.loc[selected, numeric_columns].astype(float)
        finite = values.where(np.isfinite(values))
        groups = finite.groupby(keys[selected].to_numpy(), sort=False)
        max_value = np.nanmax(np.abs(finite.to_numpy()), initial=0.0)
        if max_value >= np.finfo(float).max / max(1, len(finite)):
            # Scale within each group if summing its finite values could
            # overflow before dividing by the number of observations.
            self._means = groups.agg(self._scaled_mean)
        else:
            self._means = groups.mean()

    @staticmethod
    def _scaled_mean(column: pd.Series) -> float:
        scale = float(column.abs().max())
        if scale == 0 or isnan(scale):
            return scale
        return float((column / scale).mean()) * scale

    def overlap(self, other: "KeySketch") -> float:
        """Estimate Jaccard overlap from the bottom-k keys of the union."""
        # pylint: disable=protected-access
        sample = nsmallest(min(self._k, other._k), self._ranks | other._ranks)
        if not sample:
            return 0.0
        shared = self._ranks & other._ranks
        return sum(rank in shared for rank in sample) / len(sample)

    def correlation(
        self, other: "KeySketch", left_column: str, right_column: str
    ) -> float | None:
        """Return signed Pearson correlation of aligned per-key means.

        Return None if either column is unavailable or the paired finite
        values do not define a correlation.
        """
        # pylint: disable=protected-access
        if (
            left_column not in self._means.columns
            or right_column not in other._means.columns
        ):
            return None
        keys = [key for _, key in sorted(self._ranks & other._ranks)]
        values = np.column_stack(
            (
                self._means[left_column].reindex(keys),
                other._means[right_column].reindex(keys),
            )
        )
        paired = values[np.isfinite(values).all(axis=1)]
        if len(paired) < 2 or np.all(paired == paired[0], axis=0).any():
            return None

        # Rescale and shift before centering to handle large or close values.
        _, exponents = np.frexp(np.abs(paired).max(axis=0))
        scaled = np.ldexp(paired, -exponents)
        shifted = scaled - scaled[0]
        return float(np.corrcoef(shifted, rowvar=False)[0, 1])


def build_column_statistics(
    tables: Mapping[str, pd.DataFrame],
) -> dict[tuple[str, str], CountMinSketch | QuantileHistogram]:
    """Build one statistic per table ID and column name."""
    return {
        (table_id, str(name)): (
            QuantileHistogram(column)
            if is_integer_dtype(column) or is_float_dtype(column)
            else CountMinSketch(column)
        )
        for table_id, table in tables.items()
        for name, column in table.items()
    }
