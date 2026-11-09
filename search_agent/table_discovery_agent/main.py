# -*- coding: utf-8 -*-
"""Run the table discovery command-line interface."""

import argparse
from pathlib import Path

from data_lake import load_data_lake


def main() -> None:
    """List CSV tables or search their columns."""
    parser = argparse.ArgumentParser(
        description="List CSV tables and search their columns."
    )
    parser.add_argument(
        "--lake",
        type=Path,
        metavar="DIRECTORY",
        help="CSV data lake directory",
    )
    parser.add_argument("--search", metavar="QUERY", help="column search text")
    parser.add_argument(
        "--channel",
        choices=("metadata", "content"),
        default="metadata",
        help="column representation to search (default: metadata)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="maximum number of search results (default: 5)",
    )
    parser.add_argument(
        "--encoder",
        choices=("bge",),
        default="bge",
        help="text encoder to use for search (default: bge)",
    )
    parser.add_argument(
        "--embedding-model",
        type=Path,
        metavar="DIRECTORY",
        help="local model directory for the encoder (required for search)",
    )
    args = parser.parse_args()

    if args.search is not None:
        if args.lake is None or args.embedding_model is None:
            parser.error("--search requires --lake and --embedding-model")
        if not args.search.strip():
            parser.error("--search requires non-empty text")
        if args.top_k < 1:
            parser.error("--top-k must be at least 1")

    if args.lake is None:
        parser.print_help()
        return

    try:
        tables = load_data_lake(args.lake)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    if args.search is None:
        print(f"Found {len(tables)} tables")
        print()
        for table in tables:
            print(f"{table.id}: {', '.join(table.columns)}")
        return

    try:
        from data_lake import read_table
        from indexing import ColumnIndex, format_columns
        from indexing.embedding import create_encoder

        frames = {table.id: read_table(table) for table in tables}
        index = ColumnIndex(
            format_columns(frames),
            create_encoder(args.encoder, args.embedding_model),
        )
        results = index.search(args.search, args.channel, args.top_k)
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    for result in results:
        print(
            f"{result.table_id}.{result.column_name} "
            f"({result.column_type}) score={result.score:.4f}"
        )


if __name__ == "__main__":
    main()
