from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class Chunk:
    """
    Represents a chunk of text with associated metadata and embedding.

    A chunk is a segment of text extracted from a document, along with its reference
    information, metadata, and optional embedding vector.

    Attributes:
        text: The text content of the chunk.
        reference: A reference to the source of the chunk (e.g., file path, URL).
        metadata: Additional metadata associated with the chunk.
        embedding: The vector embedding of the chunk, if available.
    """

    def __init__(
        self,
        text: str,
        reference: str,
        metadata: dict = None,
        embedding: List[float] = None,
    ):
        """
        Initialize a Chunk object.

        Args:
            text: The text content of the chunk.
            reference: A reference to the source of the chunk.
            metadata: Additional metadata associated with the chunk. Defaults to an empty dict.
            embedding: The vector embedding of the chunk. Defaults to None.
        """
        self.text = text
        self.reference = reference
        self.metadata = metadata or {}
        self.embedding = embedding or None


def _sentence_window_split(
    split_docs: List[Document], original_document: Document, offset: int = 200
) -> List[Chunk]:
    """
    Create chunks with context windows from split documents.

    This function takes documents that have been split into smaller pieces and
    adds context from the original document by including text before and after
    each split piece, up to the specified offset.

    Args:
        split_docs: List of documents that have been split.
        original_document: The original document before splitting.
        offset: Number of characters to include before and after each split piece.

    Returns:
        A list of Chunk objects with context windows.
    """
    chunks = []
    original_text = original_document.page_content
    for doc in split_docs:
        doc_text = doc.page_content
        start_index = original_text.index(doc_text)
        end_index = start_index + len(doc_text) - 1
        wider_text = original_text[
            max(0, start_index - offset) : min(len(original_text), end_index + offset)
        ]
        reference = doc.metadata.pop("reference", "")
        doc.metadata["wider_text"] = wider_text
        chunk = Chunk(text=doc_text, reference=reference, metadata=doc.metadata)
        chunks.append(chunk)
    return chunks


def split_docs_to_chunks(
    documents: List[Document], chunk_size: int = 1500, chunk_overlap=100
) -> List[Chunk]:
    """
    Split documents into chunks with context windows.

    This function splits a list of documents into smaller chunks with overlapping text,
    and adds context windows to each chunk by including text before and after the chunk.

    Args:
        documents: List of documents to split.
        chunk_size: Size of each chunk in characters.
        chunk_overlap: Number of characters to overlap between chunks.

    Returns:
        A list of Chunk objects with context windows.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    all_chunks = []
    for doc in documents:
        split_docs = text_splitter.split_documents([doc])
        split_chunks = _sentence_window_split(split_docs, doc, offset=300)
        all_chunks.extend(split_chunks)
    return all_chunks
