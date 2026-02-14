# -*- coding: utf-8 -*-
"""Document loading API routes."""
import os
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from local_deep_research.embedding.base import BaseEmbedding
from local_deep_research.offline_loading import load_from_local_files, load_from_website
from local_deep_research.utils import log
from local_deep_research.vector_db.base import BaseVectorDB

from ..config import settings
from ..dependencies import get_embedding_dependency, get_vector_db_dependency
from ..models import (
    CollectionInfo,
    CollectionListResponse,
    DocumentLoadRequest,
    DocumentLoadResponse,
    ErrorResponse,
    FileUploadResponse,
    WebsiteLoadRequest,
    WebsiteLoadResponse,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Upload a document file",
    description="Upload a file to the server for later processing",
)
async def upload_file(file: UploadFile = File(...)) -> FileUploadResponse:
    """Upload a document file.

    Args:
        file (UploadFile): The file to upload.

    Returns:
        FileUploadResponse: Upload result with file path.

    Raises:
        HTTPException: If upload fails.
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # Save file
        file_path = os.path.join(settings.upload_dir, file.filename)

        # Read and write file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        file_size = len(content)

        log.info(f"File uploaded: {file.filename} ({file_size} bytes)")

        return FileUploadResponse(
            filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            status="success",
        )

    except Exception as e:
        log.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post(
    "/load",
    response_model=DocumentLoadResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Load documents into vector database",
    description="Load documents from file paths or directories into the vector database",
)
async def load_documents(
    request: DocumentLoadRequest,
    embedding: BaseEmbedding = Depends(get_embedding_dependency),
    vector_db: BaseVectorDB = Depends(get_vector_db_dependency),
) -> DocumentLoadResponse:
    """Load documents into vector database.

    Args:
        request (DocumentLoadRequest): Load request parameters.
        embedding (BaseEmbedding): Embedding model dependency.
        vector_db (BaseVectorDB): Vector database dependency.

    Returns:
        DocumentLoadResponse: Load result.

    Raises:
        HTTPException: If loading fails.
    """
    try:
        # Validate file paths
        for path in request.file_paths:
            if not os.path.exists(path):
                raise HTTPException(
                    status_code=400, detail=f"Path does not exist: {path}"
                )

        # Use settings defaults if not provided
        collection_name = request.collection_name or settings.vector_db.default_collection
        chunk_size = request.chunk_size or settings.load_settings.chunk_size
        chunk_overlap = request.chunk_overlap or settings.load_settings.chunk_overlap

        log.info(f"Loading documents into collection: {collection_name}")
        log.info(f"File paths: {request.file_paths}")
        log.info(f"Chunk size: {chunk_size}, overlap: {chunk_overlap}")

        # Count files before loading
        files_count = 0
        for path in request.file_paths:
            if os.path.isdir(path):
                files_count += sum(1 for _ in os.walk(path))
            else:
                files_count += 1

        # Load documents
        load_from_local_files(
            paths_or_directory=request.file_paths,
            collection_name=collection_name,
            collection_description=request.collection_description,
            force_new_collection=request.force_new_collection,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        log.info(f"Documents loaded successfully into {collection_name}")

        # TODO: Get actual chunk count from load_from_local_files
        # For now, estimate based on files
        estimated_chunks = files_count * 10  # Rough estimate

        return DocumentLoadResponse(
            collection_name=collection_name,
            files_processed=files_count,
            chunks_created=estimated_chunks,
            status="success",
            message=f"Successfully loaded {files_count} files into collection '{collection_name}'",
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Document loading failed: {e}")
        raise HTTPException(status_code=500, detail=f"Loading failed: {str(e)}")


@router.post(
    "/load-from-website",
    response_model=WebsiteLoadResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Load website content into vector database",
    description="Crawl and load content from websites into the vector database",
)
async def load_website(
    request: WebsiteLoadRequest,
    embedding: BaseEmbedding = Depends(get_embedding_dependency),
    vector_db: BaseVectorDB = Depends(get_vector_db_dependency),
) -> WebsiteLoadResponse:
    """Load website content into vector database.

    Args:
        request (WebsiteLoadRequest): Load request parameters.
        embedding (BaseEmbedding): Embedding model dependency.
        vector_db (BaseVectorDB): Vector database dependency.

    Returns:
        WebsiteLoadResponse: Load result.

    Raises:
        HTTPException: If loading fails.
    """
    try:
        # Validate URLs
        if not request.urls:
            raise HTTPException(status_code=400, detail="URLs list cannot be empty")

        # Use settings defaults if not provided
        collection_name = request.collection_name or settings.vector_db.default_collection
        chunk_size = request.chunk_size or settings.load_settings.chunk_size
        chunk_overlap = request.chunk_overlap or settings.load_settings.chunk_overlap
        batch_size = request.batch_size or 256

        log.info(f"Loading website content into collection: {collection_name}")
        log.info(f"URLs: {request.urls}")
        log.info(f"Chunk size: {chunk_size}, overlap: {chunk_overlap}, batch size: {batch_size}")

        # Load website content
        load_from_website(
            urls=request.urls,
            collection_name=collection_name,
            collection_description=request.collection_description,
            force_new_collection=request.force_new_collection,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            batch_size=batch_size,
        )

        log.info(f"Website content loaded successfully into {collection_name}")

        # TODO: Get actual chunk count from load_from_website
        # For now, estimate based on URLs
        estimated_chunks = len(request.urls) * 50  # Rough estimate

        return WebsiteLoadResponse(
            collection_name=collection_name,
            urls_processed=len(request.urls),
            chunks_created=estimated_chunks,
            status="success",
            message=f"Successfully loaded content from {len(request.urls)} URLs into collection '{collection_name}'",
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Website loading failed: {e}")
        raise HTTPException(status_code=500, detail=f"Loading failed: {str(e)}")


@router.get(
    "/collections",
    response_model=CollectionListResponse,
    responses={500: {"model": ErrorResponse}},
    summary="List all collections",
    description="Get a list of all collections in the vector database",
)
async def list_collections(
    vector_db: BaseVectorDB = Depends(get_vector_db_dependency),
) -> CollectionListResponse:
    """List all collections in vector database.

    Args:
        vector_db (BaseVectorDB): Vector database dependency.

    Returns:
        CollectionListResponse: List of collections.

    Raises:
        HTTPException: If listing fails.
    """
    try:
        # Get collections from vector database
        collections = vector_db.list_collections()

        # Convert to response model
        collection_infos = [
            CollectionInfo(
                collection_name=col.collection_name,
                description=col.description,
                document_count=None,  # TODO: Get actual count if available
            )
            for col in collections
        ]

        return CollectionListResponse(
            collections=collection_infos,
            total_count=len(collection_infos),
        )

    except Exception as e:
        log.error(f"Failed to list collections: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list collections: {str(e)}")


@router.delete(
    "/collections/{collection_name}",
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Delete a collection",
    description="Delete a collection from the vector database",
)
async def delete_collection(
    collection_name: str,
    vector_db: BaseVectorDB = Depends(get_vector_db_dependency),
) -> dict:
    """Delete a collection.

    Args:
        collection_name (str): Name of collection to delete.
        vector_db (BaseVectorDB): Vector database dependency.

    Returns:
        dict: Deletion result.

    Raises:
        HTTPException: If deletion fails.
    """
    try:
        # Check if collection exists
        collections = vector_db.list_collections()
        collection_names = [col.collection_name for col in collections]

        if collection_name not in collection_names:
            raise HTTPException(
                status_code=404, detail=f"Collection not found: {collection_name}"
            )

        # Delete collection
        vector_db.clear_db(collection=collection_name)

        log.info(f"Collection deleted: {collection_name}")

        return {
            "status": "success",
            "message": f"Collection '{collection_name}' deleted successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Failed to delete collection: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete collection: {str(e)}"
        )
