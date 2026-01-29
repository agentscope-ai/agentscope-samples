# -*- coding: utf-8 -*-
"""
DeepFinance dataset preparation (tuner-compatible)

Converts DeepFinance task JSON files into HuggingFace-friendly JSONL files.

Usage:
    python _deep_finance_reader.py \
      --train_input /path/to/train_tasks.json \
      --val_input /path/to/val_tasks.json \
      --output_dir /path/to/data
"""

from __future__ import annotations

import argparse
import json
import os
from decimal import Decimal
from typing import Any, Dict, Iterator


class _DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal objects."""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return int(obj) if obj == obj.to_integral_value() else float(obj)
        return super().default(obj)


def _json_dumps(obj: Any) -> str:
    """Safe JSON dumps with Decimal support."""
    try:
        return json.dumps(obj, ensure_ascii=False, cls=_DecimalEncoder)
    except Exception:
        return json.dumps(str(obj), ensure_ascii=False)


def _normalize_split(split: str) -> str:
    """Normalize split name to train/validation/test (HuggingFace standard)."""
    s = (split or "").strip().lower()
    if s in ("val", "valid", "validation", "dev"):
        return "validation"
    if s == "test":
        return "test"
    return "train"


def _load_json_file(path: str) -> Any:
    """Load JSON file (supports both .json and .jsonl)."""
    with open(path, "r", encoding="utf-8") as f:
        if path.endswith(".jsonl"):
            return [json.loads(line) for line in f if line.strip()]
        return json.load(f)


def _iter_records(data: Any) -> Iterator[Dict[str, Any]]:
    """
    Iterate over records from loaded JSON data.
    
    Supports:
    - List of records: [{"task": {...}}, ...]
    - Dict keyed by task_id: {"task_id_1": {"task": {...}}, ...}
    - Dict with "data" key: {"data": [...]}
    """
    if isinstance(data, list):
        yield from (obj for obj in data if isinstance(obj, dict))
    elif isinstance(data, dict):
        # Check if it's a dict of records (keyed by task_id)
        first_val = next(iter(data.values()), None) if data else None
        if isinstance(first_val, dict) and ("task" in first_val or "query" in first_val):
            yield from data.values()
        elif "data" in data and isinstance(data["data"], list):
            yield from (obj for obj in data["data"] if isinstance(obj, dict))
        else:
            yield data


def _convert_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Convert one raw record into a tuner-friendly sample dict."""
    task = raw.get("task") if isinstance(raw.get("task"), dict) else raw
    task_meta = task.get("metadata") if isinstance(task.get("metadata"), dict) else {}

    task_id = str(task.get("task_id") or task.get("id") or raw.get("task_id") or "")
    query = str(task.get("query") or task.get("question") or raw.get("query") or "")

    return {
        "task_id": task_id,
        "query": query,
        "messages": [{"role": "user", "content": query}],
        "init_messages": [{"role": "user", "content": query}],
        "domain": str(task_meta.get("domain") or raw.get("domain") or ""),
        "split": _normalize_split(str(task_meta.get("split") or raw.get("split") or "train")),
        "env_type": str(task.get("env_type") or raw.get("env_type") or ""),
        "evaluator": str(task.get("evaluator") or raw.get("evaluator") or ""),
        "ground_truth": str(task.get("ground_truth") or raw.get("ground_truth") or ""),
        "confidence": raw.get("confidence"),
        "reward": raw.get("reward"),
        "metadata_json": _json_dumps(task_meta),
        "raw_task_json": _json_dumps(raw),
    }


def build_dataset(
    output_dir: str,
    train_input: str | None = None,
    val_input: str | None = None,
    test_input: str | None = None,
) -> Dict[str, int]:
    """
    Convert input files and write train/val/test JSONL files.
    
    Args:
        output_dir: Output directory for JSONL files.
        train_input: Path to training data file.
        val_input: Path to validation data file.
        test_input: Path to test data file.
    
    Returns:
        Dict with counts per split.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    input_files = [
        (train_input, "train"),
        (val_input, "validation"),
        (test_input, "test"),
    ]
    counts = {"train": 0, "validation": 0, "test": 0}

    for input_path, split_name in input_files:
        if not input_path:
            continue
            
        print(f"Processing {input_path} as '{split_name}' split...")
        data = _load_json_file(input_path)
        output_path = os.path.join(output_dir, f"{split_name}.jsonl")
        
        with open(output_path, "w", encoding="utf-8") as f:
            for raw in _iter_records(data):
                sample = _convert_record(raw)
                sample["split"] = split_name  # Force split
                f.write(_json_dumps(sample) + "\n")
                counts[split_name] += 1
        
        # Remove empty file
        if counts[split_name] == 0 and os.path.exists(output_path):
            os.remove(output_path)

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare DeepFinance dataset for tuner.")
    parser.add_argument("--train_input", type=str, help="Path to training data .json/.jsonl")
    parser.add_argument("--val_input", type=str, help="Path to validation data .json/.jsonl")
    parser.add_argument("--test_input", type=str, help="Path to test data .json/.jsonl")
    parser.add_argument("--output_dir", type=str, required=True, help="Output directory")
    parser.add_argument("--input", type=str, help="(Legacy) Same as --train_input")
    args = parser.parse_args()

    train_input = args.train_input or args.input
    if not any([train_input, args.val_input, args.test_input]):
        raise ValueError("At least one input file required (--train_input, --val_input, or --test_input)")

    counts = build_dataset(
        output_dir=args.output_dir,
        train_input=train_input,
        val_input=args.val_input,
        test_input=args.test_input,
    )
    print(f"Done. Split counts: {counts}")
    print(f"Output: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()


"""
Example:
python _deep_finance_reader.py \
  --train_input ori_data/train_cc423_11171143_tasks.json \
  --val_input ori_data/val_30_tasks.json \
  --output_dir data
"""
