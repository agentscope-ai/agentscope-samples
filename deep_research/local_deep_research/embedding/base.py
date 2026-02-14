from typing import List

from tqdm import tqdm

from local_deep_research.loader.splitter import Chunk


class BaseEmbedding:
    """
    Abstract base class for embedding model implementations.

    This class defines the interface for embedding model implementations,
    including methods for embedding queries and documents, and a property
    for the dimensionality of the embeddings.
    """

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text.

        Args:
            text: The query text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        pass

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of document texts.

        This default implementation calls embed_query for each text,
        but implementations may override this with a more efficient batch method.

        Args:
            texts: A list of document texts to embed.

        Returns:
            A list of embedding vectors, one for each input text.
        """
        return [self.embed_query(text) for text in texts]

    def embed_chunks(self, chunks: List[Chunk], batch_size: int = 256) -> List[Chunk]:
        """
        Embed a list of Chunk objects.

        This method extracts the text from each chunk, embeds it in batches,
        and updates the chunks with their embeddings.

        Args:
            chunks: A list of Chunk objects to embed.
            batch_size: The number of chunks to process in each batch.

        Returns:
            The input list of Chunk objects, updated with embeddings.
        """
        texts = [chunk.text for chunk in chunks]
        batch_texts = [texts[i : i + batch_size] for i in range(0, len(texts), batch_size)]
        embeddings = []
        for batch_text in tqdm(batch_texts, desc="Embedding chunks"):
            batch_embeddings = self.embed_documents(batch_text)
            embeddings.extend(batch_embeddings)
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
        return chunks

    @property
    def dimension(self) -> int:
        """
        Get the dimensionality of the embeddings.

        Returns:
            The number of dimensions in the embedding vectors.
        """
        pass
