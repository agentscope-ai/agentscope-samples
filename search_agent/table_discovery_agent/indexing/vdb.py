# -*- coding: utf-8 -*-
"""Build and reopen a discovery index for a local CSV lake."""

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal
from uuid import uuid4

from data_lake import LazyTableFrames, Table, list_csv_paths, load_data_lake
from discovery.relationship_graph import (
    RelationshipEdge,
    RelationshipGraph,
    build_relationship_graph,
)

from .column_formatter import format_columns
from .column_index import ColumnIndex
from .embedding import ColumnEncoder
from .sketches import SketchStore, build_sketch_store

_VERSION = 1
_BUILD_COMMAND = "Run --build-index to rebuild the VDB."
_Channel = Literal["metadata", "content"]


@dataclass(frozen=True)
class StoredVdb:
    """A published generation and the indexes loaded for this query."""

    generation: Path
    index: ColumnIndex
    tables: tuple[Table, ...]


def _fingerprints(paths: list[Path], root: Path) -> list[dict[str, Any]]:
    fingerprints = []
    for path in paths:
        stat = path.stat()
        fingerprints.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            },
        )
    return fingerprints


def _model_fingerprint(name: str, directory: Path) -> dict[str, Any]:
    model = directory.resolve()
    if not model.is_dir():
        raise ValueError(f"Embedding model directory does not exist: {model}")
    paths = sorted(path for path in model.rglob("*") if path.is_file())
    return {
        "encoder": name,
        "model_dir": str(model),
        "files": _fingerprints(paths, model),
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_vdb(
    directory: Path,
    lake: Path,
    encoder: ColumnEncoder,
    *,
    encoder_name: str,
    model_dir: Path,
) -> None:
    """Build a complete generation before publishing its manifest."""
    files = _fingerprints(list_csv_paths(lake), lake)
    model = _model_fingerprint(encoder_name, model_dir)
    tables = load_data_lake(lake)
    frames = LazyTableFrames(tables)
    directory.mkdir(parents=True, exist_ok=True)
    generation = f"build-{uuid4().hex}"
    with TemporaryDirectory(dir=directory, prefix=".building-") as path:
        staging = Path(path)
        index = ColumnIndex(format_columns(frames), encoder, batch_size=64)
        index.save(staging)

        sketches_path = staging / "sketches.sqlite3"
        build_sketch_store(sketches_path, frames)
        with SketchStore(sketches_path) as sketches:
            graph = build_relationship_graph(
                index,
                frames,
                encoder,
                schemas=frames.schemas,
                key_sketch=sketches.key_sketch,
            )
        _write_json(
            staging / "graph.json",
            {
                table: [asdict(edge) for edge in edges]
                for table, edges in graph.items()
            },
        )
        if files != _fingerprints(list_csv_paths(lake), lake):
            raise ValueError("CSV files changed while building the VDB.")
        if model != _model_fingerprint(encoder_name, model_dir):
            raise ValueError("Embedding model changed while building the VDB.")

        manifest = {
            "version": _VERSION,
            "generation": generation,
            "csv_files": files,
            "model": model,
            "dimension": index.dimension,
            "tables": [
                {
                    "id": t.id,
                    "path": t.path.relative_to(lake).as_posix(),
                    "columns": t.columns,
                }
                for t in tables
            ],
        }
        _write_json(staging / "manifest.json", manifest)
        published = staging.rename(directory / generation)
        # Keep the old generation readable while replacing the pointer.
        (published / "manifest.json").replace(directory / "manifest.json")


def _load_tables(
    rows: list[dict[str, Any]], paths: list[Path]
) -> tuple[Table, ...]:
    by_name = {path.name: path for path in paths}
    tables = []
    for row in rows:
        path = by_name[row["path"]]
        columns = row["columns"]
        if (
            row["id"] != path.stem
            or not isinstance(columns, list)
            or not columns
            or any(
                not isinstance(name, str) or not name.strip()
                for name in columns
            )
            or len(columns) != len(set(columns))
        ):
            raise ValueError("The saved table catalog is invalid.")
        tables.append(Table(row["id"], path, tuple(columns)))
    if [table.path for table in tables] != paths:
        raise ValueError("The saved table catalog does not match the lake.")
    return tuple(tables)


def load_vdb(
    directory: Path,
    lake: Path,
    encoder: ColumnEncoder,
    *,
    encoder_name: str,
    model_dir: Path,
    channel: _Channel | None = None,
) -> StoredVdb:
    """Open a published VDB and check its source and model fingerprints."""
    try:
        manifest = _read_json(directory / "manifest.json")
        if manifest["version"] != _VERSION:
            raise ValueError("Unsupported VDB format version.")
        generation = manifest["generation"]
        if not isinstance(generation, str) or not re.fullmatch(
            r"build-[0-9a-f]{32}", generation
        ):
            raise ValueError("The VDB generation name is invalid.")
        paths = list_csv_paths(lake)
        if manifest["csv_files"] != _fingerprints(paths, lake):
            raise ValueError("The CSV lake has changed.")
        if manifest["model"] != _model_fingerprint(encoder_name, model_dir):
            raise ValueError("The embedding model has changed.")
        tables = _load_tables(manifest["tables"], paths)
        generation_path = directory / generation
        if channel is None:
            for name in ("graph.json", "sketches.sqlite3"):
                if not (generation_path / name).is_file():
                    raise ValueError(f"The VDB is missing {name}.")
        channels: tuple[_Channel, ...] = (
            ("metadata", "content") if channel is None else (channel,)
        )
        index = ColumnIndex.load(generation_path, encoder, channels=channels)
        if index.dimension != manifest["dimension"]:
            raise ValueError("The index dimension differs from the manifest.")
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        raise ValueError(
            f"Cannot load VDB at {directory}: {error} {_BUILD_COMMAND}"
        ) from error
    return StoredVdb(generation_path, index, tables)


def load_graph(generation: Path) -> RelationshipGraph:
    """Load the weighted graph from a published generation."""
    try:
        rows = _read_json(generation / "graph.json")
        return {
            table: tuple(
                RelationshipEdge(
                    target=edge["target"],
                    kind=edge["kind"],
                    score=edge["score"],
                    columns=tuple(edge["columns"]),
                )
                for edge in edges
            )
            for table, edges in rows.items()
        }
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise ValueError(
            f"Cannot load the relationship graph. {_BUILD_COMMAND}"
        ) from error
