# -*- coding: utf-8 -*-
"""Pydantic models for API requests and responses."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== Research Query Models ====================


class ResearchRequest(BaseModel):
    """Research query request model."""

    query: str = Field(..., description="Research query text", min_length=1)
    collection: Optional[str] = Field(None, description="Vector database collection to search")
    max_iters: Optional[int] = Field(None, description="Maximum iterations for research")
    max_depth: Optional[int] = Field(None, description="Maximum search depth")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "query": "What is AgentScope and how does it support multi-agent systems?",
                "collection": "deepsearcher",
                "max_iters": 30,
                "max_depth": 3,
            }
        }


class ResearchResponse(BaseModel):
    """Research query response model."""

    query: str = Field(..., description="Original query")
    result: str = Field(..., description="Research result")
    agent_name: str = Field(..., description="Agent name")
    report_path: Optional[str] = Field(None, description="Path to detailed report")
    status: str = Field("success", description="Request status")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "query": "What is AgentScope?",
                "result": "AgentScope is a flexible and user-friendly...",
                "agent_name": "LocalResearcher",
                "report_path": "./tmp/LocalResearcher_20250102123456_detailed_report.md",
                "status": "success",
            }
        }


# ==================== Document Loading Models ====================


class DocumentLoadRequest(BaseModel):
    """Document loading request model."""

    file_paths: List[str] = Field(..., description="List of file paths or directories to load")
    collection_name: Optional[str] = Field(None, description="Collection name to store documents")
    collection_description: Optional[str] = Field(
        None, description="Collection description"
    )
    force_new_collection: bool = Field(
        False, description="Force create new collection if exists"
    )
    chunk_size: Optional[int] = Field(None, description="Chunk size for document splitting")
    chunk_overlap: Optional[int] = Field(None, description="Chunk overlap size")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "file_paths": ["./docs/agentscope_intro.md", "./docs/tutorials/"],
                "collection_name": "agentscope_docs",
                "collection_description": "AgentScope documentation",
                "force_new_collection": False,
                "chunk_size": 1500,
                "chunk_overlap": 100,
            }
        }


class DocumentLoadResponse(BaseModel):
    """Document loading response model."""

    collection_name: str = Field(..., description="Collection name")
    files_processed: int = Field(..., description="Number of files processed")
    chunks_created: int = Field(..., description="Number of chunks created")
    status: str = Field("success", description="Request status")
    message: str = Field(..., description="Status message")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "collection_name": "agentscope_docs",
                "files_processed": 15,
                "chunks_created": 234,
                "status": "success",
                "message": "Successfully loaded documents into vector database",
            }
        }


class WebsiteLoadRequest(BaseModel):
    """Website loading request model."""

    urls: List[str] = Field(..., description="List of URLs to crawl and load")
    collection_name: Optional[str] = Field(None, description="Collection name to store documents")
    collection_description: Optional[str] = Field(
        None, description="Collection description"
    )
    force_new_collection: bool = Field(
        False, description="Force create new collection if exists"
    )
    chunk_size: Optional[int] = Field(None, description="Chunk size for document splitting")
    chunk_overlap: Optional[int] = Field(None, description="Chunk overlap size")
    batch_size: Optional[int] = Field(256, description="Batch size for embedding")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "urls": ["https://example.com/docs", "https://example.com/tutorials"],
                "collection_name": "example_website",
                "collection_description": "Example website documentation",
                "force_new_collection": False,
                "chunk_size": 1500,
                "chunk_overlap": 100,
                "batch_size": 256,
            }
        }


class WebsiteLoadResponse(BaseModel):
    """Website loading response model."""

    collection_name: str = Field(..., description="Collection name")
    urls_processed: int = Field(..., description="Number of URLs processed")
    chunks_created: int = Field(..., description="Number of chunks created")
    status: str = Field("success", description="Request status")
    message: str = Field(..., description="Status message")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "collection_name": "example_website",
                "urls_processed": 2,
                "chunks_created": 150,
                "status": "success",
                "message": "Successfully loaded website content into vector database",
            }
        }


class FileUploadResponse(BaseModel):
    """File upload response model."""

    filename: str = Field(..., description="Uploaded filename")
    file_path: str = Field(..., description="Saved file path")
    file_size: int = Field(..., description="File size in bytes")
    status: str = Field("success", description="Upload status")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "filename": "document.pdf",
                "file_path": "./uploads/document.pdf",
                "file_size": 1048576,
                "status": "success",
            }
        }


# ==================== Collection Management Models ====================


class CollectionInfo(BaseModel):
    """Collection information model."""

    collection_name: str = Field(..., description="Collection name")
    description: str = Field(..., description="Collection description")
    document_count: Optional[int] = Field(None, description="Number of documents")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "collection_name": "deepsearcher",
                "description": "Default collection",
                "document_count": 1234,
            }
        }


class CollectionListResponse(BaseModel):
    """Collection list response model."""

    collections: List[CollectionInfo] = Field(..., description="List of collections")
    total_count: int = Field(..., description="Total number of collections")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "collections": [
                    {
                        "collection_name": "deepsearcher",
                        "description": "Default collection",
                        "document_count": 1234,
                    }
                ],
                "total_count": 1,
            }
        }


# ==================== Error Response Models ====================


class ErrorResponse(BaseModel):
    """Error response model."""

    status: str = Field("error", description="Request status")
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "status": "error",
                "error": "ValueError",
                "message": "Invalid query parameter",
                "details": {"query": "Query cannot be empty"},
            }
        }


# ==================== Health Check Models ====================


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str = Field("healthy", description="Service status")
    vector_db_connected: bool = Field(..., description="Vector database connection status")
    embedding_model_loaded: bool = Field(..., description="Embedding model loaded status")
    version: str = Field("1.0.0", description="API version")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "status": "healthy",
                "vector_db_connected": True,
                "embedding_model_loaded": True,
                "version": "1.0.0",
            }
        }
