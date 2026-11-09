# -*- coding: utf-8 -*-
"""Define and construct encoders for column text."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

import numpy as np


class ColumnEncoder(Protocol):
    """Encode column text as one vector per input."""

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Return contiguous, L2-normalized float32 vectors in input order.

        The result has one row per input and a fixed dimension for this
        encoder.
        """


class BGEEncoder:
    """Encode text into L2-normalized BGE vectors."""

    def __init__(self, model_path: str | Path, batch_size: int = 64) -> None:
        """Load a local Hugging Face model and select the available device."""
        if batch_size < 1:
            raise ValueError("batch_size must be positive")

        path = Path(model_path).expanduser()
        if not path.is_dir():
            raise FileNotFoundError(
                f"BGE model directory does not exist: {path}"
            )

        import torch
        from transformers import AutoModel, AutoTokenizer

        self.batch_size = batch_size
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                path, local_files_only=True
            )
            self.model = AutoModel.from_pretrained(path, local_files_only=True)
        except (OSError, ValueError, RuntimeError) as exc:
            raise RuntimeError(
                f"Could not load the local BGE model from {path}: {exc}"
            ) from exc

        self.model.to(self.device)
        self.model.eval()

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Return one contiguous float32 vector per input, in input order."""
        if isinstance(texts, str):
            raise TypeError("texts must be a sequence of strings")

        from torch import inference_mode
        from torch.nn.functional import normalize

        embeddings = np.empty(
            (len(texts), self.model.config.hidden_size), dtype=np.float32
        )
        with inference_mode():
            for start in range(0, len(texts), self.batch_size):
                stop = min(start + self.batch_size, len(texts))
                tokens = self.tokenizer(
                    list(texts[start:stop]),
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt",
                ).to(self.device)
                first_tokens = self.model(**tokens).last_hidden_state[:, 0]
                vectors = normalize(first_tokens.float(), p=2, dim=1)
                embeddings[start:stop] = vectors.cpu().numpy()

        return embeddings


def create_encoder(name: str, model_path: str | Path) -> ColumnEncoder:
    """Construct the selected encoder from a local model directory."""
    if name == "bge":
        return BGEEncoder(model_path)
    raise ValueError(f"Unknown encoder {name!r}. Supported encoder: 'bge'.")
