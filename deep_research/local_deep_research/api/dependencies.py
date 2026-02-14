# -*- coding: utf-8 -*-
"""Dependency injection for FastAPI.

This module provides singleton instances of:
- Embedding model
- Vector database
- Agent (lazy-loaded per request)
"""
from typing import Optional

from agentscope.formatter import DashScopeChatFormatter, OpenAIChatFormatter 
from agentscope.memory import InMemoryMemory
from agentscope.model import DashScopeChatModel, OpenAIChatModel

from local_deep_research.agent import LocalDeepResearchAgent
from local_deep_research.embedding import (
    AliyunEmbedding,
    OpenAIEmbedding,
    SentenceTransformerEmbedding,
    SiliconflowEmbedding,
)
from local_deep_research.embedding.base import BaseEmbedding
from local_deep_research.utils import log
from local_deep_research.vector_db import Milvus
from local_deep_research.vector_db.base import BaseVectorDB

from .config import settings


# ==================== Global Singletons ====================


_embedding_model: Optional[BaseEmbedding] = None
_vector_db: Optional[BaseVectorDB] = None


def get_embedding_model() -> BaseEmbedding:
    """Get or create embedding model singleton.

    Returns:
        BaseEmbedding: Embedding model instance.
    """
    global _embedding_model

    if _embedding_model is None:
        log.info(f"Initializing embedding model: {settings.embedding.provider}")

        provider = settings.embedding.provider
        config = settings.embedding

        if provider == "SiliconflowEmbedding":
            _embedding_model = SiliconflowEmbedding(
                model=config.model,
                api_key=config.api_key,
                base_url=config.base_url,
            )
        elif provider == "OpenAIEmbedding":
            _embedding_model = OpenAIEmbedding(
                model=config.model,
                api_key=config.api_key,
                base_url=config.base_url,
            )
        elif provider == "AliyunEmbedding":
            _embedding_model = AliyunEmbedding(
                model=config.model,
                api_key=config.api_key,
            )
        elif provider == "SentenceTransformerEmbedding":
            _embedding_model = SentenceTransformerEmbedding(
                model=config.model,
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")

        log.info(f"Embedding model initialized: dimension={_embedding_model.dimension}")

    return _embedding_model


def get_vector_db() -> BaseVectorDB:
    """Get or create vector database singleton.

    Returns:
        BaseVectorDB: Vector database instance.
    """
    global _vector_db

    if _vector_db is None:
        log.info(f"Initializing vector database: {settings.vector_db.provider}")

        provider = settings.vector_db.provider
        config = settings.vector_db

        if provider == "Milvus":
            _vector_db = Milvus(
                default_collection=config.default_collection,
                uri=config.uri,
                token=config.token,
                db=config.db,
                hybrid=config.hybrid,
            )
        else:
            raise ValueError(f"Unsupported vector DB provider: {provider}")

        log.info(f"Vector database initialized: {config.uri}")

    return _vector_db


def create_agent(
    max_iters: Optional[int] = None,
    max_depth: Optional[int] = None,
) -> LocalDeepResearchAgent:
    """Create a new agent instance.

    Note: Agent is NOT a singleton - each request gets a fresh agent instance
    to avoid state conflicts between concurrent requests.

    Args:
        max_iters (Optional[int]): Override maximum iterations.
        max_depth (Optional[int]): Override maximum search depth.

    Returns:
        LocalDeepResearchAgent: New agent instance.
    """
    log.info("Creating new LocalDeepResearchAgent instance")

    # Get singletons
    embedding_model = get_embedding_model()
    vector_db = get_vector_db()

    # Use provided values or fall back to settings
    max_iters = max_iters or settings.agent.max_iters
    max_depth = max_depth or settings.agent.max_depth

    # Create LLM model based on provider
    provider = settings.llm.provider
    log.info(f"Creating LLM model with provider: {provider}")
    
    if provider == "DashScope":
        # DashScope (Aliyun Qwen models)
        llm_model = DashScopeChatModel(
            model_name=settings.llm.model,
            api_key=settings.llm.api_key,
            enable_thinking=settings.llm.enable_thinking,
            stream=True,
        )
        formatter = DashScopeChatFormatter()
        log.info("Using DashScopeChatModel with DashScopeChatFormatter")
        
    elif provider == "OpenAI":
        # OpenAI-compatible APIs (OpenAI, ZhipuAI/BigModel, etc.)
        # Note: extra_body should be in generate_kwargs, not client_args
        # client_args only accepts parameters for openai.AsyncClient() initialization
        client_args = {}
        if settings.llm.base_url:
            client_args["base_url"] = settings.llm.base_url
            
        generate_kwargs = {}
        # For ZhipuAI thinking mode
        if settings.llm.enable_thinking:
            generate_kwargs["extra_body"] = {
                "thinking": {
                    "type": "enabled",
                }
            }
        
        llm_model = OpenAIChatModel(
            model_name=settings.llm.model,
            api_key=settings.llm.api_key,
            client_args=client_args,
            generate_kwargs=generate_kwargs,
        )
        formatter = OpenAIChatFormatter()
        log.info("Using OpenAIChatModel with OpenAIChatFormatter")
        
    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. "
            f"Supported providers: 'OpenAI', 'DashScope'"
        )

    # Create agent with appropriate formatter
    agent_kwargs = {
        "name": "LocalResearcher",
        "sys_prompt": (
            "You are a helpful research assistant with access to a local knowledge base. "
            "Use the search_vector_database tool to find relevant information when answering questions. "
            "Provide comprehensive, well-researched answers based on the retrieved documents. "
            "Always cite your sources and be transparent about the limitations of your knowledge."
        ),
        "model": llm_model,
        "memory": InMemoryMemory(),
        "embedding_model": embedding_model,
        "vector_db": vector_db,
        "max_iters": max_iters,
        "max_depth": max_depth,
        "tmp_file_storage_dir": settings.tmp_file_storage_dir,
    }
    
    # Add formatter (always required)
    agent_kwargs["formatter"] = formatter
    
    agent = LocalDeepResearchAgent(**agent_kwargs)

    log.info(f"Agent created: max_iters={max_iters}, max_depth={max_depth}")
    return agent


# ==================== Dependency Functions ====================


async def get_embedding_dependency() -> BaseEmbedding:
    """FastAPI dependency for embedding model.

    Returns:
        BaseEmbedding: Embedding model instance.
    """
    return get_embedding_model()


async def get_vector_db_dependency() -> BaseVectorDB:
    """FastAPI dependency for vector database.

    Returns:
        BaseVectorDB: Vector database instance.
    """
    return get_vector_db()


async def get_agent_dependency(
    max_iters: Optional[int] = None,
    max_depth: Optional[int] = None,
) -> LocalDeepResearchAgent:
    """FastAPI dependency for agent.

    Note: Creates a new agent instance for each request.

    Args:
        max_iters (Optional[int]): Override maximum iterations.
        max_depth (Optional[int]): Override maximum search depth.

    Returns:
        LocalDeepResearchAgent: Agent instance.
    """
    return create_agent(max_iters=max_iters, max_depth=max_depth)


# ==================== Initialization ====================


def initialize_components():
    """Initialize all components at startup.

    This ensures embedding model and vector database are loaded
    before handling any requests.
    """
    log.info("Initializing application components...")

    try:
        # Initialize embedding model
        embedding_model = get_embedding_model()
        log.info(f"✓ Embedding model ready: {embedding_model.dimension}D")

        # Initialize vector database
        vector_db = get_vector_db()
        log.info(f"✓ Vector database ready: {vector_db.default_collection}")

        # Verify default collection exists
        embedding_dim = embedding_model.dimension
        try:
            vector_db.init_collection(
                dim=embedding_dim,
                collection=settings.vector_db.default_collection,
                description="Default collection for local deep research",
                force_new_collection=False,
            )
            log.info(f"✓ Default collection verified: {settings.vector_db.default_collection}")
        except Exception as e:
            log.warning(f"Could not verify default collection: {e}")

        log.info("All components initialized successfully!")

    except Exception as e:
        log.error(f"Failed to initialize components: {e}")
        raise


def cleanup_components():
    """Cleanup components on shutdown."""
    global _embedding_model, _vector_db

    log.info("Cleaning up application components...")

    _embedding_model = None
    _vector_db = None

    log.info("Cleanup completed")
