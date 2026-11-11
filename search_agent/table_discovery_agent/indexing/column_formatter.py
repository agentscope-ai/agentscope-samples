# -*- coding: utf-8 -*-
"""Format column names and values into texts for table discovery."""

import math
import re
from collections import Counter
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from heapq import nsmallest
from numbers import Integral
from sys import float_info

import pandas as pd
from pandas.api.types import is_float_dtype, is_integer_dtype

MAX_REPRESENTATIVE_VALUES = 12
MAX_VALUE_LENGTH = 80
EMPTY_CONTENT = "N/A"
_PERCENTILES = (0.2, 0.4, 0.6, 0.8)


@dataclass(frozen=True)
class ColumnRepresentation:
    """Texts and source identity for one table column."""

    table_id: str
    column_name: str
    column_type: str
    metadata: str
    content: str


def _normalize_name(name: str) -> str:
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    return " ".join(name.replace("_", " ").replace("-", " ").lower().split())


def _normalized_values(column: pd.Series) -> Iterator[str]:
    for value in column.dropna():
        normalized = " ".join(str(value).split())
        if normalized:
            yield normalized


def _is_numerical(column: pd.Series) -> bool:
    return is_integer_dtype(column) or is_float_dtype(column)


def _categorical_content(
    counts: Counter[str],
    document_frequency: Counter[str],
    document_count: int,
) -> str:
    def rank(value: str) -> tuple[float, str]:
        idf = (
            math.log(
                (document_count + 1) / (document_frequency[value] + 1),
            )
            + 1
        )
        # Raw counts give the same order as normalized TF within a column.
        return -counts[value] * idf, value

    values = nsmallest(MAX_REPRESENTATIVE_VALUES, counts, key=rank)
    return ", ".join(value[:MAX_VALUE_LENGTH] for value in values) or (
        EMPTY_CONTENT
    )


def _format_stat(value: float) -> str:
    if isinstance(value, Integral):
        return f"{value}.00"
    return f"{value:.2f}" if math.isfinite(value) else EMPTY_CONTENT


def _numerical_content(column: pd.Series) -> str:
    values = column.dropna()
    if values.empty:
        return EMPTY_CONTENT

    finite = values[values.between(-math.inf, math.inf, inclusive="neither")]
    counts = (
        f"Count: {len(values)}, Unique: {values.nunique()}, "
        f"NaN: {len(column) - len(values)}"
    )
    if finite.empty:
        return counts

    minimum, maximum = finite.min(), finite.max()
    # Scale large samples before summing squared deviations.
    magnitude = max(abs(float(minimum)), abs(float(maximum)))
    safe_magnitude = math.sqrt(float_info.max / len(finite)) / 2
    scale = 1.0
    sample = finite.astype(float)
    if magnitude > safe_magnitude:
        scale = magnitude
        sample = sample / scale

    quantiles = sample.quantile(list(_PERCENTILES))
    std = float(sample.std()) * scale if len(sample) > 1 else 0.0
    stats = {
        "Min": minimum,
        "Max": maximum,
        "Mean": float(sample.mean()) * scale,
        "Std": std,
        "P20": float(quantiles.loc[0.2]) * scale,
        "P40": float(quantiles.loc[0.4]) * scale,
        "P60": float(quantiles.loc[0.6]) * scale,
        "P80": float(quantiles.loc[0.8]) * scale,
    }
    stats_text = ", ".join(
        f"{label}: {_format_stat(value)}" for label, value in stats.items()
    )
    return f"{counts}, {stats_text}"


def _categorical_document_frequency(
    tables: Mapping[str, pd.DataFrame],
) -> tuple[Counter[str], int]:
    document_frequency: Counter[str] = Counter()
    document_count = 0
    for table in tables.values():
        for _, column in table.items():
            if _is_numerical(column):
                continue
            values = set(_normalized_values(column))
            if values:
                document_count += 1
                document_frequency.update(values)
    return document_frequency, document_count


def format_columns(
    tables: Mapping[str, pd.DataFrame],
) -> tuple[ColumnRepresentation, ...]:
    """Format columns in source order using lake-wide categorical IDF."""
    document_frequency, document_count = _categorical_document_frequency(
        tables,
    )

    representations = []
    for table_id, table in tables.items():
        for label, column in table.items():
            name = str(label)
            if _is_numerical(column):
                column_type = "Numerical"
                summary = _numerical_content(column)
            else:
                column_type = "Categorical"
                summary = _categorical_content(
                    Counter(_normalized_values(column)),
                    document_frequency,
                    document_count,
                )

            prefix = f"Column: {_normalize_name(name)} | Type: {column_type}"
            representations.append(
                ColumnRepresentation(
                    table_id=table_id,
                    column_name=name,
                    column_type=column_type,
                    metadata=f"{prefix} | Description: None",
                    content=f"{prefix} | Content: {summary}",
                ),
            )
    return tuple(representations)
