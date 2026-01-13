# -*- coding: utf-8 -*-
"""
Prepare math data from LLM360/guru-RL-92k
Transfer to the GSM8K Format
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
from huggingface_hub import hf_hub_download

# Define constants for the dataset
DATASET_REPO = "LLM360/guru-RL-92k"
DATASET_FILE = "train/math__combined_54.4k.parquet"


# Download the dataset from Hugging Face Hub.
# The dataset is from LLM360/guru-RL-92k.
def download_dataset(
    repo_id: str,
    filename_in_repo: str,
    local_dir: str,
) -> Path:
    print(f"--- Downloading dataset: {repo_id} ---")
    print(f"File: {filename_in_repo}")

    local_path = Path(local_dir)
    local_path.mkdir(parents=True, exist_ok=True)

    try:
        downloaded_file_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename_in_repo,
            repo_type="dataset",
            local_dir=local_path,
        )
        print(f"Successfully downloaded to: {downloaded_file_path}")
        return Path(downloaded_file_path)
    except Exception as e:
        print(f"Error downloading dataset: {e}", file=sys.stderr)
        sys.exit(1)


# Transform a single row from the original format to the target format.
def transform_row(row: pd.Series) -> pd.Series:
    try:
        original_question = row["prompt"][0]["content"]
        sentence_to_remove = "Please output the final answer within \\boxed{}."
        question = original_question.replace(sentence_to_remove, "").strip()

        ground_truth = row["reward_model"]["ground_truth"]
        answer = f"#### {ground_truth}"

        rate_7b = row.get("qwen2.5_7b_pass_rate")
        rate_30b = row.get("qwen3_30b_pass_rate")

        return pd.Series(
            {
                "question": question,
                "answer": answer,
                "qwen2.5_7b_pass_rate": rate_7b,
                "qwen3_30b_pass_rate": rate_30b,
            },
        )
    except (TypeError, IndexError, KeyError) as e:
        error_msg = (
            f"Skipping row due to processing error: {e}. "
            f"Row content: {row.to_dict()}"
        )
        print(error_msg, file=sys.stderr)
        return pd.Series(
            {
                "question": None,
                "answer": None,
                "qwen2.5_7b_pass_rate": None,
                "qwen3_30b_pass_rate": None,
            },
        )


# Read, transform, and save the dataset to a new location.
def transform_and_save_dataset(input_file: Path, output_dir: str):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    output_file_path = output_path / input_file.name

    print(f"--- Reading source file: {input_file} ---")
    try:
        df_original = pd.read_parquet(input_file)
        print(f"Successfully read {len(df_original)} records.")
    except Exception as e:
        print(f"Fatal error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    print("--- Starting data transformation ---")
    df_transformed = df_original.apply(transform_row, axis=1)

    original_count = len(df_transformed)
    df_transformed.dropna(subset=["question", "answer"], inplace=True)
    dropped_count = original_count - len(df_transformed)
    if dropped_count > 0:
        print(f"Warning: Dropped {dropped_count} invalid records.")

    print(f"Transformation complete. {len(df_transformed)} generated.")

    print(f"--- Saving processed file to: {output_file_path} ---")
    try:
        df_transformed.to_parquet(output_file_path, index=False)
        print(f"Process complete! New file saved at: {output_file_path}")
    except Exception as e:
        print(f"Fatal error saving file: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Download and transform the guru-RL-92k math dataset.",
    )
    parser.add_argument(
        "--raw_data_dir",
        type=str,
        default="data/train/raw",
        help="Directory to download the raw dataset file.",
    )
    parser.add_argument(
        "--processed_data_dir",
        type=str,
        default="data/train/math",
        help="Directory to save the transformed dataset file.",
    )

    args = parser.parse_args()

    downloaded_file = download_dataset(
        repo_id=DATASET_REPO,
        filename_in_repo=DATASET_FILE,
        local_dir=args.raw_data_dir,
    )

    transform_and_save_dataset(
        input_file=downloaded_file,
        output_dir=args.processed_data_dir,
    )


if __name__ == "__main__":
    main()
