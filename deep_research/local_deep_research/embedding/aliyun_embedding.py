import os
from typing import Any, Callable, List, Optional

from requests.exceptions import HTTPError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from local_deep_research.embedding.base import BaseEmbedding

# Default dimensions according to official documentation
DASHSCOPE_MODEL_DIM_MAP = {
    "text-embedding-v1": 1536,
    "text-embedding-v2": 1536,
    "text-embedding-v3": 1024,
    "text-embedding-v4": 1024,
}

# Batch size limits
BATCH_SIZE_MAP = {
    "text-embedding-v1": 25,
    "text-embedding-v2": 25,
    "text-embedding-v3": 10,
    "text-embedding-v4": 10,
}


def _create_retry_decorator(max_retries: int) -> Callable[[Any], Any]:
    """Create retry decorator with exponential backoff"""
    multiplier = 1
    min_seconds = 1
    max_seconds = 4
    # Exponential backoff: 2^x * 1 second, min 1 second, max 4 seconds
    return retry(
        reraise=True,
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier, min=min_seconds, max=max_seconds),
        retry=(retry_if_exception_type(HTTPError)),
    )


class AliyunEmbedding(BaseEmbedding):
    """
    Aliyun DashScope embedding model implementation.

    This class provides an interface to the Aliyun DashScope embedding API,
    which offers various embedding models for text processing.

    For more information, see:
    - Sync API: https://bailian.console.aliyun.com/?tab=api#/api/?type=model&url=2712515
    - Async API: https://bailian.console.aliyun.com/?tab=api#/api/?type=model&url=2712516
    """

    def __init__(
        self,
        model: str = "text-embedding-v3",
        api_key: Optional[str] = None,
        dimension: Optional[int] = None,
        max_retries: int = 5,
        **kwargs
    ):
        """
        Initialize the Aliyun DashScope embedding model.

        Args:
            model (str): The model identifier to use for embeddings.
                Default is "text-embedding-v3".
            api_key (str, optional): The DashScope API key. If not provided,
                it will be read from the DASHSCOPE_API_KEY environment variable.
            dimension (int, optional): The dimension of the embedding vectors.
                If not provided, the default dimension for the model will be used.
            max_retries (int): Maximum number of retries for API calls. Default is 5.
            **kwargs: Additional keyword arguments.

        Notes:
            Available models and dimensions:
                - 'text-embedding-v1': 1536 (default)
                - 'text-embedding-v2': 1536 (default)
                - 'text-embedding-v3': 1024 (default), 768, 512, 256, 128, 64
                - 'text-embedding-v4': 2048, 1536, 1024 (default), 768, 512, 256, 128, 64

            Supported languages (100+ languages for v3 and v4):
                Chinese, English, Spanish, French, Portuguese, Indonesian, Japanese,
                Korean, German, Russian, and many more
        """
        # Get API key
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "DashScope API key must be provided either via api_key parameter "
                "or DASHSCOPE_API_KEY environment variable"
            )

        # Set model
        self.model = model

        # Set dimension
        if dimension is not None:
            self.dim = dimension
        else:
            self.dim = DASHSCOPE_MODEL_DIM_MAP.get(model, 1024)

        # Set max retries
        self.max_retries = max_retries

        # Get batch size
        self.batch_size = BATCH_SIZE_MAP.get(model, 10)

        # Initialize DashScope client
        try:
            import dashscope
        except ImportError:
            raise ImportError(
                "Could not import dashscope python package. "
                "Please install it with `pip install dashscope` or `uv pip install dashscope`."
            )

        # Set API key
        dashscope.api_key = self.api_key
        self.client = dashscope.TextEmbedding

    def _embed_with_retry(
        self, input_data: List[str] | str, text_type: str
    ) -> List[dict]:
        """
        Call embedding API with retry mechanism.

        Args:
            input_data: Input text or list of texts
            text_type: Text type, "query" or "document"

        Returns:
            List of dictionaries containing embeddings
        """
        retry_decorator = _create_retry_decorator(self.max_retries)

        @retry_decorator
        def _embed() -> List[dict]:
            result = []
            # Ensure input_data is a list
            texts = [input_data] if isinstance(input_data, str) else input_data
            input_len = len(texts)

            # Process in batches
            i = 0
            while i < input_len:
                batch_texts = texts[i : i + self.batch_size]

                # Call DashScope API
                resp = self.client.call(
                    model=self.model, input=batch_texts, text_type=text_type
                )

                if resp.status_code == 200:
                    result.extend(resp.output["embeddings"])
                elif resp.status_code in [400, 401]:
                    raise ValueError(
                        f"status_code: {resp.status_code}\n"
                        f"code: {resp.code}\nmessage: {resp.message}"
                    )
                else:
                    raise HTTPError(
                        f"HTTP error occurred: status_code: {resp.status_code}\n"
                        f"code: {resp.code}\nmessage: {resp.message}",
                        response=resp,
                    )

                i += self.batch_size

            return result

        return _embed()

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text.

        Args:
            text (str): The query text to embed.

        Returns:
            List[float]: A list of floats representing the embedding vector.
        """
        embeddings = self._embed_with_retry(input_data=text, text_type="query")
        return embeddings[0]["embedding"]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of document texts.

        Args:
            texts (List[str]): A list of document texts to embed.

        Returns:
            List[List[float]]: A list of embedding vectors, one for each input text.
        """
        embeddings = self._embed_with_retry(input_data=texts, text_type="document")
        return [item["embedding"] for item in embeddings]

    @property
    def dimension(self) -> int:
        """
        Get the dimensionality of the embeddings for the current model.

        Returns:
            int: The number of dimensions in the embedding vectors.
        """
        return self.dim
