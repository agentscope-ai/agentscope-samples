# -*- coding: utf-8 -*-
import os

from dotenv import load_dotenv
from mem0.configs.base import MemoryConfig
from mem0.embeddings.configs import EmbedderConfig
from mem0.graphs.configs import GraphStoreConfig
from mem0.llms.configs import LlmConfig
from mem0.vector_stores.configs import VectorStoreConfig
from pydantic_settings import BaseSettings

from alias.memory_service.profiling_utils.logging_utils import setup_logging

logger = setup_logging()

# Load environment variables from .env file
load_dotenv()

MEM0_DEFAULT_LLM_CONFIG = LlmConfig(
    provider="openai",
    config={
        "model": os.environ.get("DASHSCOPE_MODEL_4_MEMORY"),
        "api_key": os.environ.get("DASHSCOPE_API_KEY"),
        "openai_base_url": os.environ.get("DASHSCOPE_API_BASE_URL"),
    },
)
MEM0_DEFAULT_EMBEDDER_CONFIG = EmbedderConfig(
    provider="openai",
    config={
        "model": os.environ.get("DASHSCOPE_EMBEDDER", "text-embedding-v4"),
        "api_key": os.environ.get("DASHSCOPE_API_KEY"),
        "openai_base_url": os.environ.get("DASHSCOPE_API_BASE_URL"),
        "embedding_dims": os.environ.get("QDRANT_EMBEDDING_MODEL_DIMS", 1536),
    },
)
MEM0_DEFAULT_GRAPH_CONFIG = GraphStoreConfig(
    provider="neo4j",
    config={
        "url": os.environ.get("NEO4J_URL", "neo4j://127.0.0.1:7687"),
        "username": os.environ.get("NEO4J_USER", "neo4j"),
        "password": os.environ.get("NEO4J_PASSWORD", "12345678"),
        "database": "userprofiling",
    },
    llm=MEM0_DEFAULT_LLM_CONFIG,
)

MEM0_DEFAULT_VECTOR_STORE_CONFIG = VectorStoreConfig(
    provider="qdrant",
    config={
        "host": os.environ.get("QDRANT_HOST", "localhost"),
        "port": os.environ.get("QDRANT_PORT", 6333),
        "collection_name": os.environ.get(
            "QDRANT_COLLECTION_NAME",
            "my_mem0_memory",
        ),
        "embedding_model_dims": os.environ.get(
            "QDRANT_EMBEDDING_MODEL_DIMS",
            1536,
        ),
        "on_disk": True,
    },
)

MEM0_DEFAULT_MEMORY_CONFIG = MemoryConfig(
    embedder=MEM0_DEFAULT_EMBEDDER_CONFIG,
    llm=MEM0_DEFAULT_LLM_CONFIG,
    # graph_store=MEM0_DEFAULT_GRAPH_CONFIG,
    vector_store=MEM0_DEFAULT_VECTOR_STORE_CONFIG,
)


class Mem0Config(BaseSettings):
    MEM0_LLM_CONFIG: LlmConfig = MEM0_DEFAULT_LLM_CONFIG
    MEM0_EMBEDDER_CONFIG: EmbedderConfig = MEM0_DEFAULT_EMBEDDER_CONFIG
    # MEM0_GRAPH_CONFIG: GraphStoreConfig = MEM0_DEFAULT_GRAPH_CONFIG
    MEM0_MEMORY_CONFIG: MemoryConfig = MEM0_DEFAULT_MEMORY_CONFIG


class UserProfilingServiceConfig(BaseSettings):
    MEM0_CONFIG: Mem0Config = Mem0Config()


def create_memory_config_with_collection(
    collection_name: str,
    use_graph_store: bool = False,
    persist_history: bool = False,
) -> MemoryConfig:
    """
    Create a MemoryConfig instance with specified collection name and
    optional graph store.

    Args:
        collection_name (str): Name of the collection for vector storage
        use_graph_store (bool, optional): Flag to include graph store
            configuration. Defaults to False.
        persist_history (bool, optional): Flag to persist history to disk.
            Defaults to False.

    Returns:
        MemoryConfig: Configured memory settings with vector store
            (and optionally graph store)
    """
    # Create vector store configuration for Qdrant
    # vector_store_config = VectorStoreConfig(
    #     provider="qdrant",
    #     config={
    #         "collection_name": collection_name,
    #         "path": f"tmp/{collection_name}",  # Local storage path
    #         "on_disk": persist_history
    #     }
    # )
    vector_store_config = VectorStoreConfig(
        provider="qdrant",
        config={
            "host": os.environ.get("QDRANT_HOST", "localhost"),
            "port": os.environ.get("QDRANT_PORT", 6333),
            "collection_name": collection_name,
            "embedding_model_dims": os.environ.get(
                "QDRANT_EMBEDDING_MODEL_DIMS",
                1536,
            ),
            # "path": f"tmp/db/{collection_name}",
            "on_disk": persist_history,
        },
    )

    # Build memory configuration with optional graph store
    if use_graph_store:
        config = MemoryConfig(
            embedder=MEM0_DEFAULT_EMBEDDER_CONFIG,  # Default embedding
            llm=MEM0_DEFAULT_LLM_CONFIG,  # Default LLM settings
            graph_store=MEM0_DEFAULT_GRAPH_CONFIG,  # Include graph DB
            vector_store=vector_store_config,  # Qdrant vector store
            # history_db_path=f"tmp/db/{collection_name}"
        )
    else:
        config = MemoryConfig(
            embedder=MEM0_DEFAULT_EMBEDDER_CONFIG,
            llm=MEM0_DEFAULT_LLM_CONFIG,
            vector_store=vector_store_config,  # Qdrant without graph
            # history_db_path = f"tmp/db/{collection_name}.db"
            history_db_path=os.path.join(
                os.path.expanduser("~"),
                ".mem0",
                f"{collection_name}.db",
            ),
        )
    logger.info(f"config: {config}")
    return config
