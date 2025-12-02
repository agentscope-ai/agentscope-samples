# -*- coding: utf-8 -*-
import os
from typing import TYPE_CHECKING
import traceback
from loguru import logger
from agentscope.mcp import HttpStatelessClient
from agentscope.embedding import DashScopeTextEmbedding
from agentscope.rag import SimpleKnowledge, QdrantStore
from agentscope.tool import execute_shell_command

if TYPE_CHECKING:
    from alias.agent.tools.alias_toolkit import AliasToolkit
else:
    AliasToolkit = "alias.agent.tools.alias_toolkit.AliasToolkit"


async def add_qa_tools(
    toolkit: AliasToolkit,
):
    """
    Adding additional MCP server to the toolkit for QA Agent.
    Currently added MCP:
    - RAG
    - GitHub MCP
    """
    # toolkit.create_tool_group(
    #     group_name="qa_mode",
    #     description="The tools used in QA mode to answer user's question",
    #     active=False,
    # )
    try:
        # Check and initialize RAG data if needed
        from alias.agent.agents.qa_agent_utils.create_rag_file import (
            check_rag_initialized,
            initialize_rag,
            SCRIPT_DIR,
        )

        collection_name = "as_faq"
        is_initialized = await check_rag_initialized(collection_name)

        if not is_initialized:
            logger.info("RAG data not found. Initializing RAG data...")
            # Check for custom FAQ file in the qaagent_tools directory
            custom_faq_file = SCRIPT_DIR / "as_faq_samples.txt"

            if custom_faq_file.exists():
                logger.info(f"Using FAQ file: {custom_faq_file}")
                await initialize_rag(
                    faq_file_path=custom_faq_file,
                    collection_name=collection_name,
                )
            else:
                logger.warning(
                    f"FAQ file not found at {custom_faq_file}. "
                    "Please ensure as_faq_samples.txt exists "
                    "in the qa_agent_utils directory.",
                )
                logger.info("Attempting to use default FAQ file...")
                await initialize_rag(collection_name=collection_name)
            logger.info("RAG data initialization completed.")
        else:
            logger.info(
                "RAG data already initialized. Skipping initialization.",
            )

        knowledge = SimpleKnowledge(
            embedding_store=QdrantStore(
                # location=":memory:",
                location=None,
                client_kwargs={
                    "host": "127.0.0.1",  # Qdrant server address
                    "port": 6333,  # Qdrant server port
                },
                collection_name="as_faq",
                dimensions=1024,  # The dimension of the embedding vectors
            ),
            embedding_model=DashScopeTextEmbedding(
                api_key=os.environ["DASHSCOPE_API_KEY"],
                model_name="text-embedding-v4",
            ),
        )
        toolkit.register_tool_function(
            knowledge.retrieve_knowledge,
            func_description=(  # Provide a clear description for the tool
                "Quickly retrieve answers to questions related to "
                "the AgentScope FAQ. The `query` parameter is crucial "
                "for retrieval quality."
                "You may try multiple different queries to get the best "
                "results. Adjust the `limit` and `score_threshold` "
                "parameters to control the number and relevance of results."
            ),
            # group_name="qa_mode",
        )
    except Exception as e:
        print(traceback.format_exc())
        raise e from None

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

            await toolkit.register_mcp_client(
                github_client,
                enable_funcs=[
                    "search_repositories",
                    "search_code",
                    "get_file_contents",
                ],
                # group_name="qa_mode",
            )
            toolkit.register_tool_function(execute_shell_command)
        except Exception as e:
            print(traceback.format_exc())
            raise e from None
