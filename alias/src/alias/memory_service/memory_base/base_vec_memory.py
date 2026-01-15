# -*- coding: utf-8 -*-
import asyncio
import concurrent
import gc
import hashlib
import json
import uuid
import warnings
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytz
from pydantic import ValidationError

from mem0.configs.base import MemoryConfig, MemoryItem
from mem0.configs.enums import MemoryType
from mem0.configs.prompts import (
    PROCEDURAL_MEMORY_SYSTEM_PROMPT,
    get_update_memory_messages,
)
from mem0.memory.base import MemoryBase
from mem0.memory.setup import setup_config
from mem0.memory.telemetry import capture_event
from mem0.memory.utils import (
    get_fact_retrieval_messages,
    parse_messages,
    parse_vision_messages,
    remove_code_blocks,
)
from mem0.utils.factory import EmbedderFactory, LlmFactory, VectorStoreFactory

from alias.memory_service.memory_base.storage import SQLiteManager
from alias.memory_service.profiling_utils.logging_utils import setup_logging
from alias.memory_service.profiling_utils.memory_utils import (
    build_filters_and_metadata,
    extract_json_from_text,
    run_async_in_thread,
)
from .prompt import GET_MEMORY_TYPE

logger = setup_logging()

setup_config()
# logger = logger.getLogger(__name__)


class BaseAsyncVectorMemory(MemoryBase):
    # Adapted from mem0.memory.main.AsyncMemory.__init__
    def __init__(self, config: MemoryConfig = MemoryConfig()):
        self.config = config

        self.embedding_model = EmbedderFactory.create(
            self.config.embedder.provider,
            self.config.embedder.config,
            self.config.vector_store.config,
        )
        self.vector_store = VectorStoreFactory.create(
            self.config.vector_store.provider,
            self.config.vector_store.config,
        )
        self.llm = LlmFactory.create(
            self.config.llm.provider,
            self.config.llm.config,
        )
        self.db = SQLiteManager(self.config.history_db_path)
        self.collection_name = self.config.vector_store.config.collection_name
        self.api_version = self.config.version

        self.enable_graph = False

        if self.config.graph_store.config:
            from mem0.memory.graph_memory import MemoryGraph

            self.graph = MemoryGraph(self.config)
            self.enable_graph = True
        else:
            self.graph = None

        capture_event("mem0.init", self, {"sync_type": "async"})

    @classmethod
    # Adapted from mem0.memory.main.AsyncMemory.from_config
    async def from_config(cls, config_dict: Dict[str, Any]):
        try:
            config = cls._process_config(config_dict)
            config = MemoryConfig(**config_dict)
        except ValidationError as e:
            logger.error(f"Configuration validation error: {e}")
            raise
        return cls(config)

    @staticmethod
    # Adapted from mem0.memory.main.AsyncMemory._process_config
    def _process_config(config_dict: Dict[str, Any]) -> Dict[str, Any]:
        if "graph_store" in config_dict:
            if "vector_store" not in config_dict and "embedder" in config_dict:
                config_dict["vector_store"] = {}
                config_dict["vector_store"]["config"] = {}
                config_dict["vector_store"]["config"][
                    "embedding_model_dims"
                ] = config_dict["embedder"]["config"]["embedding_dims"]
        try:
            return config_dict
        except ValidationError as e:
            logger.error(f"Configuration validation error: {e}")
            raise

    def _prepare_metadata_for_add(
        self,
        metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Hook for subclasses to normalize metadata before `add` processing.
        By default it returns a shallow template that downstream helpers
        can mutate.
        """
        return deepcopy(metadata) if metadata else {}

    async def _on_existing_memory_retrieved(
        self,
        _memory_ids: List[str],
        _metadata: Dict[str, Any],
        _filters: Dict[str, Any],
    ) -> None:
        """
        Hook invoked after retrieving existing memories during `add`.
        Subclasses can override to perform side effects such as metadata
        updates.
        """
        return None

    async def add(
        self,
        messages,
        *,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        infer: bool = True,
        memory_type: Optional[str] = None,
        prompt: Optional[str] = None,
        llm=None,
        extract_facts: bool = False,
    ):
        # Adapted from mem0.memory.main.AsyncMemory.add
        """
        Create a new memory asynchronously.

        Args:
            messages (str or List[Dict[str, str]]): Messages to store in
                the memory.
            user_id (str, optional): ID of the user creating the memory.
            agent_id (str, optional): ID of the agent creating the memory.
                Defaults to None.
            run_id (str, optional): ID of the run creating the memory.
                Defaults to None.
            metadata (dict, optional): Metadata to store with the memory.
                Defaults to None.
            infer (bool, optional): Whether to infer the memories.
                Defaults to True.
            memory_type (str, optional): Type of memory to create.
                Defaults to None. Pass "procedural_memory" to create
                procedural memories.
            prompt (str, optional): Prompt to use for the memory creation.
                Defaults to None.
            llm (BaseChatModel, optional): LLM class to use for generating
                procedural memories. Defaults to None. Useful when user is
                using LangChain ChatModel.
            extract_facts (bool, optional): Whether to extract facts from
                the memory. Defaults to False.
        Returns:
            dict: A dictionary containing the result of the memory addition
                operation.
        """
        metadata_template = self._prepare_metadata_for_add(metadata)
        processed_metadata, effective_filters = build_filters_and_metadata(
            user_id=user_id,
            agent_id=agent_id,
            run_id=run_id,
            input_metadata=metadata_template,
        )

        if (
            memory_type is not None
            and memory_type != MemoryType.PROCEDURAL.value
        ):
            raise ValueError(
                f"Invalid 'memory_type'. Please pass "
                f"{MemoryType.PROCEDURAL.value} to create procedural "
                f"memories.",
            )

        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        elif isinstance(messages, dict):
            messages = [messages]

        elif not isinstance(messages, list):
            raise ValueError("messages must be str, dict, or list[dict]")

        if agent_id is not None and memory_type == MemoryType.PROCEDURAL.value:
            results = await self._create_procedural_memory(
                messages,
                metadata=processed_metadata,
                prompt=prompt,
                llm=llm,
            )
            return results

        if self.config.llm.config.get("enable_vision"):
            messages = parse_vision_messages(
                messages,
                self.llm,
                self.config.llm.config.get("vision_details"),
            )
        else:
            messages = parse_vision_messages(messages)

        vector_store_task = asyncio.create_task(
            self._add_to_vector_store(
                messages,
                processed_metadata,
                effective_filters,
                infer,
                extract_facts,
            ),
        )
        graph_task = asyncio.create_task(
            self._add_to_graph(messages, effective_filters),
        )

        vector_store_result, graph_result = await asyncio.gather(
            vector_store_task,
            graph_task,
        )

        if self.api_version == "v1.0":
            warnings.warn(
                "The current add API output format is deprecated. "
                "To use the latest format, set `api_version='v1.1'`. "
                "The current format will be removed in mem0ai 1.1.0 "
                "and later versions.",
                category=DeprecationWarning,
                stacklevel=2,
            )
            return vector_store_result

        if self.enable_graph:
            return {
                "results": vector_store_result,
                "relations": graph_result,
            }

        return {"results": vector_store_result}

    async def _add_messages_without_inference(
        self,
        messages: list,
        metadata: dict,
    ) -> list:
        """Add messages directly to vector store without inference."""
        returned_memories = []
        for message_dict in messages:
            if (
                not isinstance(message_dict, dict)
                or message_dict.get("role") is None
                or message_dict.get("content") is None
            ):
                logger.warning(
                    f"Skipping invalid message format (async): {message_dict}",
                )
                continue

            if message_dict["role"] == "system":
                continue

            per_msg_meta = deepcopy(metadata)
            per_msg_meta["role"] = message_dict["role"]

            actor_name = message_dict.get("name")
            if actor_name:
                per_msg_meta["actor_id"] = actor_name

            msg_content = message_dict["content"]
            msg_embeddings = await asyncio.to_thread(
                self.embedding_model.embed,
                msg_content,
                "add",
            )
            mem_id = await self._create_memory(
                msg_content,
                {msg_content: msg_embeddings},
                per_msg_meta,
            )

            returned_memories.append(
                {
                    "id": mem_id,
                    "memory": msg_content,
                    "event": "ADD",
                    "actor_id": actor_name if actor_name else None,
                    "role": message_dict["role"],
                },
            )
        return returned_memories

    async def _extract_facts_from_messages(self, messages: list) -> list:
        """Extract facts from messages using LLM."""
        parsed_messages = parse_messages(messages)
        if self.config.custom_fact_extraction_prompt:
            system_prompt = self.config.custom_fact_extraction_prompt
            user_prompt = f"Input:\n{parsed_messages}"
        else:
            system_prompt, user_prompt = get_fact_retrieval_messages(
                parsed_messages,
            )

        response = await asyncio.to_thread(
            self.llm.generate_response,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={
                "type": (
                    "json_object"
                    if "qwen-max" not in self.config.llm.config["model"]
                    else "text"
                ),
            },
        )

        parsed_response = self._parse_llm_json_response(
            response,
            expected_key="facts",
        )
        return (
            parsed_response.get("facts", [])
            if isinstance(parsed_response, dict)
            else []
        )

    async def _search_existing_memories(
        self,
        content_list: list,
        effective_filters: dict,
    ) -> tuple:
        """Search for existing memories similar to the given content list."""
        retrieved_memories = []
        embeddings_map = {}

        async def process_content_for_search(content):
            embeddings = await asyncio.to_thread(
                self.embedding_model.embed,
                content,
                "add",
            )
            embeddings_map[content] = embeddings
            existing_mems = await asyncio.to_thread(
                self.vector_store.search,
                query=content,
                vectors=embeddings,
                limit=5,
                filters=effective_filters,
            )
            return [
                {"id": mem.id, "text": mem.payload["data"]}
                for mem in existing_mems
            ]

        search_tasks = [
            process_content_for_search(content) for content in content_list
        ]
        search_results_list = await asyncio.gather(*search_tasks)

        for result_group in search_results_list:
            retrieved_memories.extend(result_group)

        return retrieved_memories, embeddings_map

    async def _prepare_memory_for_update(
        self,
        retrieved_memories: list,
        metadata: dict,
        effective_filters: dict,
    ) -> tuple:
        """Prepare retrieved memories for update: deduplicate and create
        UUID mapping."""
        existing_memory_ids = list({item["id"] for item in retrieved_memories})
        if existing_memory_ids:
            await self._on_existing_memory_retrieved(
                existing_memory_ids,
                metadata,
                effective_filters,
            )

        # Deduplicate
        unique_data = {item["id"]: item for item in retrieved_memories}
        deduplicated_memories = list(unique_data.values())

        # Create temporary UUID mapping
        uuid_mapping = {}
        for idx, item in enumerate(deduplicated_memories):
            uuid_mapping[str(idx)] = item["id"]
            deduplicated_memories[idx]["id"] = str(idx)

        return deduplicated_memories, uuid_mapping

    def _parse_llm_json_response(
        self,
        response: str,
        expected_key: str = None,
    ) -> dict:
        """Parse LLM JSON response with fallback error handling."""
        try:
            response = remove_code_blocks(response)
            parsed = json.loads(response)
            if expected_key and expected_key not in parsed:
                return {}
            return parsed
        except Exception as e:
            try:
                parsed = extract_json_from_text(response)
                if isinstance(parsed, dict):
                    if expected_key is None or expected_key in parsed:
                        return parsed
                logger.error(f"Invalid JSON response: {e}")
            except Exception as e2:
                logger.error(f"Error parsing JSON response: {e2}")
            return {}

    async def _generate_memory_actions(
        self,
        retrieved_memories: list,
        content_list: list,
    ) -> dict:
        """Generate memory actions (ADD/UPDATE/DELETE) from LLM."""
        prompt = get_update_memory_messages(
            retrieved_memories,
            content_list,
            self.config.custom_update_memory_prompt,
        )

        try:
            response = await asyncio.to_thread(
                self.llm.generate_response,
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": (
                        "json_object"
                        if "qwen-max" not in self.config.llm.config["model"]
                        else "text"
                    ),
                },
            )
        except Exception as e:
            logger.error(f"Error in new memory actions response: {e}")
            return {}

        return (
            self._parse_llm_json_response(response, expected_key="memory")
            or {}
        )

    def _create_memory_task_for_event(
        self,
        action: dict,
        uuid_mapping: dict,
        embeddings_map: dict,
        metadata: dict,
    ):
        """Create a memory task for a specific event type
        (ADD/UPDATE/DELETE)."""
        action_text = action.get("text")
        if not action_text:
            return None

        event_type = action.get("event")

        if event_type == "NONE":
            logger.info("NOOP for Memory (async).")
            return None

        if event_type not in ("ADD", "UPDATE", "DELETE"):
            logger.error(f"Unknown event_type: {event_type}")
            return None

        # Handle UPDATE and DELETE which require action_id
        if event_type in ("UPDATE", "DELETE"):
            action_id = action.get("id")
            if action_id not in uuid_mapping:
                logger.error(
                    f"ID {action_id} not found in uuid_mapping for "
                    f"{event_type} event: {action}",
                )
                return None
            memory_id = uuid_mapping[action_id]
        else:
            memory_id = None

        try:
            if event_type == "ADD":
                task = asyncio.create_task(
                    self._create_memory(
                        data=action_text,
                        existing_embeddings=embeddings_map,
                        metadata=deepcopy(metadata),
                    ),
                )
            elif event_type == "UPDATE":
                task = asyncio.create_task(
                    self._update_memory(
                        memory_id=memory_id,
                        data=action_text,
                        existing_embeddings=embeddings_map,
                        metadata=deepcopy(metadata),
                    ),
                )
            else:  # DELETE
                task = asyncio.create_task(
                    self._delete_memory(memory_id=memory_id),
                )

            return (task, action, event_type, memory_id)
        except Exception as e:
            error_str = str(e).lower()
            if error_str not in ["not an error", "no error", "success"]:
                logger.error(f"Error processing memory action (async): {e}")
            else:
                logger.debug(
                    f"Non-error exception in memory task (async): {e}",
                )
            return None

    async def _execute_memory_actions(
        self,
        memory_actions: dict,
        uuid_mapping: dict,
        embeddings_map: dict,
        metadata: dict,
    ) -> list:
        """Execute memory actions (ADD/UPDATE/DELETE) based on LLM response."""
        returned_memories = []
        memory_tasks = []

        # Create tasks for each action
        for action in memory_actions.get("memory", []):
            logger.info(action)
            task_info = self._create_memory_task_for_event(
                action,
                uuid_mapping,
                embeddings_map,
                metadata,
            )
            if task_info:
                memory_tasks.append(task_info)

        logger.info(f"Memory tasks: {memory_tasks}")

        # Execute all tasks
        for task, resp, event_type, mem_id in memory_tasks:
            logger.info(
                f"Processing memory task: {task}, {resp}, "
                f"{event_type}, {mem_id}",
            )
            try:
                if task is None:
                    logger.warning(
                        f"Skipping None task for event_type: {event_type}",
                    )
                    continue

                if not hasattr(task, "__await__"):
                    logger.error(f"Task is not awaitable: {type(task)}")
                    continue

                result_id = await task

                if event_type == "ADD":
                    returned_memories.append(
                        {
                            "id": result_id,
                            "memory": resp.get("text"),
                            "event": event_type,
                        },
                    )
                elif event_type == "UPDATE":
                    returned_memories.append(
                        {
                            "id": mem_id,
                            "memory": resp.get("text"),
                            "event": event_type,
                            "previous_memory": resp.get("old_memory"),
                        },
                    )
                elif event_type == "DELETE":
                    returned_memories.append(
                        {
                            "id": mem_id,
                            "memory": resp.get("text"),
                            "event": event_type,
                        },
                    )
            except Exception as e:
                if str(e).lower() not in [
                    "not an error",
                    "no error",
                    "success",
                ]:
                    logger.error(f"Error awaiting memory task (async): {e}")
                else:
                    logger.debug(
                        f"Non-error exception in memory task (async): {e}",
                    )

        return returned_memories

    async def _add_to_vector_store(
        self,
        messages: list,
        metadata: dict,
        effective_filters: dict,
        infer: bool,
        extract_facts: bool = False,
    ):
        """Main method to add messages to vector store with inference
        support."""
        if not infer:
            return await self._add_messages_without_inference(
                messages,
                metadata,
            )

        # Extract facts or use message content
        if extract_facts:
            facts = await self._extract_facts_from_messages(messages)
            if not facts:
                logger.debug(
                    "No new facts retrieved from input. "
                    "Skipping memory update LLM call.",
                )
                return []
            content_list = facts
        else:
            content_list = [msg["content"] for msg in messages]

        # Search for existing memories and get embeddings
        (
            retrieved_memories,
            embeddings_map,
        ) = await self._search_existing_memories(
            content_list,
            effective_filters,
        )

        # Prepare memory data for update
        (
            prepared_memories,
            uuid_mapping,
        ) = await self._prepare_memory_for_update(
            retrieved_memories,
            metadata,
            effective_filters,
        )

        # Generate memory actions from LLM
        memory_actions = await self._generate_memory_actions(
            prepared_memories,
            content_list,
        )

        if not memory_actions:
            logger.info(
                "No new facts retrieved from input (async). "
                "Skipping memory update LLM call.",
            )
            return []

        # Execute memory actions
        returned_memories = await self._execute_memory_actions(
            memory_actions,
            uuid_mapping,
            embeddings_map,
            metadata,
        )

        capture_event(
            "mem0.add",
            self,
            {
                "version": self.api_version,
                "keys": list(effective_filters.keys()),
                "sync_type": "async",
            },
        )
        return returned_memories

    async def _add_to_graph(self, messages, filters):
        # Adapted from mem0.memory.main.AsyncMemory._add_to_graph
        added_entities = []
        if self.enable_graph:
            if filters.get("user_id") is None:
                filters["user_id"] = "user"

            data = "\n".join(
                [
                    msg["content"]
                    for msg in messages
                    if "content" in msg and msg["role"] != "system"
                ],
            )
            added_entities = await asyncio.to_thread(
                self.graph.add,
                data,
                filters,
            )

        return added_entities

    async def get(self, memory_id):
        # Adapted from mem0.memory.main.AsyncMemory.get
        """
        Retrieve a memory by ID asynchronously.

        Args:
            memory_id (str): ID of the memory to retrieve.

        Returns:
            dict: Retrieved memory.
        """
        capture_event(
            "mem0.get",
            self,
            {"memory_id": memory_id, "sync_type": "async"},
        )
        memory = await asyncio.to_thread(
            self.vector_store.get,
            vector_id=memory_id,
        )
        if not memory:
            return None

        promoted_payload_keys = [
            "user_id",
            "agent_id",
            "run_id",
            "actor_id",
            "role",
        ]

        core_and_promoted_keys = {
            "data",
            "hash",
            "created_at",
            "updated_at",
            "id",
            *promoted_payload_keys,
        }

        result_item = MemoryItem(
            id=memory.id,
            memory=memory.payload["data"],
            hash=memory.payload.get("hash"),
            created_at=memory.payload.get("created_at"),
            updated_at=memory.payload.get("updated_at"),
        ).model_dump()

        for key in promoted_payload_keys:
            if key in memory.payload:
                result_item[key] = memory.payload[key]

        additional_metadata = {
            k: v
            for k, v in memory.payload.items()
            if k not in core_and_promoted_keys
        }
        if additional_metadata:
            result_item["metadata"] = additional_metadata

        return result_item

    async def get_all(
        self,
        *,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ):
        # Adapted from mem0.memory.main.AsyncMemory.get_all
        """
        List all memories.

         Args:
             user_id (str, optional): user id
             agent_id (str, optional): agent id
             run_id (str, optional): run id
             filters (dict, optional): Additional custom key-value filters
                 to apply to the search. These are merged with the ID-based
                 scoping filters. For example, `filters={"actor_id":
                 "some_user"}`.
             limit (int, optional): The maximum number of memories to
                 return. Defaults to 100.

         Returns:
             dict: A dictionary containing a list of memories under the
                 "results" key, and potentially "relations" if graph store
                 is enabled. For API v1.0, it might return a direct list
                 (see deprecation warning). Example for v1.1+:
                 `{"results": [{"id": "...", "memory": "...", ...}]}`
        """

        _, effective_filters = build_filters_and_metadata(
            user_id=user_id,
            agent_id=agent_id,
            run_id=run_id,
            input_filters=filters,
        )

        if not any(
            key in effective_filters
            for key in ("user_id", "agent_id", "run_id")
        ):
            raise ValueError(
                "When 'conversation_id' is not provided (classic mode), "
                "at least one of 'user_id', 'agent_id', or 'run_id' must be "
                "specified for get_all.",
            )

        capture_event(
            "mem0.get_all",
            self,
            {
                "limit": limit,
                "keys": list(effective_filters.keys()),
                "sync_type": "async",
            },
        )

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_memories = executor.submit(
                run_async_in_thread,
                self._get_all_from_vector_store,
                effective_filters,
                limit,
            )
            future_graph_entities = (
                executor.submit(self.graph.get_all, effective_filters, limit)
                if self.enable_graph
                else None
            )

            concurrent.futures.wait(
                [future_memories, future_graph_entities]
                if future_graph_entities
                else [future_memories],
            )

            all_memories_result = future_memories.result()
            graph_entities_result = (
                future_graph_entities.result()
                if future_graph_entities
                else None
            )

        if self.enable_graph:
            return {
                "results": all_memories_result,
                "relations": graph_entities_result,
            }

        if self.api_version == "v1.0":
            warnings.warn(
                "The current get_all API output format is deprecated. "
                "To use the latest format, set `api_version='v1.1'` "
                "(which returns a dict with a 'results' key). "
                "The current format (direct list for v1.0) will be removed "
                "in mem0ai 1.1.0 and later versions.",
                category=DeprecationWarning,
                stacklevel=2,
            )
            return all_memories_result
        else:
            return {"results": all_memories_result}

    async def _get_all_from_vector_store(self, filters, limit):
        # Adapted from mem0.memory.main.AsyncMemory._get_all_from_vector_store
        memories_result = await asyncio.to_thread(
            self.vector_store.list,
            filters=filters,
            limit=limit,
        )
        actual_memories = (
            memories_result[0]
            if isinstance(memories_result, (tuple, list))
            and len(memories_result) > 0
            else memories_result
        )

        promoted_payload_keys = [
            "user_id",
            "agent_id",
            "run_id",
            "actor_id",
            "role",
        ]
        core_and_promoted_keys = {
            "data",
            "hash",
            "created_at",
            "updated_at",
            "id",
            *promoted_payload_keys,
        }

        formatted_memories = []
        for mem in actual_memories:
            memory_item_dict = MemoryItem(
                id=mem.id,
                memory=mem.payload["data"],
                hash=mem.payload.get("hash"),
                created_at=mem.payload.get("created_at"),
                updated_at=mem.payload.get("updated_at"),
            ).model_dump(exclude={"score"})

            for key in promoted_payload_keys:
                if key in mem.payload:
                    memory_item_dict[key] = mem.payload[key]

            additional_metadata = {
                k: v
                for k, v in mem.payload.items()
                if k not in core_and_promoted_keys
            }
            if additional_metadata:
                memory_item_dict["metadata"] = additional_metadata

            formatted_memories.append(memory_item_dict)

        return formatted_memories

    async def search(
        self,
        query: str,
        *,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        threshold: Optional[float] = None,
    ):
        # Adapted from mem0.memory.main.AsyncMemory.search
        """
        Searches for memories based on a query
        Args:
            query (str): Query to search for.
            user_id (str, optional): ID of the user to search for.
                Defaults to None.
            agent_id (str, optional): ID of the agent to search for.
                Defaults to None.
            run_id (str, optional): ID of the run to search for.
                Defaults to None.
            limit (int, optional): Limit the number of results.
                Defaults to 10.
            filters (dict, optional): Filters to apply to the search.
                Defaults to None.
            threshold (float, optional): Minimum score for a memory to be
                included in the results. Defaults to None.

        Returns:
            dict: A dictionary containing the search results, typically
                under a "results" key, and potentially "relations" if
                graph store is enabled. Example for v1.1+:
                `{"results": [{"id": "...", "memory": "...", "score": 0.8,
                ...}]}`
        """

        _, effective_filters = build_filters_and_metadata(
            user_id=user_id,
            agent_id=agent_id,
            run_id=run_id,
            input_filters=filters,
        )

        if not any(
            key in effective_filters
            for key in ("user_id", "agent_id", "run_id")
        ):
            raise ValueError(
                "at least one of 'user_id', 'agent_id', or 'run_id' "
                "must be specified ",
            )

        capture_event(
            "mem0.search",
            self,
            {
                "limit": limit,
                "version": self.api_version,
                "keys": list(effective_filters.keys()),
                "sync_type": "sync",
            },
        )

        vector_store_task = asyncio.create_task(
            self._search_vector_store(
                query,
                effective_filters,
                limit,
                threshold,
            ),
        )

        graph_task = None
        if self.enable_graph:
            if hasattr(
                self.graph.search,
                "__await__",
            ):  # Check if graph search is async
                graph_task = asyncio.create_task(
                    self.graph.search(query, effective_filters, limit),
                )
            else:
                graph_task = asyncio.create_task(
                    asyncio.to_thread(
                        self.graph.search,
                        query,
                        effective_filters,
                        limit,
                    ),
                )

        if graph_task:
            original_memories, graph_entities = await asyncio.gather(
                vector_store_task,
                graph_task,
            )
        else:
            original_memories = await vector_store_task
            graph_entities = None

        if self.enable_graph:
            return {"results": original_memories, "relations": graph_entities}

        if self.api_version == "v1.0":
            warnings.warn(
                "The current search API output format is deprecated. "
                "To use the latest format, set `api_version='v1.1'`. "
                "The current format will be removed in mem0ai 1.1.0 "
                "and later versions.",
                category=DeprecationWarning,
                stacklevel=2,
            )
            return {"results": original_memories}
        else:
            return {"results": original_memories}

    async def _search_vector_store(
        self,
        query,
        filters,
        limit,
        threshold: Optional[float] = None,
    ):
        # Adapted from mem0.memory.main.AsyncMemory._search_vector_store
        embeddings = await asyncio.to_thread(
            self.embedding_model.embed,
            query,
            "search",
        )
        memories = await asyncio.to_thread(
            self.vector_store.search,
            query=query,
            vectors=embeddings,
            limit=limit,
            filters=filters,
        )

        promoted_payload_keys = [
            "user_id",
            "agent_id",
            "run_id",
            "actor_id",
            "role",
        ]

        core_and_promoted_keys = {
            "data",
            "hash",
            "created_at",
            "updated_at",
            "id",
            *promoted_payload_keys,
        }

        original_memories = []
        for mem in memories:
            memory_item_dict = MemoryItem(
                id=mem.id,
                memory=mem.payload["data"],
                hash=mem.payload.get("hash"),
                created_at=mem.payload.get("created_at"),
                updated_at=mem.payload.get("updated_at"),
                score=mem.score,
            ).model_dump()

            for key in promoted_payload_keys:
                if key in mem.payload:
                    memory_item_dict[key] = mem.payload[key]

            additional_metadata = {
                k: v
                for k, v in mem.payload.items()
                if k not in core_and_promoted_keys
            }
            if additional_metadata:
                memory_item_dict["metadata"] = additional_metadata

            if threshold is None or mem.score >= threshold:
                original_memories.append(memory_item_dict)

        return original_memories

    async def update(self, memory_id, data, metadata=None):
        # Adapted from mem0.memory.main.AsyncMemory.update
        """
        Update a memory by ID asynchronously.

        Args:
            memory_id (str): ID of the memory to update.
            data (str): Data to update the memory with.
            metadata (dict, optional): Metadata to update the memory with.

        Returns:
            dict: Updated memory.
        """
        capture_event(
            "mem0.update",
            self,
            {"memory_id": memory_id, "sync_type": "async"},
        )

        embeddings = await asyncio.to_thread(
            self.embedding_model.embed,
            data,
            "update",
        )
        existing_embeddings = {data: embeddings}

        await self._update_memory(
            memory_id,
            data,
            existing_embeddings,
            metadata,
        )
        return {"message": "Memory updated successfully!"}

    async def delete(self, memory_id):
        # Adapted from mem0.memory.main.AsyncMemory.delete
        """
        Delete a memory by ID asynchronously.

        Args:
            memory_id (str): ID of the memory to delete.
        """
        capture_event(
            "mem0.delete",
            self,
            {"memory_id": memory_id, "sync_type": "async"},
        )
        await self._delete_memory(memory_id)
        return {"message": "Memory deleted successfully!"}

    async def delete_all(self, user_id=None, agent_id=None, run_id=None):
        # Adapted from mem0.memory.main.AsyncMemory.delete_all
        """
        Delete all memories asynchronously.

        Args:
            user_id (str, optional): ID of the user to delete memories for.
                Defaults to None.
            agent_id (str, optional): ID of the agent to delete memories for.
                Defaults to None.
            run_id (str, optional): ID of the run to delete memories for.
                Defaults to None.
        """
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        if agent_id:
            filters["agent_id"] = agent_id
        if run_id:
            filters["run_id"] = run_id

        if not filters:
            raise ValueError(
                "At least one filter is required to delete all memories. "
                "If you want to delete all memories, use the `reset()` "
                "method.",
            )

        capture_event(
            "mem0.delete_all",
            self,
            {"keys": list(filters.keys()), "sync_type": "sync"},
        )
        memories = await asyncio.to_thread(
            self.vector_store.list,
            filters=filters,
        )

        delete_tasks = []
        for memory in memories[0]:
            delete_tasks.append(self._delete_memory(memory.id))

        await asyncio.gather(*delete_tasks)

        logger.info(f"Deleted {len(memories[0])} memories")

        if self.enable_graph:
            await asyncio.to_thread(self.graph.delete_all, filters)

        return {"message": "Memories deleted successfully!"}

    async def history(self, memory_id):
        # Adapted from mem0.memory.main.AsyncMemory.history
        """
        Get the history of changes for a memory by ID asynchronously.

        Args:
            memory_id (str): ID of the memory to get history for.

        Returns:
            list: List of changes for the memory.
        """
        capture_event(
            "mem0.history",
            self,
            {"memory_id": memory_id, "sync_type": "async"},
        )
        return await asyncio.to_thread(self.db.get_history, memory_id)

    async def _create_memory(self, data, existing_embeddings, metadata=None):
        # Adapted from mem0.memory.main.AsyncMemory._create_memory
        logger.debug(f"Creating memory with {data=}")
        if data in existing_embeddings:
            embeddings = existing_embeddings[data]
        else:
            embeddings = await asyncio.to_thread(
                self.embedding_model.embed,
                data,
                memory_action="add",
            )

        memory_id = (
            metadata["memory_id"]
            if "memory_id" in metadata
            else str(uuid.uuid4())
        )
        metadata = metadata or {}
        metadata["data"] = data
        metadata["hash"] = hashlib.md5(data.encode()).hexdigest()
        metadata["created_at"] = datetime.now(
            pytz.timezone("US/Pacific"),
        ).isoformat()

        if "memory_id" in metadata:
            del metadata["memory_id"]

        await asyncio.to_thread(
            self.vector_store.insert,
            vectors=[embeddings],
            ids=[memory_id],
            payloads=[metadata],
        )

        await asyncio.to_thread(
            self.db.add_history,
            memory_id,
            None,
            data,
            "ADD",
            created_at=metadata.get("created_at"),
            actor_id=metadata.get("actor_id"),
            role=metadata.get("role"),
        )

        capture_event(
            "mem0._create_memory",
            self,
            {"memory_id": memory_id, "sync_type": "async"},
        )
        return memory_id

    async def _create_procedural_memory(
        self,
        messages,
        metadata=None,
        llm=None,
        prompt=None,
    ):
        # Adapted from mem0.memory.main.AsyncMemory._create_procedural_memory
        """
        Create a procedural memory asynchronously

        Args:
            messages (list): List of messages to create a procedural memory
                from.
            metadata (dict): Metadata to create a procedural memory from.
            llm (llm, optional): LLM to use for the procedural memory
                creation. Defaults to None.
            prompt (str, optional): Prompt to use for the procedural memory
                creation. Defaults to None.
        """
        try:
            from langchain_core.messages.utils import (
                convert_to_messages,  # type: ignore
            )
        except Exception:
            logger.error(
                "Import error while loading langchain-core. "
                "Please install 'langchain-core' to use procedural memory.",
            )
            raise

        logger.info("Creating procedural memory")

        parsed_messages = [
            {
                "role": "system",
                "content": prompt or PROCEDURAL_MEMORY_SYSTEM_PROMPT,
            },
            *messages,
            {
                "role": "user",
                "content": (
                    "Create procedural memory of the above conversation."
                ),
            },
        ]

        try:
            if llm is not None:
                parsed_messages = convert_to_messages(parsed_messages)
                response = await asyncio.to_thread(
                    llm.invoke,
                    input=parsed_messages,
                )
                procedural_memory = response.content
            else:
                procedural_memory = await asyncio.to_thread(
                    self.llm.generate_response,
                    messages=parsed_messages,
                )
        except Exception as e:
            logger.error(f"Error generating procedural memory summary: {e}")
            raise

        if metadata is None:
            raise ValueError("Metadata cannot be done for procedural memory.")

        metadata["memory_type"] = MemoryType.PROCEDURAL.value
        embeddings = await asyncio.to_thread(
            self.embedding_model.embed,
            procedural_memory,
            memory_action="add",
        )
        memory_id = await self._create_memory(
            procedural_memory,
            {procedural_memory: embeddings},
            metadata=metadata,
        )
        capture_event(
            "mem0._create_procedural_memory",
            self,
            {"memory_id": memory_id, "sync_type": "async"},
        )

        result = {
            "results": [
                {"id": memory_id, "memory": procedural_memory, "event": "ADD"},
            ],
        }

        return result

    async def _update_memory(
        self,
        memory_id,
        data,
        existing_embeddings,
        metadata=None,
    ):
        # Adapted from mem0.memory.main.AsyncMemory._update_memory
        logger.info(f"Updating memory with {data=}")

        try:
            existing_memory = await asyncio.to_thread(
                self.vector_store.get,
                vector_id=memory_id,
            )
        except Exception as exc:
            logger.error(
                f"Error getting memory with ID {memory_id} during update.",
            )
            raise ValueError(
                f"Error getting memory with ID {memory_id}. "
                "Please provide a valid 'memory_id'",
            ) from exc

        prev_value = existing_memory.payload.get("data")

        new_metadata = deepcopy(metadata) if metadata is not None else {}

        new_metadata["data"] = data
        new_metadata["hash"] = hashlib.md5(data.encode()).hexdigest()
        new_metadata["created_at"] = existing_memory.payload.get("created_at")
        new_metadata["updated_at"] = datetime.now(
            pytz.timezone("US/Pacific"),
        ).isoformat()

        # Set session_id
        new_metadata["session_id"] = (
            metadata.get("session_id", str(uuid.uuid4()))
            if metadata
            else str(uuid.uuid4())
        )

        if "memory_id" in new_metadata:
            del new_metadata["memory_id"]

        # Copy promoted keys from existing memory
        promoted_keys = ["user_id", "agent_id", "run_id", "actor_id", "role"]
        for key in promoted_keys:
            if key in existing_memory.payload:
                new_metadata[key] = existing_memory.payload[key]

        # Copy remaining metadata from existing memory
        for k, v in existing_memory.payload.items():
            if k not in new_metadata:
                new_metadata[k] = v

        if data in existing_embeddings:
            embeddings = existing_embeddings[data]
        else:
            embeddings = await asyncio.to_thread(
                self.embedding_model.embed,
                data,
                "update",
            )

        await asyncio.to_thread(
            self.vector_store.update,
            vector_id=memory_id,
            vector=embeddings,
            payload=new_metadata,
        )
        logger.info(f"Updating memory with ID {memory_id=} with {data=}")

        await asyncio.to_thread(
            self.db.add_history,
            memory_id,
            prev_value,
            data,
            "UPDATE",
            created_at=new_metadata["created_at"],
            updated_at=new_metadata["updated_at"],
            actor_id=new_metadata.get("actor_id"),
            role=new_metadata.get("role"),
        )
        capture_event(
            "mem0._update_memory",
            self,
            {"memory_id": memory_id, "sync_type": "async"},
        )
        return memory_id

    async def _delete_memory(self, memory_id):
        # Adapted from mem0.memory.main.AsyncMemory._delete_memory
        logger.info(f"Deleting memory with {memory_id=}")
        existing_memory = await asyncio.to_thread(
            self.vector_store.get,
            vector_id=memory_id,
        )
        prev_value = existing_memory.payload["data"]

        await asyncio.to_thread(self.vector_store.delete, vector_id=memory_id)
        await asyncio.to_thread(
            self.db.add_history,
            memory_id,
            prev_value,
            None,
            "DELETE",
            actor_id=existing_memory.payload.get("actor_id"),
            role=existing_memory.payload.get("role"),
            is_deleted=1,
        )

        capture_event(
            "mem0._delete_memory",
            self,
            {"memory_id": memory_id, "sync_type": "async"},
        )
        return memory_id

    async def reset(self):
        # Adapted from mem0.memory.main.AsyncMemory.reset
        """
        Reset the memory store asynchronously by:
            Deletes the vector store collection
            Resets the database
            Recreates the vector store with a new client
        """
        logger.warning("Resetting all memories")
        await asyncio.to_thread(self.vector_store.delete_col)

        gc.collect()

        if hasattr(self.vector_store, "client") and hasattr(
            self.vector_store.client,
            "close",
        ):
            await asyncio.to_thread(self.vector_store.client.close)

        # Use the new async reset method
        await asyncio.to_thread(self.db.reset)

        self.vector_store = VectorStoreFactory.create(
            self.config.vector_store.provider,
            self.config.vector_store.config,
        )
        capture_event("mem0.reset", self, {"sync_type": "async"})

    async def get_memory_type(
        self,
        content: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Get the memory type of the given content with improved performance
        and accuracy.
        Args:
            content: The content to get the memory type for.
            context: Optional context information for better classification.
        Returns:
            str: The memory type of the content.
        """
        try:
            memory_content = self._preprocess_content(content)
            rule_based_type = self._rule_based_classification(
                memory_content,
                context,
            )
            if rule_based_type:
                return rule_based_type

            llm_type = await self._llm_classification(memory_content, context)
            final_type = self._post_process_classification(llm_type)
            return final_type

        except Exception as e:
            logger.warning(f"Error in get_memory_type: {e}")
            return "Core Memory"

    def _preprocess_content(self, content: Any) -> str:
        """Format the content to be preprocessed"""
        try:
            if isinstance(content, str):
                return content.strip()

            if isinstance(content, dict):
                return self._preprocess_dict_content(content)

            if isinstance(content, list):
                return self._preprocess_list_content(content)

            return str(content).strip()
        except Exception as e:
            logger.warning(f"Error in content preprocessing: {e}")
            return str(content)

    def _preprocess_dict_content(self, content: dict) -> str:
        """Preprocess dictionary content"""
        if "content" in content:
            return str(content["content"]).strip()

        key_fields = ["message", "text", "data", "description"]
        for field in key_fields:
            if field in content:
                return str(content[field]).strip()

        return json.dumps(content, indent=2, ensure_ascii=False)

    def _preprocess_list_content(self, content: list) -> str:
        """Preprocess list content"""
        if not content:
            return ""

        if not isinstance(content[0], dict):
            return json.dumps(content, indent=2, ensure_ascii=False)

        messages = []
        for item in content:
            if isinstance(item, dict):
                if "content" in item:
                    messages.append(str(item["content"]))
                elif "message" in item:
                    messages.append(str(item["message"]))

        return (
            "\n".join(messages)
            if messages
            else json.dumps(
                content,
                indent=2,
                ensure_ascii=False,
            )
        )

    def _rule_based_classification(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        if not content:
            return "Core Memory"

        # Check context-based classification first
        context_type = self._classify_from_context(context)
        if context_type:
            return context_type

        content_lower = content.lower()

        # Keyword-based classification
        keyword_mappings = {
            "Procedural Memory": [
                "step",
                "procedure",
                "process",
                "instruction",
                "guide",
                "tutorial",
                "how to",
                "method",
                "algorithm",
                "workflow",
                "protocol",
            ],
            "Resource Memory": [
                "file",
                "document",
                "resource",
                "attachment",
                "upload",
                "download",
                "pdf",
                "doc",
                "image",
                "video",
                "audio",
            ],
            "Knowledge Vault": [
                "contact",
                "email",
                "phone",
                "address",
                "credential",
                "password",
                "api key",
                "token",
                "configuration",
                "setting",
            ],
            "Semantic Memory": [
                "concept",
                "definition",
                "explanation",
                "theory",
                "principle",
                "understanding",
                "knowledge about",
                "information about",
            ],
        }

        for memory_type, keywords in keyword_mappings.items():
            if any(keyword in content_lower for keyword in keywords):
                return memory_type

        return None

    def _classify_from_context(
        self,
        context: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """Classify memory type based on context action_type"""
        if not context:
            return None

        action_type = context.get("action_type", "").upper()
        action_type_map = {
            "PROCEDURAL": "Procedural Memory",
            "SESSION": "Episodic Memory",
            "TOOL": "Procedural Memory",
            "EDIT": "Semantic Memory",
            "CHAT": "Episodic Memory",
        }

        return action_type_map.get(action_type)

    async def _llm_classification(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        try:
            user_prompt = (
                f"Please determine the type of memory for the following "
                f"content:\n{content}"
            )

            if context:
                context_info = json.dumps(context, indent=2)
                user_prompt += f"\n\nContext information:\n{context_info}"

            memory_type_response = await asyncio.to_thread(
                self.llm.generate_response,
                messages=[
                    {"role": "system", "content": GET_MEMORY_TYPE},
                    {"role": "user", "content": user_prompt},
                ],
            )

            return memory_type_response.strip()
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return "Core Memory"

    def _post_process_classification(self, llm_type: str) -> str:
        valid_types = [
            "Core Memory",
            "Episodic Memory",
            "Procedural Memory",
            "Resource Memory",
            "Knowledge Vault",
            "Semantic Memory",
        ]

        cleaned_type = llm_type.strip()

        if cleaned_type not in valid_types:
            for valid_type in valid_types:
                if valid_type.lower() in cleaned_type.lower():
                    return valid_type

        if cleaned_type not in valid_types:
            logger.warning(
                f"Invalid memory type from LLM: {cleaned_type}, using default",
            )
            return "Core Memory"

        return cleaned_type
