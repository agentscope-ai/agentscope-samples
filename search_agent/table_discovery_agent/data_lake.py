# -*- coding: utf-8 -*-
"""Discover CSV tables and read their data."""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True)
class Table:
    """Metadata for one CSV table."""

    id: str
    path: Path
    columns: tuple[str, ...]


def _read_columns(path: Path) -> tuple[str, ...]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            header = next(csv.reader(stream, strict=True), None)
    except (csv.Error, UnicodeError, OSError) as error:
        raise ValueError(
            f"Cannot read CSV header in {path}: {error}"
        ) from error

    if not header or any(not name.strip() for name in header):
        raise ValueError(
            f"Invalid CSV header in {path}: column names cannot be empty"
        )
    if len(set(header)) != len(header):
        raise ValueError(
            f"Invalid CSV header in {path}: duplicate column names"
        )
    return tuple(header)


def load_data_lake(directory: Path) -> tuple[Table, ...]:
    """Read the metadata for each CSV file directly inside the directory."""
    if not directory.exists():
        raise ValueError(f"Lake directory does not exist: {directory}")
    if not directory.is_dir():
        raise ValueError(f"Lake path is not a directory: {directory}")

    paths = sorted(
        (path for path in directory.glob("*.csv") if path.is_file()),
        key=lambda path: path.stem,
    )
    if not paths:
        raise ValueError(f"No CSV tables found in lake directory: {directory}")

    return tuple(Table(path.stem, path, _read_columns(path)) for path in paths)


def read_table(table: Table) -> "pd.DataFrame":
    """Read a CSV table with inferred types and verify its columns."""
    import pandas as pd

    try:
        frame = pd.read_csv(table.path, encoding="utf-8-sig")
    except (OSError, ValueError) as error:
        raise ValueError(
            f"Cannot read CSV data in {table.path}: {error}"
        ) from error

    columns = tuple(frame.columns)
    if columns != table.columns:
        raise ValueError(
            f"CSV header mismatch in {table.path}: "
            f"expected {table.columns!r}, got {columns!r}"
        )
    if not frame.empty and not isinstance(frame.index, pd.RangeIndex):
        raise ValueError(
            f"Cannot read CSV data in {table.path}: "
            "a row has more fields than the header"
        )
    return frame
