# -*- coding: utf-8 -*-
"""Configuration module for local_deep_research.

This module provides global instances of embedding model, vector database, and file loader.
These are lazily initialized to avoid circular imports.
"""
from typing import Optional

from local_deep_research.embedding.base import BaseEmbedding
from local_deep_research.loader.file_loader.base import BaseLoader
from local_deep_research.vector_db.base import BaseVectorDB


# Global instances (lazily initialized)
_embedding_model: Optional[BaseEmbedding] = None
_vector_db: Optional[BaseVectorDB] = None
_file_loader: Optional[BaseLoader] = None
_web_crawler: Optional[any] = None


# Create a module-level object that mimics the old configuration module
class Configuration:
    """Configuration object that provides access to global instances."""

    @property
    def embedding_model(self) -> BaseEmbedding:
        """Get embedding model."""
        global _embedding_model
        if _embedding_model is None:
            try:
                from local_deep_research.api.dependencies import get_embedding_model

                _embedding_model = get_embedding_model()
            except ImportError:
                raise RuntimeError(
                    "Embedding model not initialized. "
                    "Please initialize it via API dependencies or call set_embedding_model()."
                )
        return _embedding_model

    @property
    def vector_db(self) -> BaseVectorDB:
        """Get vector database."""
        global _vector_db
        if _vector_db is None:
            try:
                from local_deep_research.api.dependencies import get_vector_db

                _vector_db = get_vector_db()
            except ImportError:
                raise RuntimeError(
                    "Vector database not initialized. "
                    "Please initialize it via API dependencies or call set_vector_db()."
                )
        return _vector_db

    @property
    def file_loader(self) -> BaseLoader:
        """Get file loader."""
        global _file_loader
        if _file_loader is None:
            # Initialize default file loader
            try:
                from local_deep_research.loader.file_loader import PDFLoader

                _file_loader = PDFLoader()
            except ImportError:
                raise RuntimeError(
                    "File loader not initialized. Call set_file_loader() first."
                )
        return _file_loader

    @property
    def web_crawler(self):
        """Get web crawler."""
        global _web_crawler
        if _web_crawler is None:
            # Initialize default web crawler
            try:
                from local_deep_research.loader.web_crawler import FireCrawlCrawler

                _web_crawler = FireCrawlCrawler()
            except ImportError:
                raise RuntimeError(
                    "Web crawler not initialized. Call set_web_crawler() first."
                )
        return _web_crawler


# Create a singleton instance
configuration = Configuration()


def set_embedding_model(model: BaseEmbedding):
    """Set the global embedding model instance."""
    global _embedding_model
    _embedding_model = model


def set_vector_db(db: BaseVectorDB):
    """Set the global vector database instance."""
    global _vector_db
    _vector_db = db


def set_file_loader(loader: BaseLoader):
    """Set the global file loader instance."""
    global _file_loader
    _file_loader = loader


def set_web_crawler(crawler):
    """Set the global web crawler instance."""
    global _web_crawler
    _web_crawler = crawler


__all__ = [
    "configuration",
    "set_embedding_model",
    "set_vector_db",
    "set_file_loader",
    "set_web_crawler",
]
