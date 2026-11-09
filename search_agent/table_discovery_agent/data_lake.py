# -*- coding: utf-8 -*-
"""Discover CSV tables and read their data."""

import csv
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
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


def list_csv_paths(directory: Path) -> list[Path]:
    """List the CSV paths directly inside the directory by table ID."""
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

    return paths


def _read_metadata(path: Path) -> Table:
    return Table(path.stem, path, _read_columns(path))


def load_data_lake(directory: Path) -> tuple[Table, ...]:
    """Read the metadata for each CSV file directly inside the directory."""
    return tuple(_read_metadata(path) for path in list_csv_paths(directory))


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


class LazyTableFrames(Mapping[str, "pd.DataFrame"]):
    """Read CSV data on first access and keep a bounded cache of frames."""

    def __init__(
        self, tables: Sequence[Table], *, cache_size: int = 4
    ) -> None:
        if (
            isinstance(cache_size, bool)
            or not isinstance(cache_size, int)
            or cache_size < 0
        ):
            raise ValueError("cache_size must be a nonnegative integer")
        self._tables = {table.id: table for table in tables}
        self._read = lru_cache(maxsize=cache_size)(read_table)

    @property
    def schemas(self) -> dict[str, Sequence[str]]:
        """Return table headers without reading any CSV data."""
        return {
            table_id: table.columns for table_id, table in self._tables.items()
        }

    def __getitem__(self, table_id: str) -> "pd.DataFrame":
        return self._read(self._tables[table_id])

    def __iter__(self) -> Iterator[str]:
        return iter(self._tables)

    def __len__(self) -> int:
        return len(self._tables)

    def __contains__(self, table_id: object) -> bool:
        return table_id in self._tables


def validate_data_lake(directory: Path) -> tuple[int, list[str]]:
    """Return the number of readable tables and one diagnostic per failure."""
    paths = list_csv_paths(directory)
    errors = []
    for path in paths:
        try:
            read_table(_read_metadata(path))
        except ValueError as error:
            errors.append(str(error))
    return len(paths) - len(errors), errors
