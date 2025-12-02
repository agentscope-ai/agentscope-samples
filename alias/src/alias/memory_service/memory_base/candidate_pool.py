# -*- coding: utf-8 -*-
import asyncio
import hashlib
import json
import math
import uuid
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytz

from mem0.memory.setup import setup_config
from mem0.memory.telemetry import capture_event
from mem0.memory.utils import remove_code_blocks

from alias.memory_service.profiling_utils.memory_utils import (
    extract_json_from_text,
)
from alias.memory_service.profiling_utils.logging_utils import setup_logging
from alias.memory_service.memory_base.prompt import (
    AGENT_KEY_WORKFLOW_PROMPT,
    AGENT_ROADMAP_PROMPT,
    EXTRACT_BREAK_CHAT_PREFERENCE,
    EXTRACT_EDIT_FILE_PREFERENCE,
    EXTRACT_EDIT_PREFERENCE,
    EXTRACT_FOLLOWUP_CHAT_PREFERENCE,
    EXTRACT_LIKE_MESSAGE,
    EXTRACT_START_CHAT_PREFERENCE,
    EXTRACT_UNLIKE_MESSAGE,
    EXTRACT_WORKFLOWS_PROMPT,
    SESSION_SUMMARY_PROMPT,
    SESSION_SUMMARY_USER_PROMPT,
    SUBTASK_KEY_WORKFLOW_PROMPT,
    SUBTASK_ROADMAP_PROMPT,
)

from .base_vec_memory import BaseAsyncVectorMemory

logger = setup_logging()

setup_config()


class AsyncVectorCandidateMemory(BaseAsyncVectorMemory):
    async def _on_existing_memory_retrieved(
        self,
        memory_ids: List[str],
        metadata: Dict[str, Any],
        filters: Dict[str, Any],
    ) -> None:
        await super()._on_existing_memory_retrieved(
            memory_ids,
            metadata,
            filters,
        )
        if not memory_ids:
            return
        try:
            await self._update_metadata(memory_ids)
        except Exception as exc:
            logger.error(
                f"Failed to update metadata for existing memories: {exc}",
            )

    async def _search_vector_store(
        self,
        query: str,
        filters: Dict[str, Any],
        limit: int,
        threshold: Optional[float] = None,
    ):
        results = await super()._search_vector_store(
            query,
            filters,
            limit,
            threshold,
        )
        memory_ids = [item["id"] for item in results if "id" in item]
        if memory_ids:
            try:
                await self._update_metadata(memory_ids)
            except Exception as exc:
                logger.error(f"Failed to update metadata after search: {exc}")
        return results

    async def reset_metadata(self, memory_id):
        capture_event(
            "mem0.reset_metadata",
            self,
            {"memory_id": memory_id, "sync_type": "async"},
        )
        if memory_id is not None:
            await self._update_metadata(memory_id, visited_count_reset=True)
        return {"message": "Metadata reset successfully!"}

    async def get_highest_score_memory(self, candidates):
        if not candidates:
            return None, None

        now_ts = datetime.now(pytz.timezone("US/Pacific")).timestamp()
        highest_score = 0.0
        highest_score_memory = None

        for candidate in candidates:
            total_score = await self.compute_score(
                visited_count=candidate["metadata"].get("visited_count", 1),
                last_access_time=candidate["metadata"].get("last_access_time"),
                now_ts=now_ts,
            )

            if total_score > highest_score:
                highest_score = total_score
                highest_score_memory = candidate

            logger.info(
                f"Updated score for memory {candidate['id']}, {total_score}",
            )

        capture_event(
            "mem0.get_highest_score_memory",
            self,
            {"sync_type": "async"},
        )
        return highest_score_memory, highest_score

    async def get_highest_score_memory_by_threshold(self, candidates):
        if not candidates:
            return None, None

        now_ts = datetime.now(pytz.timezone("US/Pacific")).timestamp()
        highest_score = 0.0
        highest_score_memory = None

        threshold = 0.95 * (1.0 - (1 / len(candidates)))

        for candidate in candidates:
            total_score = await self.compute_score(
                visited_count=candidate["metadata"].get("visited_count", 1),
                last_access_time=candidate["metadata"].get("last_access_time"),
                now_ts=now_ts,
            )

            if total_score >= threshold and total_score > highest_score:
                highest_score = total_score
                highest_score_memory = candidate

            logger.info(
                f"Updated score for memory {candidate['id']}, {total_score}",
            )

        capture_event(
            "mem0.get_highest_score_memory",
            self,
            {"sync_type": "async"},
        )
        return highest_score_memory, highest_score

    async def compute_score(
        self,
        visited_count,
        last_access_time,
        now_ts,
        max_time_diff: float = 1.0,
        temperature: float = 1e-3,
    ):
        try:
            last_access_time = datetime.fromisoformat(
                last_access_time,
            ).timestamp()
        except Exception:
            logger.warning(
                f"Invalid format of last_access_time: {last_access_time}",
            )
            last_access_time = 0

        time_diff_hours = (now_ts - last_access_time) / 3600
        time_score = math.exp(-temperature * time_diff_hours)
        normalized_time = time_score / max_time_diff

        normalized_visit = 1 / (1 + math.exp(-visited_count / 10))

        score = round(0.7 * normalized_time + 0.3 * normalized_visit, 3)

        return score

    def _prepare_update_metadata(
        self,
        existing_memory,
        visited_count: int,
        last_access_time,
        visited_count_reset: bool,
        update_score_only: bool,
        now: str,
        memory_ids_count: int,
    ) -> Dict[str, Any]:
        """
        Prepare metadata for memory update.

        Args:
            existing_memory: The existing memory object.
            visited_count: Current visited count.
            last_access_time: Last access time.
            visited_count_reset: Whether to reset visited count.
            update_score_only: Whether to update score only.
            now: Current timestamp as ISO string.
            memory_ids_count: Number of memory IDs being updated.

        Returns:
            Dictionary with prepared metadata.
        """
        memory_data = existing_memory.payload["data"]
        memory_hash = existing_memory.payload.get("hash")
        created_at = existing_memory.payload.get("created_at")
        updated_at = existing_memory.payload.get("updated_at")
        session_id = existing_memory.payload.get("session_id")

        metadata = {
            "data": memory_data,
            "hash": memory_hash,
            "created_at": created_at,
            "updated_at": updated_at,
            "session_id": session_id,
        }

        if update_score_only:
            if memory_ids_count > 1:
                raise ValueError(
                    "update_score_only cannot be True when updating "
                    "multiple memories",
                )
            metadata["visited_count"] = visited_count
            metadata["last_access_time"] = last_access_time
        elif visited_count_reset:
            metadata["visited_count"] = 1
            metadata["last_access_time"] = last_access_time
        else:
            metadata["visited_count"] = visited_count + 1
            metadata["last_access_time"] = now

        for key in ("user_id", "agent_id", "run_id", "actor_id", "role"):
            if key in existing_memory.payload:
                metadata[key] = existing_memory.payload[key]

        for key, value in existing_memory.payload.items():
            if key not in metadata:
                metadata[key] = value

        return metadata

    async def _update_metadata(
        self,
        memory_ids,
        visited_count_reset: bool = False,
        update_score_only: bool = False,
        updated_score: Optional[float] = None,
    ):
        logger.info("Updating old memories with NEW metadata")

        if isinstance(memory_ids, str):
            memory_ids = [memory_ids]
        elif not isinstance(memory_ids, list):
            raise ValueError("memories should be a str or a list")

        now = datetime.now(pytz.timezone("US/Pacific")).isoformat()
        now_ts = datetime.fromisoformat(now).timestamp()

        for memory_id in memory_ids:
            try:
                existing_memory = await asyncio.to_thread(
                    self.vector_store.get,
                    vector_id=memory_id,
                )
            except Exception as exc:
                logger.error(
                    f"Error getting memory with ID {memory_id} during "
                    f"metadata update.",
                )
                raise ValueError(
                    f"Error getting memory with ID {memory_id}. "
                    f"Please check the validity of the 'memory_id'",
                ) from exc

            visited_count = existing_memory.payload.get("visited_count") or 0
            last_access_time = existing_memory.payload.get("last_access_time")

            if update_score_only and updated_score is None:
                logger.warning("No SCORE provided, computing score")
                updated_score = await self.compute_score(
                    visited_count=visited_count,
                    last_access_time=last_access_time,
                    now_ts=now_ts,
                )

            metadata = self._prepare_update_metadata(
                existing_memory,
                visited_count,
                last_access_time,
                visited_count_reset,
                update_score_only,
                now,
                len(memory_ids),
            )

            memory_data = existing_memory.payload["data"]
            embeddings = (
                await asyncio.to_thread(
                    self.embedding_model.embed,
                    memory_data,
                    "update metadata",
                )
                if existing_memory.vector is None
                else existing_memory.vector
            )

            await asyncio.to_thread(
                self.vector_store.update,
                vector_id=memory_id,
                vector=embeddings,
                payload=metadata,
            )
            logger.info(
                f"Updating memory with ID {memory_id=} with new metadata",
            )

        return memory_ids

    async def _update_memory(
        self,
        memory_id,
        data,
        existing_embeddings,
        metadata=None,
    ):
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
                f"Please provide a valid 'memory_id'",
            ) from exc

        now = datetime.now(pytz.timezone("US/Pacific")).isoformat()
        prev_value = existing_memory.payload.get("data")

        new_metadata = deepcopy(metadata) if metadata is not None else {}

        new_metadata["data"] = data
        new_metadata["hash"] = hashlib.md5(data.encode()).hexdigest()
        new_metadata["created_at"] = existing_memory.payload.get("created_at")
        new_metadata["updated_at"] = now
        new_metadata["visited_count"] = (
            existing_memory.payload.get("visited_count") or 0
        ) + 1
        new_metadata["last_access_time"] = now
        if metadata is None:
            new_metadata["session_id"] = str(uuid.uuid4())
        else:
            new_metadata["session_id"] = metadata.get(
                "session_id",
                str(uuid.uuid4()),
            )

        if "memory_id" in new_metadata:
            del new_metadata["memory_id"]

        for key in ("user_id", "agent_id", "run_id", "actor_id", "role"):
            if key in existing_memory.payload:
                new_metadata[key] = existing_memory.payload[key]

        for key, value in existing_memory.payload.items():
            if key not in new_metadata:
                new_metadata[key] = value

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

    async def chat(self, query):
        raise NotImplementedError("Chat function not implemented yet.")

    async def one_step_extract_CollectionSession(self, session_content):
        try:
            contents = []
            for msg in session_content:
                contents.append(
                    f"{msg.get('role', '')}: {msg.get('content', '')}",
                )
            contents = "\n".join(contents)
            session_summary_response = await asyncio.to_thread(
                self.llm.generate_response,
                messages=[
                    {"role": "system", "content": SESSION_SUMMARY_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Session content: {contents}\n"
                            f"+{SESSION_SUMMARY_USER_PROMPT}"
                        ),
                    },
                ],
                response_format={
                    "type": (
                        "json_object"
                        if "qwen-max" not in self.config.llm.config["model"]
                        else "text"
                    ),
                },
            )

            try:
                session_summary = json.loads(
                    remove_code_blocks(session_summary_response),
                )
                logger.info(
                    f"session_summary_response: \n{session_summary_response}",
                )
            except Exception as exc:
                try:
                    session_summary = extract_json_from_text(
                        session_summary_response,
                    )
                    if not isinstance(session_summary, dict):
                        logger.error(
                            f"Error in extracting session summary: {exc}",
                        )
                        session_summary = {
                            "task": "Unknown Task Type",
                            "problem_category": "Unknown Task Type",
                        }
                except Exception as exc_inner:
                    logger.error(
                        f"Error in extracting session summary: {exc_inner}",
                    )
                    session_summary = {
                        "task": "Unknown Task Type",
                        "problem_category": "Unknown Task Type",
                    }

            full_workflows_response = await asyncio.to_thread(
                self.llm.generate_response,
                messages=[
                    {"role": "system", "content": EXTRACT_WORKFLOWS_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Task type: "
                            f"{session_summary.get('problem_category', '')}\n"
                            f"Task description: "
                            f"{session_summary.get('task', '')}\n"
                            f"Session content: {contents}"
                        ),
                    },
                ],
                response_format={
                    "type": (
                        "json_object"
                        if "qwen-max" not in self.config.llm.config["model"]
                        else "text"
                    ),
                },
            )

            try:
                logger.info(
                    f"Full workflows response: \n{full_workflows_response}",
                )
                full_workflows = json.loads(
                    remove_code_blocks(full_workflows_response),
                )
            except Exception as exc:
                try:
                    full_workflows = extract_json_from_text(
                        full_workflows_response,
                    )
                    if (
                        not isinstance(full_workflows, dict)
                        or "workflows" not in full_workflows
                    ):
                        logger.error(
                            f"Error in extracting key workflows: {exc}",
                        )
                        full_workflows = {"workflows": []}
                except Exception as exc_inner:
                    logger.error(
                        f"Error in extracting key workflows: {exc_inner}",
                    )
                    full_workflows = {"workflows": []}

            final_result = {
                "task_type": session_summary.get("problem_category", ""),
                "task_description": session_summary.get("task", ""),
                "workflows": full_workflows.get("workflows", []),
            }
            return [final_result]

        except Exception as exc:
            logger.error(f"Error in one_step_extract_CollectionSession: {exc}")
            raise

    def _parse_json_with_fallback(
        self,
        response: str,
        default_value: Dict[str, Any],
        error_context: str,
    ) -> Dict[str, Any]:
        """
        Parse JSON from response with fallback extraction.

        Args:
            response: The response string to parse.
            default_value: Default value if parsing fails.
            error_context: Context for error logging.

        Returns:
            Parsed dictionary or default value.
        """
        try:
            return json.loads(remove_code_blocks(response))
        except Exception as exc:
            try:
                parsed = extract_json_from_text(response)
                if not isinstance(parsed, dict):
                    logger.error(f"Error in {error_context}: {exc}")
                    return default_value
                return parsed
            except Exception as exc_inner:
                logger.error(f"Error in {error_context}: {exc_inner}")
                return default_value

    async def _extract_session_summary(
        self,
        contents: str,
    ) -> Dict[str, Any]:
        """
        Extract session summary from contents.

        Args:
            contents: Formatted session contents.

        Returns:
            Dictionary with session summary.
        """
        session_summary_response = await asyncio.to_thread(
            self.llm.generate_response,
            messages=[
                {"role": "system", "content": SESSION_SUMMARY_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Session content: {contents}\n"
                        f"+{SESSION_SUMMARY_USER_PROMPT}"
                    ),
                },
            ],
            response_format={
                "type": (
                    "json_object"
                    if "qwen-max" not in self.config.llm.config["model"]
                    else "text"
                ),
            },
        )

        default_summary = {
            "task": "Unknown Task Type",
            "problem_category": "Unknown Task Type",
        }
        return self._parse_json_with_fallback(
            session_summary_response,
            default_summary,
            "extracting session summary",
        )

    async def _extract_agent_roadmap(
        self,
        session_summary: Dict[str, Any],
        contents: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Extract agent roadmap and key path.

        Args:
            session_summary: The session summary dictionary.
            contents: Formatted session contents.

        Returns:
            Dictionary with agent key path or None.
        """
        problem_category_val = session_summary.get("problem_category", "")
        task_desc = session_summary.get("task", "")

        agent_roadmap_response = await asyncio.to_thread(
            self.llm.generate_response,
            messages=[
                {"role": "system", "content": AGENT_ROADMAP_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Task type: {problem_category_val}\n"
                        f" Task description: {task_desc}\n"
                        f" Session content: {contents}"
                    ),
                },
            ],
            response_format={
                "type": (
                    "json_object"
                    if "qwen-max" not in self.config.llm.config["model"]
                    else "text"
                ),
            },
        )

        default_roadmap = {"roadmap": []}
        agent_roadmap = self._parse_json_with_fallback(
            agent_roadmap_response,
            default_roadmap,
            "extracting agent roadmap",
        )

        def agent_roadmap_to_text(roadmap_json):
            lines = []
            roadmap_list = roadmap_json.get("roadmap", [])
            for item in roadmap_list:
                agent_name = item.get("name", "")
                seq = item.get("seq", "")
                subtask = item.get("subtask", "")
                implement = item.get("implement", "")
                status = item.get("status", "")
                handover = item.get("handover_to", "")
                lines.append(
                    f"Step {seq} - Agent: {agent_name}\n"
                    f"- Subtask: {subtask}\n"
                    f"- Implementation: {implement}\n"
                    f"- Status: {status}\n"
                    f"- Handover: {handover}\n",
                )
            return "\n".join(lines)

        agent_roadmap_text = agent_roadmap_to_text(agent_roadmap)

        agent_key_path_response = await asyncio.to_thread(
            self.llm.generate_response,
            messages=[
                {
                    "role": "system",
                    "content": AGENT_KEY_WORKFLOW_PROMPT,
                },
                {
                    "role": "user",
                    "content": f"Agent roadmap:\n{agent_roadmap_text}",
                },
            ],
            response_format={
                "type": (
                    "json_object"
                    if "qwen-max" not in self.config.llm.config["model"]
                    else "text"
                ),
            },
        )

        default_key_path = {"workflows": []}
        agent_key_path = self._parse_json_with_fallback(
            agent_key_path_response,
            default_key_path,
            "extracting agent key path",
        )

        return agent_key_path

    async def _extract_subtask_roadmap(
        self,
        session_summary: Dict[str, Any],
        contents: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Extract subtask roadmap and key path.

        Args:
            session_summary: The session summary dictionary.
            contents: Formatted session contents.

        Returns:
            Dictionary with subtask key path or None.
        """
        problem_category_val = session_summary.get("problem_category", "")
        task_desc = session_summary.get("task", "")

        subtask_roadmap_response = await asyncio.to_thread(
            self.llm.generate_response,
            messages=[
                {"role": "system", "content": SUBTASK_ROADMAP_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Task type: {problem_category_val}\n"
                        f"Task description: {task_desc}\n"
                        f"Session content: {contents}"
                    ),
                },
            ],
            response_format={
                "type": (
                    "json_object"
                    if "qwen-max" not in self.config.llm.config["model"]
                    else "text"
                ),
            },
        )

        default_roadmap = {"roadmap": []}
        subtask_roadmap = self._parse_json_with_fallback(
            subtask_roadmap_response,
            default_roadmap,
            "extracting subtask roadmap",
        )

        def subtask_roadmap_to_text(roadmap_json):
            lines = []
            roadmap_list = roadmap_json.get("roadmap", [])
            problem_category = session_summary.get("problem_category", "")
            task = session_summary.get("task", "")
            lines.append(
                f"Task type: {problem_category}\n"
                f"Task description: {task}\nRoadmap:\n",
            )
            for item in roadmap_list:
                seq = item.get("seq", "")
                subtask = item.get("subtask", "")
                implement = item.get("implement", "")
                lines.append(
                    f"Step {seq}- Subtask: {subtask}\n"
                    f"- Implementation: {implement}\n",
                )
            return "\n".join(lines)

        subtask_roadmap_text = subtask_roadmap_to_text(subtask_roadmap)

        subtask_key_path_response = await asyncio.to_thread(
            self.llm.generate_response,
            messages=[
                {
                    "role": "system",
                    "content": SUBTASK_KEY_WORKFLOW_PROMPT,
                },
                {
                    "role": "user",
                    "content": (f"Subtask roadmap:\n{subtask_roadmap_text}"),
                },
            ],
            response_format={
                "type": (
                    "json_object"
                    if "qwen-max" not in self.config.llm.config["model"]
                    else "text"
                ),
            },
        )

        default_key_path = {"workflows": []}
        subtask_key_path = self._parse_json_with_fallback(
            subtask_key_path_response,
            default_key_path,
            "extracting subtask key path",
        )

        return subtask_key_path

    def _build_final_result(
        self,
        abstract_type: str,
        session_summary: Dict[str, Any],
        agent_key_path: Optional[Dict[str, Any]],
        subtask_key_path: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Build final result based on abstract type.

        Args:
            abstract_type: Type of abstraction.
            session_summary: The session summary dictionary.
            agent_key_path: Agent key path dictionary.
            subtask_key_path: Subtask key path dictionary.

        Returns:
            List of final result dictionaries.
        """
        task_type = session_summary.get("problem_category", "")
        task_description = session_summary.get("task", "")

        if abstract_type == "multi_levels":
            return [
                {
                    "task_type": task_type,
                    "task_description": task_description,
                    "workflows": (
                        agent_key_path.get("workflows", [])
                        if agent_key_path
                        else []
                    ),
                },
                {
                    "task_type": task_type,
                    "task_description": task_description,
                    "workflows": (
                        subtask_key_path.get("workflows", [])
                        if subtask_key_path
                        else []
                    ),
                },
            ]

        if abstract_type == "agent_levels":
            merged_workflows = agent_key_path or {"workflows": []}
            return [
                {
                    "task_type": task_type,
                    "task_description": task_description,
                    "workflows": merged_workflows.get("workflows", []),
                },
            ]

        if abstract_type == "subtask_levels":
            merged_workflows = subtask_key_path or {"workflows": []}
            return [
                {
                    "task_type": task_type,
                    "task_description": task_description,
                    "workflows": merged_workflows.get("workflows", []),
                },
            ]

        raise ValueError("Invalid extracted_type")

    async def multi_levels_extract_CollectionSession(
        self,
        session_content,
        abstract_type="multi_levels",
    ):
        try:
            contents = []
            for msg in session_content:
                contents.append(
                    f"{msg.get('role', '')}: {msg.get('content', '')}",
                )
            contents = "\n".join(contents)

            session_summary = await self._extract_session_summary(contents)

            agent_key_path = None
            subtask_key_path = None

            if abstract_type in ["multi_levels", "agent_levels"]:
                agent_key_path = await self._extract_agent_roadmap(
                    session_summary,
                    contents,
                )

            if abstract_type in ["multi_levels", "subtask_levels"]:
                subtask_key_path = await self._extract_subtask_roadmap(
                    session_summary,
                    contents,
                )

            final_result = self._build_final_result(
                abstract_type,
                session_summary,
                agent_key_path,
                subtask_key_path,
            )

            return final_result

        except Exception as exc:
            logger.error(
                f"Error in multi_levels_extract_CollectionSession: {exc}",
            )
            raise

    async def get_summary(self, session_content):
        try:
            contents = []
            for msg in session_content:
                message = msg["message"]
                role_or_name = message.get("name", message.get("role"))
                content = message.get("content", "")
                contents.append(f"{role_or_name}: {content}")
            contents = "\n".join(contents)
            session_summary_response = await asyncio.to_thread(
                self.llm.generate_response,
                messages=[
                    {"role": "system", "content": SESSION_SUMMARY_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Session content: {contents}\n"
                            f"+{SESSION_SUMMARY_USER_PROMPT}"
                        ),
                    },
                ],
                response_format={
                    "type": (
                        "json_object"
                        if "qwen-max" not in self.config.llm.config["model"]
                        else "text"
                    ),
                },
            )

            try:
                session_summary = json.loads(
                    remove_code_blocks(session_summary_response),
                )
            except Exception as exc:
                try:
                    session_summary = extract_json_from_text(
                        session_summary_response,
                    )
                    if not isinstance(session_summary, dict):
                        logger.error(
                            f"Error in extracting session summary: {exc}",
                        )
                        session_summary = {
                            "task": "Unknown Task Type",
                            "problem_category": "Unknown Task Type",
                        }
                except Exception as exc_inner:
                    logger.error(
                        f"Error in extracting session summary: {exc_inner}",
                    )
                    session_summary = {
                        "task": "Unknown Task Type",
                        "problem_category": "Unknown Task Type",
                    }
            return session_summary

        except Exception as exc:
            logger.error(f"Error in get_summary: {exc}")
            raise

    async def extract_like_unlike_message(
        self,
        message,
        task_summary,
        message_type=None,
    ):
        try:
            if message_type == "like":
                prompt = EXTRACT_LIKE_MESSAGE.format(
                    task_description=task_summary.get(
                        "task",
                        "No task description provided",
                    ),
                    liked_message=message,
                    task_classification=task_summary.get(
                        "problem_category",
                        "Unknown",
                    ),
                )
            elif message_type == "dislike":
                prompt = EXTRACT_UNLIKE_MESSAGE.format(
                    task_description=task_summary.get(
                        "task",
                        "No task description provided",
                    ),
                    unliked_message=message,
                    task_classification=task_summary.get(
                        "problem_category",
                        "Unknown",
                    ),
                )
            else:
                raise ValueError(
                    "Invalid message_type: must be 'like' or 'dislike'.",
                )

            response = await asyncio.to_thread(
                self.llm.generate_response,
                messages=[{"role": "user", "content": prompt}],
            )
            return [
                {
                    "role": "user",
                    "content": response,
                },
            ]

        except Exception as exc:
            logger.error(f"Error in extract_like_unlike_message: {exc}")
            raise

    async def extract_user_edit_intent(self, user_edit, edit_type):
        try:
            edit_preference = None
            if edit_type == "EDIT_ROADMAP":
                prompt = "The content of `diff_map` is as follows:\n{diff_map}"
                user_prompt = prompt.strip().format(
                    diff_map=json.dumps(
                        user_edit,
                        indent=2,
                        ensure_ascii=False,
                    ),
                )
                edit_intent_response = await asyncio.to_thread(
                    self.llm.generate_response,
                    messages=[
                        {"role": "system", "content": EXTRACT_EDIT_PREFERENCE},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={
                        "type": (
                            "json_object"
                            if "qwen-max"
                            not in self.config.llm.config["model"]
                            else "text"
                        ),
                    },
                )

                try:
                    edit_preference = json.loads(
                        remove_code_blocks(edit_intent_response),
                    )
                except Exception as exc:
                    try:
                        edit_preference = extract_json_from_text(
                            edit_intent_response,
                        )
                        if (
                            not isinstance(edit_preference, dict)
                            or "analysis_result" not in edit_preference
                        ):
                            logger.error(
                                f"Error in extracting edit preference: {exc}",
                            )
                            edit_preference = {"analysis_result": []}
                    except Exception as exc_inner:
                        logger.error(
                            f"Error in extracting edit preference: "
                            f"{exc_inner}",
                        )
                        edit_preference = {"analysis_result": []}

            elif edit_type == "EDIT_FILE":
                prompt = (
                    "The output of a `git diff` command is as follows:\n"
                    "{diff_output}"
                )
                user_prompt = prompt.strip().format(
                    diff_output=json.dumps(
                        user_edit["operation_data"],
                        indent=2,
                        ensure_ascii=False,
                    ),
                )
                edit_intent_response = await asyncio.to_thread(
                    self.llm.generate_response,
                    messages=[
                        {
                            "role": "system",
                            "content": EXTRACT_EDIT_FILE_PREFERENCE,
                        },
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={
                        "type": (
                            "json_object"
                            if "qwen-max"
                            not in self.config.llm.config["model"]
                            else "text"
                        ),
                    },
                )

                try:
                    edit_preference = json.loads(
                        remove_code_blocks(edit_intent_response),
                    )
                except Exception as exc:
                    try:
                        edit_preference = extract_json_from_text(
                            edit_intent_response,
                        )
                        if (
                            not isinstance(edit_preference, dict)
                            or "analysis_result" not in edit_preference
                        ):
                            logger.error(
                                f"Error in extracting edit file preference: "
                                f"{exc}",
                            )
                            edit_preference = {"analysis_result": []}
                    except Exception as exc_inner:
                        logger.error(
                            f"Error in extracting edit file preference: "
                            f"{exc_inner}",
                        )
                        edit_preference = {"analysis_result": []}

            logger.info(f"Extracted edit preference: {edit_preference}")
            return edit_preference

        except Exception as exc:
            logger.error(f"Error in extract_user_edit_intent: {exc}")
            raise

    async def _extract_chat_preference(
        self,
        chat_type: str,
        chat_message: str,
        session_content: str,
        system_prompt: str,
    ) -> Dict[str, Any]:
        """
        Extract preference from chat intent response.

        Args:
            chat_type: Type of chat (START_CHAT, BREAK_CHAT, FOLLOWUP_CHAT).
            chat_message: The chat message content.
            session_content: The session content.
            system_prompt: The system prompt for LLM.

        Returns:
            Dictionary with preference message.
        """
        message_key = (
            "start_message"
            if chat_type == "START_CHAT"
            else "break_message"
            if chat_type == "BREAK_CHAT"
            else "followup_message"
        )
        user_prompt = (
            f"The content of `{message_key}` is:\n{chat_message}\n"
            f"The content of `chat_session` is:\n{session_content}\n"
            "Use these to extract the user's most plausible "
            "preference."
        )

        preference_response = await asyncio.to_thread(
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

        try:
            preference_message = json.loads(
                remove_code_blocks(preference_response),
            )
        except Exception as exc:
            try:
                preference_message = extract_json_from_text(
                    preference_response,
                )
                if not isinstance(preference_message, dict) or (
                    "type" not in preference_message
                    and "user_preference" not in preference_message
                ):
                    logger.error(
                        f"Error in extracting chat intent preference: {exc}",
                    )
                    preference_message = {
                        "type": "irrelevant",
                        "user_preference": "null",
                    }
            except Exception as exc_inner:
                logger.error(
                    f"Error in extracting chat intent preference: "
                    f"{exc_inner}",
                )
                preference_message = {
                    "type": "irrelevant",
                    "user_preference": "null",
                }

        return preference_message

    async def extract_chat_intent(
        self,
        session_content,
        chat_type,
        chat_message,
    ):
        try:
            prompt_map = {
                "START_CHAT": EXTRACT_START_CHAT_PREFERENCE,
                "BREAK_CHAT": EXTRACT_BREAK_CHAT_PREFERENCE,
                "FOLLOWUP_CHAT": EXTRACT_FOLLOWUP_CHAT_PREFERENCE,
            }

            if chat_type not in prompt_map:
                logger.warning(f"Unknown chat_type: {chat_type}")
                return {
                    "type": "irrelevant",
                    "user_preference": "null",
                }

            preference_message = await self._extract_chat_preference(
                chat_type,
                chat_message,
                session_content,
                prompt_map[chat_type],
            )

            return preference_message

        except Exception as exc:
            logger.error(f"Error in extract_StartChat_message: {exc}")
            raise
