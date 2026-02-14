import os
from typing import List, Union

import requests

from local_deep_research.embedding.base import BaseEmbedding

SILICONFLOW_MODEL_DIM_MAP = {
    "BAAI/bge-m3": 1024,
    "netease-youdao/bce-embedding-base_v1": 768,
    "BAAI/bge-large-zh-v1.5": 1024,
    "BAAI/bge-large-en-v1.5": 1024,
    "Pro/BAAI/bge-m3": 1024,  # paid model
}

SILICONFLOW_EMBEDDING_API = "https://api.siliconflow.cn/v1/embeddings"


class SiliconflowEmbedding(BaseEmbedding):
    """
    SiliconFlow embedding model implementation.

    This class provides an interface to the SiliconFlow embedding API, which offers
    various embedding models for text processing.

    For more information, see:
    https://docs.siliconflow.cn/en/api-reference/embeddings/create-embeddings
    """

    def __init__(self, model="BAAI/bge-m3", batch_size=32, **kwargs):
        """
        Initialize the SiliconFlow embedding model.

        Args:
            model (str): The model identifier to use for embeddings. Default is "BAAI/bge-m3".
            batch_size (int): Maximum number of texts to process in a single batch. Default is 32.
            **kwargs: Additional keyword arguments.
                - api_key (str, optional): The SiliconFlow API key. If not provided,
                  it will be read from the SILICONFLOW_API_KEY environment variable.
                - model_name (str, optional): Alternative way to specify the model.

        Raises:
            RuntimeError: If no API key is provided or found in environment variables.
        """
        if "model_name" in kwargs and (not model or model == "BAAI/bge-m3"):
            model = kwargs.pop("model_name")
        self.model = model
        if "api_key" in kwargs:
            api_key = kwargs.pop("api_key")
        else:
            api_key = os.getenv("SILICONFLOW_API_KEY")

        if not api_key or len(api_key) == 0:
            raise RuntimeError("api_key is required for SiliconflowEmbedding")
        self.api_key = api_key
        self.batch_size = batch_size

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text.

        Args:
            text (str): The query text to embed.

        Returns:
            List[float]: A list of floats representing the embedding vector.

        Note:
            For retrieval cases, this method uses "query" as the input type.
        """
        return self._embed_input(text)[0]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of document texts.

        This method handles batching of document embeddings based on the configured
        batch size to optimize API calls.

        Args:
            texts (List[str]): A list of document texts to embed.

        Returns:
            List[List[float]]: A list of embedding vectors, one for each input text.
        """
        # batch embedding
        if self.batch_size > 0:
            if len(texts) > self.batch_size:
                batch_texts = [
                    texts[i : i + self.batch_size] for i in range(0, len(texts), self.batch_size)
                ]
                embeddings = []
                for batch_text in batch_texts:
                    batch_embeddings = self._embed_input(batch_text)
                    embeddings.extend(batch_embeddings)
                return embeddings
            return self._embed_input(texts)
        return [self.embed_query(text) for text in texts]

    def _embed_input(self, input: Union[str, List[str]]) -> List[List[float]]:
        """
        Internal method to handle the API call for embedding inputs.

        Args:
            input (Union[str, List[str]]): Either a single text string or a list of text strings to embed.

        Returns:
            List[List[float]]: A list of embedding vectors for the input(s).

        Raises:
            HTTPError: If the API request fails.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self.model, "input": input, "encoding_format": "float"}
        response = requests.request(
            "POST", SILICONFLOW_EMBEDDING_API, json=payload, headers=headers
        )
        response.raise_for_status()
        result = response.json()["data"]
        sorted_results = sorted(result, key=lambda x: x["index"])
        return [res["embedding"] for res in sorted_results]

    @property
    def dimension(self) -> int:
        """
        Get the dimensionality of the embeddings for the current model.

        Returns:
            int: The number of dimensions in the embedding vectors.
        """
        return SILICONFLOW_MODEL_DIM_MAP[self.model]
