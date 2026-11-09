# -*- coding: utf-8 -*-
"""Run the table discovery command-line interface."""

from __future__ import annotations

import argparse
import dataclasses
import os
import sqlite3
import sys
import tomllib
from collections.abc import Callable, Mapping
from contextlib import nullcontext
from pathlib import Path
from typing import TypeVar
from data_lake import load_data_lake, validate_data_lake


def main() -> None:
    """Inspect CSV tables, search columns, or ask the discovery agent."""
    parser = argparse.ArgumentParser(
        description="List CSV tables and discover their columns."
    )
    args = _parse_args(parser)

    try:
        settings = load_config(
            args.config,
            {
                "lake": args.lake,
                "vdb_dir": args.vdb_dir,
                "output": args.output,
                "encoder": args.encoder,
                "embedding_model": args.embedding_model,
                "chat_model": args.chat_model,
                "max_rounds": args.max_rounds,
                "stagnation_limit": args.stagnation_limit,
                "candidate_limit": args.candidate_limit,
            },
        )
    except (OSError, ValueError) as error:
        parser.error(str(error))

    query = _query_text(parser, args, settings)

    api_key = (
        os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if args.ask is not None
        else ""
    )
    if args.ask is not None and not api_key:
        parser.error(
            "--ask requires the DEEPSEEK_API_KEY environment variable"
        )

    if settings.lake is None:
        if args.config is not None or args.validate:
            parser.error("set data.lake_dir or pass --lake")
        parser.print_help()
        return

    if query is None and not args.build_index:
        try:
            _inspect_lake(settings.lake, validate=args.validate)
        except (ImportError, OSError, ValueError) as error:
            parser.error(str(error))
        return

    try:
        output_path = None if args.build_index else settings.output
        if output_path is not None and (
            output_path.exists() or output_path.is_symlink()
        ):
            raise FileExistsError(f"output file already exists: {output_path}")
        if args.build_index:
            _build_index(settings)
        else:
            assert query is not None
            output = _query_output(settings, args, query, api_key)
            _write_query_output(output, output_path)
    except (
        ImportError,
        OSError,
        RuntimeError,
        ValueError,
        sqlite3.Error,
    ) as error:
        message = str(error)
        parser.error(
            message.replace(api_key, "[redacted]") if api_key else message
        )


def _build_index(settings: Config) -> None:
    from indexing.embedding import create_encoder
    from indexing.vdb import build_vdb

    assert settings.lake is not None
    assert settings.embedding_model is not None
    assert settings.vdb_dir is not None
    encoder = create_encoder(settings.encoder, settings.embedding_model)
    build_vdb(
        settings.vdb_dir,
        settings.lake,
        encoder,
        encoder_name=settings.encoder,
        model_dir=settings.embedding_model,
    )
    print(f"Built VDB at {settings.vdb_dir}")


def _query_output(
    settings: Config, args: argparse.Namespace, query: str, api_key: str
) -> str:
    from data_lake import LazyTableFrames, read_table
    from indexing import ColumnIndex, format_columns
    from indexing.embedding import create_encoder
    from indexing.sketches import SketchStore
    from indexing.vdb import load_graph, load_vdb

    assert settings.lake is not None
    assert settings.embedding_model is not None
    saved = None
    if settings.vdb_dir is None:
        tables = load_data_lake(settings.lake)
        frames = {table.id: read_table(table) for table in tables}
        columns = format_columns(frames)
        encoder = create_encoder(settings.encoder, settings.embedding_model)
        index = ColumnIndex(columns, encoder)
    else:
        frames = {}
        encoder = create_encoder(settings.encoder, settings.embedding_model)
        saved = load_vdb(
            settings.vdb_dir,
            settings.lake,
            encoder,
            encoder_name=settings.encoder,
            model_dir=settings.embedding_model,
            channel=args.channel if args.ask is None else None,
        )
        index = saved.index

    if args.ask is None:
        return "".join(
            f"{result.table_id}.{result.column_name} "
            f"({result.column_type}) score={result.score:.4f}\n"
            for result in index.search(query, args.channel, args.top_k)
        )

    from agent import SearchConfig, run_query

    lazy_frames = LazyTableFrames(saved.tables) if saved is not None else None
    graph = load_graph(saved.generation) if saved is not None else None
    store = (
        SketchStore(saved.generation / "sketches.sqlite3")
        if saved is not None
        else nullcontext()
    )
    with store as sketches:
        answer = run_query(
            index,
            query,
            settings.chat_model,
            api_key,
            frames=frames if lazy_frames is None else lazy_frames,
            encoder=encoder,
            search=SearchConfig(**settings.search),
            statistics=sketches.statistics if sketches is not None else None,
            graph=graph,
            schemas=lazy_frames.schemas if lazy_frames is not None else None,
            key_sketch=sketches.key_sketch if sketches is not None else None,
        )
    return answer + "\n"


def _inspect_lake(directory: Path, *, validate: bool) -> None:
    if validate:
        passed, errors = validate_data_lake(directory)
        print(
            f"Checked {passed + len(errors)} CSV files: "
            f"{passed} passed, {len(errors)} failed."
        )
        for error in errors:
            print(error, file=sys.stderr)
        if errors:
            raise SystemExit(1)
        return

    tables = load_data_lake(directory)
    print(f"Found {len(tables)} tables")
    print()
    for table in tables:
        print(f"{table.id}: {', '.join(table.columns)}")


def _write_query_output(output: str, path: Path | None) -> None:
    if path is None:
        print(output, end="")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(output)


def _parse_args(parser: argparse.ArgumentParser) -> argparse.Namespace:
    parser.add_argument(
        "--config",
        type=Path,
        metavar="FILE",
        help="TOML configuration file",
    )
    parser.add_argument(
        "--lake",
        type=Path,
        metavar="DIRECTORY",
        help="CSV data lake directory",
    )
    parser.add_argument(
        "--vdb-dir",
        type=Path,
        metavar="DIRECTORY",
        help="directory for persisted lake indexes and sketches",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--build-index", action="store_true", help="build a VDB for the lake"
    )
    mode.add_argument(
        "--validate", action="store_true", help="check every CSV in the lake"
    )
    mode.add_argument("--search", metavar="QUERY", help="column search text")
    mode.add_argument(
        "--ask", metavar="QUESTION", help="ask the discovery agent"
    )
    parser.add_argument(
        "--chat-model",
        help="DeepSeek model for --ask (default: deepseek-flash)",
    )
    parser.add_argument(
        "--channel",
        choices=("metadata", "content"),
        default="metadata",
        help="column representation for --search (default: metadata)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="maximum results for --search (default: 5)",
    )
    parser.add_argument(
        "--encoder",
        choices=("bge",),
        help="text encoder for --search or --ask (default: bge)",
    )
    parser.add_argument(
        "--embedding-model",
        type=Path,
        metavar="DIRECTORY",
        help="local model directory for --search or --ask",
    )
    parser.add_argument(
        "--output",
        type=Path,
        metavar="FILE",
        help="write query results to a new UTF-8 text file",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        help="maximum discovery rounds for --ask",
    )
    parser.add_argument(
        "--stagnation-limit",
        type=int,
        help="maximum rounds without progress for --ask",
    )
    parser.add_argument(
        "--candidate-limit",
        type=int,
        help="maximum candidate tables shown per --ask round",
    )
    return parser.parse_args()


def _query_text(
    parser: argparse.ArgumentParser, args: argparse.Namespace, settings: Config
) -> str | None:
    query = args.ask if args.ask is not None else args.search
    if query is not None:
        option = "--ask" if args.ask is not None else "--search"
        if settings.lake is None or settings.embedding_model is None:
            parser.error(f"{option} requires --lake and --embedding-model")
        if not query.strip():
            parser.error(f"{option} requires non-empty text")
    if args.build_index and (
        settings.lake is None
        or settings.embedding_model is None
        or settings.vdb_dir is None
    ):
        parser.error(
            "--build-index requires --lake, --embedding-model and --vdb-dir"
        )
    if args.search is not None and args.top_k < 1:
        parser.error("--top-k must be at least 1")
    return query


@dataclasses.dataclass(frozen=True)
class Config:
    """Resolved settings shared by the command-line modes."""

    lake: Path | None = None
    vdb_dir: Path | None = None
    output: Path | None = None
    encoder: str = "bge"
    embedding_model: Path | None = None
    chat_model: str = "deepseek-flash"
    search: dict[str, int] = dataclasses.field(default_factory=dict)


_TOML_FIELDS = {
    "lake": ("data", "lake_dir"),
    "vdb_dir": ("data", "vdb_dir"),
    "output": ("output", "path"),
    "encoder": ("model", "embedding", "encoder"),
    "embedding_model": ("model", "embedding", "model_dir"),
    "chat_model": ("model", "chat", "name"),
    "max_rounds": ("search", "max_rounds"),
    "stagnation_limit": ("search", "stagnation_limit"),
    "candidate_limit": ("search", "candidate_limit"),
}
_TOML_KEYS = frozenset(_TOML_FIELDS.values())
_TOML_TABLES = {
    field[:depth] for field in _TOML_KEYS for depth in range(1, len(field))
}
_T = TypeVar("_T")


def _toml_fields(
    table: Mapping[str, object], prefix: tuple[str, ...] = ()
) -> dict[tuple[str, ...], object]:
    fields = {}
    for key, value in table.items():
        field = (*prefix, key)
        name = ".".join(field)
        if field in _TOML_TABLES:
            if not isinstance(value, dict):
                raise ValueError(f"{name} must be a table")
            fields.update(_toml_fields(value, field))
        elif field in _TOML_KEYS:
            fields[field] = value
        else:
            raise ValueError(f"unknown field {name}")
    return fields


def _text(value: object, field: str, _base: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _encoder(value: object, field: str, base: Path) -> str:
    name = _text(value, field, base)
    if name != "bge":
        raise ValueError(f"{field} must be 'bge'")
    return name


def _path(value: object, field: str, base: Path) -> Path:
    if isinstance(value, Path):
        path = value
    else:
        path = Path(_text(value, field, base))
    try:
        return base / path.expanduser()
    except RuntimeError as error:
        raise ValueError(f"{field}: {error}") from error


def _positive_int(value: object, field: str, _base: Path) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def load_config(path: Path | None, overrides: Mapping[str, object]) -> Config:
    """Read TOML settings and apply any non-None command-line values."""
    cwd = Path.cwd()
    config_dir = cwd
    fields = {}
    if path is not None:
        try:
            path = cwd / path.expanduser()
            with path.open("rb") as stream:
                fields = _toml_fields(tomllib.load(stream))
        except (OSError, RuntimeError, ValueError) as error:
            raise ValueError(f"config file {path}: {error}") from error
        config_dir = path.parent

    def get(
        key: str,
        default: _T,
        parse: Callable[[object, str, Path], _T],
    ) -> _T:
        field = _TOML_FIELDS[key]
        value = default
        if field in fields:
            value = parse(
                fields[field],
                f"config file {path}: {'.'.join(field)}",
                config_dir,
            )
        override = overrides.get(key)
        if override is not None:
            return parse(override, "--" + key.replace("_", "-"), cwd)
        return value

    search = {}
    for key in ("max_rounds", "stagnation_limit", "candidate_limit"):
        value = get(key, None, _positive_int)
        if value is not None:
            search[key] = value

    defaults = Config()
    return Config(
        lake=get("lake", defaults.lake, _path),
        vdb_dir=get("vdb_dir", defaults.vdb_dir, _path),
        output=get("output", defaults.output, _path),
        encoder=get("encoder", defaults.encoder, _encoder),
        embedding_model=get(
            "embedding_model", defaults.embedding_model, _path
        ),
        chat_model=get("chat_model", defaults.chat_model, _text),
        search=search,
    )


if __name__ == "__main__":
    main()
