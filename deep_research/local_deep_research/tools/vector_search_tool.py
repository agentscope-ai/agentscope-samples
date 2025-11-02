# -*- coding: utf-8 -*-
"""Vector Database Search Tool for AgentScope.

This module provides tools for searching vector databases using text queries.
The tools are designed to be registered with AgentScope's toolkit system.
"""
from typing import List, Optional

from agentscope.tool import ToolResponse
from agentscope.message import TextBlock

from local_deep_research.embedding.base import BaseEmbedding
from local_deep_research.utils import log
from local_deep_research.vector_db.base import BaseVectorDB, RetrievalResult


def create_vector_search_tool(
    embedding_model: BaseEmbedding,
    vector_db: BaseVectorDB,
):
    """
    Create a vector search tool function bound to specific embedding model and vector database.

    This factory function creates a closure that captures the embedding model and vector database
    instances, returning a tool function ready to be registered with AgentScope's toolkit.

    Args:
        embedding_model (BaseEmbedding): The embedding model instance for converting text to vectors.
        vector_db (BaseVectorDB): The vector database instance for searching.

    Returns:
        callable: An async tool function that can be registered with AgentScope's toolkit.

    Example:
        >>> from local_deep_research.embedding import OpenAIEmbedding
        >>> from local_deep_research.vector_db import Milvus
        >>>
        >>> embedding = OpenAIEmbedding(api_key="your-key")
        >>> vector_db = Milvus(uri="http://localhost:19530")
        >>>
        >>> search_tool = create_vector_search_tool(embedding, vector_db)
        >>> toolkit.register_tool_function(search_tool)
    """

    async def search_vector_database(
        query_text: str,
        collection: Optional[str] = None,
        top_k: int = 5,
    ) -> ToolResponse:
        """
        Search the vector database for relevant documents based on query text.

        This tool converts the input text to a vector embedding and searches the vector database
        for the most similar documents. It supports both dense vector search and hybrid search
        (dense + sparse) depending on the vector database configuration.

        Args:
            query_text (str): The text query to search for.
            collection (Optional[str]): The collection name to search in.
                If None, uses the default collection. Defaults to None.
            top_k (int): The number of top results to return. Defaults to 5.

        Returns:
            ToolResponse: A formatted response containing the search results.
                The response includes the matched documents with their text,
                reference, metadata, and similarity scores.

        Example:
            >>> result = await search_vector_database(
            ...     query_text="What is AgentScope?",
            ...     top_k=3
            ... )
        """
        try:
            # Step 1: Convert query text to vector embedding
            log.info(f"Embedding query text: {query_text[:100]}...")
            query_vector = embedding_model.embed_query(query_text)

            # Step 2: Search vector database
            log.info(
                f"Searching in collection: {collection or vector_db.default_collection} "
                f"with top_k={top_k}"
            )

            # Check if vector_db supports hybrid search
            use_hybrid = getattr(vector_db, "hybrid", False)
            search_kwargs = {
                "collection": collection,
                "vector": query_vector,
                "top_k": top_k,
            }

            # Add query_text for hybrid search if supported
            if use_hybrid:
                search_kwargs["query_text"] = query_text
                log.info("Using hybrid search (dense + sparse vectors)")

            results: List[RetrievalResult] = vector_db.search_data(**search_kwargs)

            # Step 3: Format results
            if not results:
                return ToolResponse(
                    content=[
                        TextBlock(
                            type="text",
                            text="No relevant documents found in the vector database.",
                        )
                    ]
                )

            formatted_results = _format_search_results(results, query_text)

            log.info(f"Found {len(results)} relevant documents")

            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=formatted_results,
                    )
                ]
            )

        except Exception as e:
            error_message = f"Error searching vector database: {str(e)}"
            log.error(error_message)
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=error_message,
                    )
                ]
            )

    # Set function metadata for AgentScope toolkit
    search_vector_database.__name__ = "search_vector_database"
    search_vector_database.__doc__ = """
    Search the vector database for relevant documents based on query text.

    Args:
        query_text (str): The text query to search for.
        collection (Optional[str]): The collection name to search in. If None, uses default.
        top_k (int): The number of top results to return. Defaults to 5.

    Returns:
        Formatted search results with matched documents.
    """

    return search_vector_database


def create_list_collections_tool(vector_db: BaseVectorDB):
    """
    Create a list collections tool function bound to a specific vector database.

    This factory function creates a closure that captures the vector database instance,
    returning a tool function that can list all available collections.

    Args:
        vector_db (BaseVectorDB): The vector database instance.

    Returns:
        callable: A tool function that can be registered with AgentScope's toolkit.

    Example:
        >>> from local_deep_research.vector_db import Milvus
        >>> vector_db = Milvus(uri="http://localhost:19530")
        >>> list_tool = create_list_collections_tool(vector_db)
        >>> toolkit.register_tool_function(list_tool)
    """

    def list_collections() -> ToolResponse:
        """
        List all available collections in the vector database.

        This tool helps you discover what collections are available for searching.
        You should call this tool first to understand what knowledge bases exist,
        then choose the most appropriate collection(s) for your search query.

        Returns:
            ToolResponse: A formatted response containing all available collections
                with their names and descriptions.

        Example:
            >>> result = list_collections()
        """
        try:
            log.info("Listing all collections in vector database")
            collections = vector_db.list_collections()

            if not collections:
                return ToolResponse(
                    content=[
                        TextBlock(
                            type="text",
                            text="No collections found in the vector database. "
                            "Please load some documents first.",
                        )
                    ]
                )

            # Format collections list
            formatted_output = _format_collections_list(collections)
            log.info(f"Found {len(collections)} collection(s)")

            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=formatted_output,
                    )
                ]
            )

        except Exception as e:
            error_message = f"Error listing collections: {str(e)}"
            log.error(error_message)
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=error_message,
                    )
                ]
            )

    # Set function metadata for AgentScope toolkit
    list_collections.__name__ = "list_collections"
    list_collections.__doc__ = """
    List all available collections in the vector database.

    This tool helps you discover what collections (knowledge bases) are available.
    Call this first to understand what data sources you can search from.

    Returns:
        A formatted list of all collections with their names and descriptions.
    """

    return list_collections


def _format_collections_list(collections: List) -> str:
    """
    Format collections list into a readable string for the agent.

    Args:
        collections (List): List of CollectionInfo objects from vector database.

    Returns:
        str: Formatted string containing all collections information.
    """
    output = "# Available Collections in Vector Database\n\n"
    output += f"**Total: {len(collections)} collection(s)**\n\n"
    output += "---\n\n"

    for idx, collection in enumerate(collections, 1):
        output += f"## {idx}. Collection: `{collection.collection_name}`\n\n"
        
        if collection.description:
            output += f"**Description:** {collection.description}\n\n"
        else:
            output += "**Description:** No description available\n\n"
        
        output += "---\n\n"

    output += "\n**Usage Tip:** When searching, specify the `collection` parameter "
    output += "in `search_vector_database` to search a specific collection.\n"

    return output.strip()


def _format_search_results(results: List[RetrievalResult], query: str) -> str:
    """
    Format retrieval results into a readable string for the agent.

    Args:
        results (List[RetrievalResult]): List of retrieval results from vector database.
        query (str): The original query text.

    Returns:
        str: Formatted string containing all search results.
    """
    output = "# Vector Database Search Results\n\n"
    output += f"**Query:** {query}\n"
    output += f"**Found {len(results)} relevant document(s)**\n\n"

    for idx, result in enumerate(results, 1):
        output += f"## Result {idx}\n\n"
        output += f"**Similarity Score:** {result.score:.4f}\n\n"
        output += f"**Content:**\n{result.text}\n\n"

        if result.reference:
            output += f"**Source:** {result.reference}\n\n"

        if result.metadata:
            metadata_str = ", ".join(f"{k}: {v}" for k, v in result.metadata.items())
            output += f"**Metadata:** {metadata_str}\n\n"

        output += "---\n\n"

    return output.strip()
