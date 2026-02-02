# -*- coding: utf-8 -*-
"""
QAAgent: A specialized agent for question answering with RAG capabilities.

This agent extends AliasAgentBase to provide GitHub MCP tools and RAG (Retrieval-Augmented Generation)
functionality for answering questions based on a knowledge base stored in Qdrant.
"""
import hashlib
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Union

from loguru import logger

if TYPE_CHECKING:
    from alias.agent.tools import AliasToolkit

from agentscope.embedding import DashScopeTextEmbedding
from agentscope.message import TextBlock
from agentscope.mcp import HttpStatelessClient
from agentscope.rag import Document, SimpleKnowledge, QdrantStore, TextReader
from agentscope.rag._document import DocMetadata
from agentscope.tool import execute_shell_command

from alias.agent.agents._alias_agent_base import AliasAgentBase
from alias.agent.agents.qa_agent_utils.create_rag_file import (
    check_container_running,
    collection_exists,
    start_qdrant_container,
    split_faq_records,
)

# Qdrant configuration
QDRANT_HOST = "127.0.0.1"
QDRANT_PORT = 6333
QDRANT_CONTAINER_NAME = "qdrant"

# Default RAG file and collection when user does not specify
DEFAULT_RAG_FILE_PATH = (
    Path(__file__).parent / "qa_agent_utils" / "as_faq_samples.txt"
)
DEFAULT_COLLECTION_NAME = "as_faq"


class QAAgent(AliasAgentBase):
    """QA Agent with RAG capabilities for question answering."""

    @staticmethod
    def _get_default_system_prompt(name: str) -> str:
        """
        Get the default system prompt for QAAgent.

        Args:
            name: The agent's name.

        Returns:
            Default system prompt string.
        """
        try:
            # Try to load from the built-in prompt file
            prompt_file = Path(__file__).parent / "qa_agent_utils" / "build_in_prompt" / "qaagent_base_sys_prompt.md"
            if prompt_file.exists():
                prompt = prompt_file.read_text(encoding="utf-8")
                return prompt.format(name=name)
        except Exception as e:
            logger.warning(f"Could not load default QA prompt: {e}")
        
        # Fallback to a simple default prompt
        return (
            f"You are a helpful assistant named {name}.\n\n"
            "**IMPORTANT**: When answering questions, you MUST use the `retrieve_knowledge` tool "
            "to search for answers in the knowledge base FIRST before providing any answer. "
            "Do not answer based solely on your training data if the question might be in the knowledge base.\n\n"
            "The `query` parameter is crucial for retrieval quality. "
            "You may try multiple different queries to get the best results. "
            "Adjust the `limit` and `score_threshold` parameters to control "
            "the number and relevance of results.\n\n"
        )

    @classmethod
    async def create(
        cls,
        name: str,
        model: str = "qwen3-max",
        system_prompt: Optional[str] = None,
        tools: Optional[List[str]] = None,
        worker_full_toolkit: Optional["AliasToolkit"] = None,
        use_long_term_memory_service: bool = False,
        file: Optional[List[Union[str, Path]]] = None,
        collection_name: Optional[str] = None,
    ) -> "QAAgent":
        """
        Create a QAAgent instance with RAG capabilities.

        Args:
            name: The unique identifier name for the agent instance.
            model: The model name (e.g., "qwen3-max", "qwen-vl-max").
            system_prompt: The system prompt. If None, uses default prompt.
            tools: Tool names to register from worker_full_toolkit.
            worker_full_toolkit: Optional. If provided, use this toolkit (same sandbox/share_tools as AliasAgentBase).
                If None, create sandbox and full toolkit internally.
            use_long_term_memory_service: Whether to enable long-term memory service.
            file: List of file paths to process and add to the knowledge base. None to use default or skip.
            collection_name: Name of the Qdrant collection for RAG. None to use default 'as_faq'.

        Returns:
            A configured QAAgent instance with RAG capabilities.
        """
        # Validate inputs
        if file is not None and not isinstance(file, list):
            raise ValueError("file must be a list of file paths or None")

        # Resolve collection_name for this agent (RAG tool will use this collection)
        coll_name = collection_name if collection_name is not None else DEFAULT_COLLECTION_NAME

        qdrant_running = check_container_running(QDRANT_CONTAINER_NAME)

        if not qdrant_running:
            # RAG not initialized: start Qdrant first, then init by (file, collection_name)
            try:
                start_qdrant_container()
            except Exception as e:
                logger.warning(f"Could not start Qdrant container: {e}")
                logger.warning("RAG functionality may not work properly")
            else:
                # Resolve (files to process, collection_name) for initial load
                if file is None and collection_name is None:
                    files_to_process = [DEFAULT_RAG_FILE_PATH]
                    init_collection = DEFAULT_COLLECTION_NAME
                elif file is not None and collection_name is None:
                    files_to_process = file
                    init_collection = DEFAULT_COLLECTION_NAME
                elif file is None and collection_name is not None:
                    files_to_process = [DEFAULT_RAG_FILE_PATH]
                    init_collection = collection_name
                else:
                    files_to_process = file
                    init_collection = collection_name
                await cls._process_files(files_to_process, init_collection)
        else:
            # Qdrant already running: collection_name is the one this agent will use
            if file:
                await cls._process_files(file, coll_name)
            elif not collection_exists(coll_name):
                logger.info(
                    f"Collection '{coll_name}' does not exist; using default file to populate.",
                )
                if DEFAULT_RAG_FILE_PATH.exists():
                    await cls._process_files([DEFAULT_RAG_FILE_PATH], coll_name)
                else:
                    logger.warning(f"Default RAG file not found: {DEFAULT_RAG_FILE_PATH}")

        # Use default system prompt if not provided
        if system_prompt is None:
            system_prompt = cls._get_default_system_prompt(name)

        # Use caller's worker_full_toolkit, or build sandbox + full toolkit internally
        if worker_full_toolkit is None:
            try:
                from alias.runtime.alias_sandbox.alias_sandbox import AliasSandbox
                from alias.agent.tools import AliasToolkit
                from alias.agent.tools.add_tools import add_tools

                sandbox = AliasSandbox()
                sandbox.__enter__()
                worker_full_toolkit = AliasToolkit(sandbox, add_all=True)
                try:
                    await add_tools(worker_full_toolkit)
                except Exception as e:
                    logger.warning(f"add_tools failed: {e}; continuing with sandbox tools only")
                logger.info("Created sandbox and full toolkit for QAAgent")
            except Exception as e:
                logger.warning(f"Could not create sandbox for QAAgent: {e}")
                worker_full_toolkit = None

        # Create agent using parent's create (tools + worker_full_toolkit)
        agent = await super().create(
            name=name,
            model=model,
            system_prompt=system_prompt,
            tools=tools or [],
            worker_full_toolkit=worker_full_toolkit,
            use_long_term_memory_service=use_long_term_memory_service,
        )

        # Register RAG and GitHub tools on top of shared toolkit
        await cls._register_rag_tool(agent, coll_name)
        await cls._register_github_tools(agent)

        return agent

    @staticmethod
    async def _process_files(
        file_paths: List[Union[str, Path]],
        collection_name: str,
    ) -> None:
        """
        Process files and add them to the Qdrant collection.

        Args:
            file_paths: List of file paths to process.
            collection_name: Name of the Qdrant collection to add documents to.
        """
        logger.info(f"Processing {len(file_paths)} file(s) for collection '{collection_name}'")

        # Create knowledge base instance
        knowledge = SimpleKnowledge(
            embedding_store=QdrantStore(
                location=None,
                client_kwargs={
                    "host": QDRANT_HOST,
                    "port": QDRANT_PORT,
                },
                collection_name=collection_name,
                dimensions=1024,
            ),
            embedding_model=DashScopeTextEmbedding(
                api_key=os.environ.get("DASHSCOPE_API_KEY"),
                model_name="text-embedding-v4",
            ),
        )

        # Process each file
        reader = TextReader(chunk_size=2048, split_by="char")
        all_documents = []

        for file_path in file_paths:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}, skipping...")
                continue

            logger.info(f"Processing file: {file_path}")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    full_text = f.read()
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                continue

            # Split by FAQ records if applicable, otherwise use full text
            faq_records = split_faq_records(full_text)

            for faq_record in faq_records:
                # If the record is short enough, use it as-is
                if len(faq_record) <= 2048:
                    doc_id = hashlib.sha256(faq_record.encode("utf-8")).hexdigest()
                    all_documents.append(
                        Document(
                            id=doc_id,
                            metadata=DocMetadata(
                                content=TextBlock(type="text", text=faq_record),
                                doc_id=doc_id,
                                chunk_id=0,
                                total_chunks=1,
                            ),
                        ),
                    )
                else:
                    # If too long, split it further using TextReader
                    chunked_docs = await reader(text=faq_record)
                    all_documents.extend(chunked_docs)

        if all_documents:
            await knowledge.add_documents(all_documents)
            logger.info(
                f"Successfully added {len(all_documents)} document(s) "
                f"to collection '{collection_name}'",
            )
        else:
            logger.warning("No documents were processed from the provided files")

    @staticmethod
    async def _register_rag_tool(agent: "QAAgent", collection_name: str) -> None:
        """
        Register the retrieve_knowledge tool for RAG.

        Args:
            agent: The agent instance to register the tool for.
            collection_name: Name of the Qdrant collection to use.
        """
        import traceback

        try:
            knowledge = SimpleKnowledge(
                embedding_store=QdrantStore(
                    location=None,
                    client_kwargs={
                        "host": QDRANT_HOST,  # Qdrant server address
                        "port": QDRANT_PORT,  # Qdrant server port
                    },
                    collection_name=collection_name,
                    dimensions=1024,  # The dimension of the embedding vectors
                ),
                embedding_model=DashScopeTextEmbedding(
                    api_key=os.environ["DASHSCOPE_API_KEY"],
                    model_name="text-embedding-v4",
                ),
            )
            agent.toolkit.register_tool_function(
                knowledge.retrieve_knowledge,
                func_description=(  # Provide a clear description for the tool
                    "Quickly retrieve answers to questions related to "
                    "the knowledge base. The `query` parameter is crucial "
                    "for retrieval quality."
                    "You may try multiple different queries to get the best "
                    "results. Adjust the `limit` and `score_threshold` "
                    "parameters to control the number and relevance of results."
                ),
            )
            logger.info(f"Registered retrieve_knowledge tool with collection '{collection_name}'")
        except Exception as e:
            print(traceback.format_exc())
            raise e from None

    @staticmethod
    async def _register_github_tools(agent: "QAAgent") -> None:
        """
        Register GitHub MCP tools for the QA agent.

        Args:
            agent: The agent instance to register the tools for.
        """
        import traceback

        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            logger.error(
                "Missing GITHUB_TOKEN; GitHub MCP tools cannot be used. "
                "Please export GITHUB_TOKEN in your environment before "
                "proceeding.",
            )
        else:
            try:
                github_client = HttpStatelessClient(
                    name="github",
                    transport="streamable_http",
                    url="https://api.githubcopilot.com/mcp/",
                    headers={"Authorization": (f"Bearer {github_token}")},
                )

                await agent.toolkit.register_mcp_client(
                    github_client,
                    enable_funcs=[
                        "search_repositories",
                        "search_code",
                        "get_file_contents",
                    ],
                )
                agent.toolkit.register_tool_function(execute_shell_command)
                logger.info("Registered GitHub MCP tools")
            except Exception as e:
                print(traceback.format_exc())
                raise e from None
