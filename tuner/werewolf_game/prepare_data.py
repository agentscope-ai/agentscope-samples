#!/usr/bin/env python
# -*- coding: utf-8 -*-
# flake8: noqa: E501
"""Prepare dataset for werewolf game training.

This script generates a simple dataset consisting of random seeds for role shuffling.
Each seed creates a different initial role assignment, ensuring diverse training scenarios.
"""
import json
import argparse
from pathlib import Path


def prepare_dataset(
    output_dir: str,
    num_seeds: int = 300,
    split: str = "train",
) -> None:
    """Prepare the werewolf game training dataset.

    Args:
        output_dir (str): Directory to save the dataset.
        num_seeds (int): Number of seeds to generate. Default: 300.
        split (str): Dataset split name (e.g., 'train', 'eval'). Default: 'train'.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    output_file = output_path / f"{split}.jsonl"

    print(f"Generating {num_seeds} seeds for {split} split...")

    with open(output_file, "w", encoding="utf-8") as f:
        for seed in range(num_seeds):
            data = {"seed": seed}
            f.write(json.dumps(data) + "\n")

    print(f"Dataset saved to: {output_file}")
    print(f"Total samples: {num_seeds}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Prepare dataset for werewolf game training",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="data",
        help="Directory to save the dataset (default: data)",
    )
    parser.add_argument(
        "--num_seeds",
        type=int,
        default=300,
        help="Number of seeds to generate (default: 300)",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="train",
        help="Dataset split name (default: train)",
    )

    args = parser.parse_args()

    prepare_dataset(
        output_dir=args.output_dir,
        num_seeds=args.num_seeds,
        split=args.split,
    )
