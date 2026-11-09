# -*- coding: utf-8 -*-
"""Run the table discovery command-line interface."""

import argparse
import os
from pathlib import Path

from data_lake import load_data_lake


def main() -> None:
    """List CSV tables, search columns, or ask the discovery agent."""
    parser = argparse.ArgumentParser(
        description="List CSV tables and discover their columns."
    )
    parser.add_argument(
        "--lake",
        type=Path,
        metavar="DIRECTORY",
        help="CSV data lake directory",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--search", metavar="QUERY", help="column search text")
    mode.add_argument(
        "--ask", metavar="QUESTION", help="ask the discovery agent"
    )
    parser.add_argument(
        "--chat-model",
        default="deepseek-flash",
        help="DeepSeek model for --ask (default: %(default)s)",
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
        default="bge",
        help="text encoder for --search or --ask (default: bge)",
    )
    parser.add_argument(
        "--embedding-model",
        type=Path,
        metavar="DIRECTORY",
        help="local model directory for --search or --ask",
    )
    args = parser.parse_args()

    query = args.ask if args.ask is not None else args.search
    if query is not None:
        option = "--ask" if args.ask is not None else "--search"
        if args.lake is None or args.embedding_model is None:
            parser.error(f"{option} requires --lake and --embedding-model")
        if not query.strip():
            parser.error(f"{option} requires non-empty text")
    if args.search is not None and args.top_k < 1:
        parser.error("--top-k must be at least 1")

    api_key = (
        os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if args.ask is not None
        else ""
    )
    if args.ask is not None and not api_key:
        parser.error(
            "--ask requires the DEEPSEEK_API_KEY environment variable"
        )

    if args.lake is None:
        parser.print_help()
        return

    try:
        tables = load_data_lake(args.lake)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    if query is None:
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
        columns = format_columns(frames)
        encoder = create_encoder(args.encoder, args.embedding_model)
        index = ColumnIndex(columns, encoder)
        if args.ask is not None:
            from agent import run_query

            print(
                run_query(
                    index,
                    args.ask,
                    args.chat_model,
                    api_key,
                    frames=frames,
                    encoder=encoder,
                )
            )
            return

        results = index.search(args.search, args.channel, args.top_k)
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        message = str(error)
        parser.error(
            message.replace(api_key, "[redacted]") if api_key else message
        )

    for result in results:
        print(
            f"{result.table_id}.{result.column_name} "
            f"({result.column_type}) score={result.score:.4f}"
        )


if __name__ == "__main__":
    main()
