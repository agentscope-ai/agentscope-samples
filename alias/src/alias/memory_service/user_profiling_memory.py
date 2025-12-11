# -*- coding: utf-8 -*-
import asyncio
import datetime
import uuid
from copy import deepcopy
from typing import Any, Callable, Coroutine, Dict, Literal, Optional

import pytz
from mem0.configs.base import MemoryConfig

from .basememory import BaseMemory
from .memory_base.candidate_pool import AsyncVectorCandidateMemory
from .memory_base.userinfo_pool import AsyncVectorUserInfoMemory
from .memory_base.userprofiling_pool import AsyncVectorUserProfilingMemory
from .profiling_utils.logging_utils import setup_logging
from .profiling_utils.memory_utils import (
    format_session_content,
    process_extracted_workflows_from_session_content_under_collection_action,
)
from .service.config.settings import create_memory_config_with_collection

logger = setup_logging()


class AsyncUserProfilingMemory(
    BaseMemory,
):  # pylint: disable=too-many-public-methods
    def __init__(
        self,
        user_profiling_config: Optional[MemoryConfig] = None,
        candidate_pool_config: Optional[MemoryConfig] = None,
    ):
        user_profiling_config = (
            create_memory_config_with_collection(
                "user_profiling_pool",
                persist_history=True,
            )
            if user_profiling_config is None
            else user_profiling_config
        )
        logger.info(f"User profiling memory config: {user_profiling_config}")

        candidate_pool_config = (
            create_memory_config_with_collection(
                "candidate_pool",
                persist_history=True,
            )
            if candidate_pool_config is None
            else candidate_pool_config
        )
        logger.info(f"Candidate pool memory config: {candidate_pool_config}")

        user_info_pool_config = create_memory_config_with_collection(
            "user_info_pool",
            persist_history=True,
        )
        logger.info(f"User info pool memory config: {user_info_pool_config}")

        self.candidate_pool = AsyncVectorCandidateMemory(
            config=candidate_pool_config,
        )
        self.user_profiling_pool = AsyncVectorUserProfilingMemory(
            config=user_profiling_config,
        )
        self.user_info_pool = AsyncVectorUserInfoMemory(
            config=user_info_pool_config,
        )
        super().__init__()

    async def add_memory(self, uid: str, content: list, **kwargs):
        """
        Add memory to the candidate pool, then promote the best candidate
        to the user profiling pool
        Args:
            uid (str): User ID.
            content (list): The memory content to be added.
            **kwargs: Additional keyword arguments, such as session_id
                and metadata.
        Returns:
            dict: Results from both candidate pool and user profiling pool.
        """
        # Add memory to the candidate pool first
        candidate_pool_task = asyncio.create_task(
            self.add_memory_to_candidate_pool(
                uid,
                content,
                session_id=kwargs.get("session_id"),
                metadata=kwargs.get("metadata"),
                extract_facts=kwargs.get("extract_facts", True),
            ),
        )
        candidate_pool_add_result = await candidate_pool_task

        # Select and promote the best candidate from the candidate pool
        best_candidate_task = asyncio.create_task(
            self._promote_best_candidate(uid),
        )
        best_candidate = await best_candidate_task

        try:
            add_memories_ids = [
                m["id"] for m in candidate_pool_add_result["results"]
            ]
        except KeyError:
            add_memories_ids = []

        user_profiling_add_result = {}
        if best_candidate is not None:
            logger.info(f"Best candidate: {best_candidate}")
            try:
                meta_data_for_user_profiling = {"is_confirmed": 0}
                meta_data_for_user_profiling.update(
                    {
                        k: v
                        for k, v in best_candidate["metadata"].items()
                        if k
                        not in ["last_access_time", "visited_count", "score"]
                    },
                )
                user_profiling_add_result = (
                    await self.add_memory_to_user_profiling_pool(
                        uid=best_candidate["user_id"],
                        content=best_candidate["content"],
                        session_id=best_candidate["metadata"]["session_id"],
                        metadata=meta_data_for_user_profiling,
                        extract_facts=kwargs.get(
                            "extract_facts_user_profiling",
                            False,
                        ),
                    )
                )
                if best_candidate["id"] not in add_memories_ids:
                    asyncio.create_task(
                        self._safe_background_task(
                            self.candidate_pool.reset_metadata(
                                best_candidate["id"],
                            ),
                            f"reset_metadata_{best_candidate['id']}",
                            uid,
                        ),
                    )
            except Exception as e:
                logger.error(f"Failed to add to user profiling pool: {e}")
                user_profiling_add_result = {"error": str(e)}
        else:
            logger.info(f"No candidate: {best_candidate}")

        return {
            "candidates": candidate_pool_add_result,
            "profiling": user_profiling_add_result,
        }

    async def _promote_best_candidate(self, uid: str):
        """
        Select and promote the best candidate memory for a user
        Args:
            uid (str): User ID.
        Returns:
            dict or None: The best candidate's information (id, user_id,
                content, metadata, score), or None if no candidate found.
        Raises:
            ValueError: If Qdrant collection corruption is detected and
                cannot be reset.
        """

        async def _do_promote():
            # Get all candidate memories for the user
            all_candidates = await self.candidate_pool.get_all(user_id=uid)
            all_candidates = await self._safely_resolve_coroutines(
                all_candidates,
            )

            logger.info(f"All candidates for promotion: {all_candidates}")
            candidates = all_candidates.get("results", [])

            if not candidates:
                return None

            # Get the candidate with the highest score
            (
                highest_score_memory,
                highest_score,
            ) = await self.candidate_pool.get_highest_score_memory_by_threshold(  # noqa: E501
                candidates,
            )
            if highest_score_memory is None:
                return None

            return {
                "id": highest_score_memory["id"],
                "user_id": uid,
                "content": highest_score_memory["memory"],
                "metadata": highest_score_memory["metadata"],
                "score": highest_score,
            }

        return await self._handle_qdrant_corruption(uid, _do_promote)

    async def add_memory_to_candidate_pool(
        self,
        uid: str,
        content,
        session_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        **kwargs,
    ):
        """
        Add new messages to the candidate pool for a user, and extract
        the user info and user event memories.
        User info memories are added into the user_info_pool, and user
        event memories are added into the user_profiling_pool.

        Args:
            uid (str): User ID.
            content: Messages to add.
            session_id (Optional[str]): Session ID.
            metadata (Optional[dict]): Additional metadata for the messages.
            **kwargs: Other keyword arguments passed to the candidate pool.
        Returns:
            The result of adding messages to the candidate pool.
        """
        now = datetime.datetime.now(pytz.timezone("US/Pacific")).isoformat()
        metadata = deepcopy(metadata) if metadata else {}
        if "session_id" not in metadata:
            metadata["session_id"] = session_id if session_id else ""
        else:
            if session_id and metadata["session_id"] != session_id:
                raise ValueError(
                    "session_id in metadata and kwargs are not equal.",
                )

        metadata_user_info = deepcopy(metadata)  # metadata for user_info_pool
        metadata_user_event = deepcopy(
            metadata,
        )  # metadata for user_profiling_pool

        metadata.update(
            {
                "last_access_time": now,
                "visited_count": 1,
                # "score": await self.candidate_pool.compute_score(
                #     1, now, now_ts
                # )
            },
        )

        if "action_type" not in metadata:
            metadata["action_type"] = "NORMAL"
            metadata_user_info["action_type"] = "NORMAL"
            metadata_user_event["action_type"] = "NORMAL"

        if "memory_type" not in metadata:
            metadata[
                "memory_type"
            ] = await self.candidate_pool.get_memory_type(content)

        tasks = [
            self.candidate_pool.add(
                user_id=uid,
                messages=content,
                metadata=metadata,
                **kwargs,
            ),
            self.user_info_pool.get_user_info_memory(content),
            self.user_profiling_pool.get_user_event_memory(content),
        ]

        candidate_pool_add_result, facts, events = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )
        logger.info(f"Facts: {facts}, events: {events}")

        if isinstance(candidate_pool_add_result, Exception):
            logger.error(
                f"Failed to add to candidate pool: "
                f"{candidate_pool_add_result}",
            )
            raise candidate_pool_add_result

        logger.info("New messages are added into candidate_pool.")

        # Start background tasks to process facts and events
        background_tasks = []

        if not isinstance(facts, Exception) and facts:
            user_info_memories = [
                {"role": "user", "content": fact} for fact in facts
            ]
            metadata_user_info["memory_type"] = "USER INFO"
            background_tasks.append(
                self._safe_background_task(
                    self.user_info_pool.add(
                        user_id=uid,
                        messages=user_info_memories,
                        metadata=metadata_user_info,
                        infer=False,
                    ),
                    "add_user_info_memories",
                    uid,
                ),
            )

        if not isinstance(events, Exception) and events:
            user_profiling_memories = [
                {"role": "user", "content": event} for event in events
            ]
            metadata_user_event["memory_type"] = "USER EVENT"
            background_tasks.append(
                self._safe_background_task(
                    self.user_profiling_pool.add(
                        user_id=uid,
                        messages=user_profiling_memories,
                        metadata=metadata_user_event,
                        infer=False,
                    ),
                    "add_user_event_memories",
                    uid,
                ),
            )

        for task in background_tasks:
            asyncio.create_task(task)

        return candidate_pool_add_result

    async def add_memory_to_user_profiling_pool(
        self,
        uid: str,
        content,
        session_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        **kwargs,
    ):
        """
        Add new messages to the user profiling pool for a user.

        Args:
            uid (str): User ID.
            content: Messages to add.
            session_id (Optional[str]): Session ID. If not provided, a new
                UUID will be generated.
            metadata (Optional[dict]): Additional metadata for the messages.
            **kwargs: Other keyword arguments passed to the user profiling
                pool.

        Returns:
            The result of adding messages to the user profiling pool.
        """
        metadata = deepcopy(metadata) if metadata else {}
        # Ensure session_id is set in metadata
        if "session_id" not in metadata:
            metadata["session_id"] = (
                session_id if session_id else str(uuid.uuid4())
            )
        else:
            if session_id and metadata["session_id"] != session_id:
                raise ValueError(
                    "session_id in metadata and kwargs are not equal.",
                )
        if "is_confirmed" not in metadata:
            metadata["is_confirmed"] = 0

        # Set default action_type if not provided
        if "action_type" not in metadata:
            metadata["action_type"] = "NORMAL"

        if "memory_type" not in metadata:
            metadata[
                "memory_type"
            ] = await self.user_profiling_pool.get_memory_type(content)

        user_profiling_add_result = await self.user_profiling_pool.add(
            user_id=uid,
            messages=content,
            metadata=metadata,
            **kwargs,
        )
        logger.info("New messages are added into user_profiling_pool.")
        return user_profiling_add_result

    async def clear_memory(self, uid: str) -> None:
        """
        Clear all memory for a user from both candidate pool and user
        profiling pool
        Args:
            uid (str): User ID to clear memory for
        """
        try:
            results = await asyncio.gather(
                self.candidate_pool.delete_all(user_id=uid),
                self.user_profiling_pool.delete_all(user_id=uid),
                self.user_info_pool.delete_all(user_id=uid),
                return_exceptions=True,
            )

            pool_names = [
                "candidate pool",
                "user profiling pool",
                "user info pool",
            ]
            for _, (result, pool_name) in enumerate(zip(results, pool_names)):
                if isinstance(result, Exception):
                    logger.error(
                        f"Error clearing {pool_name} for user {uid}: {result}",
                    )
                else:
                    logger.info(
                        f"Successfully cleared {pool_name} for user "
                        f"{uid}: {result}",
                    )

            logger.info(f"Memory clearing completed for user {uid}")

        except Exception as e:
            logger.error(f"Error in clear_memory for user {uid}: {e}")
            raise

    async def retrieve(self, uid: str, query: str, **kwargs):
        async def _do_retrieve():
            tasks = [
                self.candidate_pool.search(user_id=uid, query=query, **kwargs),
                self.user_profiling_pool.search(
                    user_id=uid,
                    query=query,
                    **kwargs,
                ),
                self.user_info_pool.search(user_id=uid, query=query, **kwargs),
            ]

            results = await asyncio.gather(*tasks)
            return {
                "candidates": results[0],
                "profiling": results[1],
                "user_info": results[2],
            }

        return await self._handle_qdrant_corruption(uid, _do_retrieve)

    async def process_content(self, uid: str, content: list) -> list:
        # TODO
        return [{"message": "process content not implemented"}]

    async def show_all_memory(self, uid: str):
        async def _do_show_all():
            tasks = [
                self.candidate_pool.get_all(user_id=uid),
                self.user_profiling_pool.get_all(user_id=uid),
                self.user_info_pool.get_all(user_id=uid),
            ]

            results = await asyncio.gather(*tasks)

            candidates, profiling, user_info = await asyncio.gather(
                self._safely_resolve_coroutines(results[0]),
                self._safely_resolve_coroutines(results[1]),
                self._safely_resolve_coroutines(results[2]),
            )

            logger.info(
                f"Show all memory for user {uid}. candidates: {candidates}, "
                f"profiling: {profiling}, user_info: {user_info}",
            )
            return {
                "candidates": candidates,
                "profiling": profiling,
                "user_info": user_info,
            }

        return await self._handle_qdrant_corruption(uid, _do_show_all)

    async def show_all_user_profiles(self, uid: str):
        async def _do_show_all_user_profiles():
            tasks = [self.user_profiling_pool.get_all(user_id=uid)]
            results = await asyncio.gather(*tasks)
            logger.info(f"Show all user profiles for user {uid}: {results[0]}")
            formatted_results = []
            for result in results[0]["results"]:
                formatted_results.append(
                    {
                        "pid": result["id"],
                        "uid": result["user_id"],
                        "content": result["memory"],
                        "metadata": {
                            "session_id": (
                                result["metadata"]["session_id"]
                                if "session_id" in result["metadata"]
                                else None
                            ),
                            "is_confirmed": (
                                result["metadata"]["is_confirmed"]
                                if "is_confirmed" in result["metadata"]
                                else 0
                            ),
                        },
                    },
                )
            return formatted_results

        return await self._handle_qdrant_corruption(
            uid,
            _do_show_all_user_profiles,
        )

    async def get_memory(
        self,
        uid: str,
        memory_from: Literal[
            "candidate_pool",
            "user_profiling_pool",
            "both",
        ] = "both",
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """
        Retrieve memory data for a user from the candidate pool, user
        profiling pool, or both
        Args:
            uid (str): User ID whose memory is to be retrieved.
            memory_from (Literal["candidate_pool", "user_profiling_pool",
                "both"], optional): Specify which memory pool to query.
                Defaults to "both".
            agent_id (Optional[str], optional): Agent ID for filtering.
                Defaults to None.
            run_id (Optional[str], optional): Run ID for filtering.
                Defaults to None.
            filters (Optional[Dict[str, Any]], optional): Additional filter
                conditions. Defaults to None.
            **kwargs: Additional keyword arguments passed to the underlying
                get_all methods.
        Returns:
            dict: A dictionary containing the results from the candidate
                pool and/or user profiling pool.
                {
                    "candidates": ...,
                    "profiling": ...,
                    "user_info": ...
                }
        """
        if memory_from not in [
            "candidate_pool",
            "user_profiling_pool",
            "both",
        ]:
            raise ValueError(f"Invalid memory_from: {memory_from}")

        async def _do_get_memory():
            tasks = []
            task_names = []

            if memory_from in ["candidate_pool", "both"]:
                tasks.append(
                    self.candidate_pool.get_all(
                        user_id=uid,
                        agent_id=agent_id,
                        run_id=run_id,
                        filters=filters,
                        **kwargs,
                    ),
                )
                task_names.append("candidates")
            else:
                tasks.append(asyncio.create_task(asyncio.sleep(0, result={})))
                task_names.append("candidates")

            if memory_from in ["user_profiling_pool", "both"]:
                tasks.append(
                    self.user_profiling_pool.get_all(
                        user_id=uid,
                        agent_id=agent_id,
                        run_id=run_id,
                        filters=filters,
                        **kwargs,
                    ),
                )
                task_names.append("profiling")
            else:
                tasks.append(asyncio.create_task(asyncio.sleep(0, result={})))
                task_names.append("profiling")

            tasks.append(
                self.user_info_pool.get_all(
                    user_id=uid,
                    agent_id=agent_id,
                    run_id=run_id,
                    filters=filters,
                    **kwargs,
                ),
            )
            task_names.append("user_info")

            results = await asyncio.gather(*tasks)

            resolved_results = await asyncio.gather(
                *[
                    self._safely_resolve_coroutines(result)
                    for result in results
                ],
            )

            return {
                "candidates": resolved_results[0],
                "profiling": resolved_results[1],
                "user_info": resolved_results[2],
            }

        return await self._handle_qdrant_corruption(uid, _do_get_memory)

    async def delete(self, uid: str, key: Any) -> None:
        # TODO
        logger.warning(
            f"delete memory by key not implemented for uid={uid}, key={key}",
        )

    async def direct_add_profile(
        self,
        uid: str,
        content: Any,
        profiling_id: str = None,
    ):
        """
        Directly add a user profile to the user profiling pool.
        Args:
            uid (str): The user ID.
            content (Any): The content of the user profile to be added.
            profiling_id (str, optional): The profiling ID to use as
                memory_id. If not provided, a new one will be generated.
                If provided, it must be a valid UUID4.
        Returns:
            dict: The result of the add operation.
        """
        if not content:
            logger.warning("No content provided, skipping direct_add_profile")
            return {"results": None}

        metadata = {
            # "session_id": uuid.uuid4(),
            "session_id": "",
            "action_type": "NORMAL",
            "is_confirmed": 1,
        }

        def is_uuid4(value):
            try:
                uuid_obj = uuid.UUID(value)
                return uuid_obj.version == 4
            except ValueError:
                return False

        if profiling_id and is_uuid4(profiling_id):
            metadata["memory_id"] = profiling_id

        try:
            user_profiling_add_result = await self.add_memory_to_user_profiling_pool(  # noqa: E501
                uid=uid,
                content=content,
                metadata=metadata,
                infer=False,
                # extract_facts=True,
            )
            logger.info(
                "User profiling pool Qdrant collection added successfully.",
            )
            return user_profiling_add_result
        except Exception as e:
            logger.error(f"Failed to add profile for user {uid}: {e}")
            return {"results": None, "error": str(e)}

    async def delete_by_profiling_id(self, uid: str, pid: str = None):
        """
        Delete a user profile from the user profiling pool by pid.

        Args:
            uid (str): The user ID.
            pid (str): The profiling ID to delete.

        Returns:
            dict: The result of the delete operation or a message if not found.
        """
        if pid is None:
            logger.warning(
                "No profiling_id provided, skipping delete_by_profiling_id",
            )
            return {
                "message": (
                    "No profiling_id provided, "
                    "skipping delete_by_profiling_id"
                ),
            }

        try:
            profilings = await self.get_memory(
                uid=uid,
                memory_from="user_profiling_pool",
            )
            user_profiling = profilings["profiling"].get("results", [])

            if not user_profiling:
                logger.warning(
                    f"No user_profiling found for user {uid}, "
                    f"skipping delete_by_profiling_id",
                )
                return {
                    "message": (
                        f"No user_profiling found for user {uid}, "
                        f"skipping delete_by_profiling_id"
                    ),
                }

            profiling_ids = [item["id"] for item in user_profiling]

            if pid not in profiling_ids:
                logger.warning(
                    f"No user_profiling found with id {pid} for user {uid}",
                )
                return {
                    "message": (
                        f"No user_profiling found with id {pid} "
                        f"for user {uid}"
                    ),
                }

            asyncio.create_task(
                self._safe_background_task(
                    self.user_profiling_pool.delete(memory_id=pid),
                    f"delete_profiling_{pid}",
                    uid,
                ),
            )
            return {
                "message": (
                    f"User profiling with id {pid} deleted successfully "
                    f"for user {uid}"
                ),
            }

        except Exception as e:
            logger.error(
                f"Error in delete_by_profiling_id for user {uid}: {e}",
            )
            return {"message": f"Error deleting profiling: {str(e)}"}

    def _validate_profile_update_params(
        self,
        pid: Optional[str],
        content_after: Any,
    ) -> Optional[str]:
        """
        Validate parameters for profile update.

        Args:
            pid: The profiling ID to update.
            content_after: The content after update.

        Returns:
            Error message if validation fails, None otherwise.
        """
        if pid is None:
            logger.warning(
                "No profiling_id provided, skipping direct_update_profile",
            )
            return "No profiling_id provided, skipping direct_update_profile"

        if not content_after:
            logger.warning(
                "No content_after provided, skipping direct_update_profile",
            )
            return (
                "No content_after provided, " "skipping direct_update_profile"
            )

        return None

    def _process_content_for_update(
        self,
        content_before: Any,
        content_after: Any,
    ) -> tuple[Dict[str, Any], Any, Optional[str]]:
        """
        Process content_before and content_after to extract metadata and
        update data.

        Args:
            content_before: The content before update.
            content_after: The content after update.

        Returns:
            Tuple of (metadata, update_data, error_message).
            error_message is None if processing succeeds.
        """
        metadata: Dict[str, Any] = {}
        update_data = None

        if isinstance(content_after, str):
            if content_before:
                metadata = {"content_before": content_before}
            update_data = content_after
        elif isinstance(content_after, dict):
            if (
                "content" not in content_after
                or content_after["content"] is None
            ):
                logger.warning("No content provided in content_after")
                return {}, None, "No content provided in content_after"
            if (
                content_before
                and isinstance(content_before, dict)
                and "content" in content_before
            ):
                metadata = {"content_before": content_before["content"]}
            update_data = content_after["content"]
        else:
            logger.warning("Invalid content_after type")
            return {}, None, "Invalid content_after type"

        metadata["is_confirmed"] = 1
        return metadata, update_data, None

    async def direct_update_profile(
        self,
        uid: str,
        pid: str = None,
        content_before: Any = None,
        content_after: Any = None,
    ):
        """
        Directly update a user profile in the user profiling pool.

        Args:
            uid (str): The user ID.
            pid (str, optional): The profiling ID to update.
            content_before (Any): The content of the user profile before
                update.
            content_after (Any): The content of the user profile after
                update.

        Returns:
            dict: The result of the update operation or a message if not found.
        """
        error_msg = self._validate_profile_update_params(pid, content_after)
        if error_msg:
            return {"message": error_msg}

        try:
            profilings = await self.get_memory(
                uid=uid,
                memory_from="user_profiling_pool",
            )
            user_profiling = profilings["profiling"].get("results", [])

            if not user_profiling:
                logger.warning(f"No user_profiling found for user {uid}")
                return {"message": f"No user_profiling found for user {uid}"}

            profiling_ids = [item["id"] for item in user_profiling]

            if pid not in profiling_ids:
                logger.warning(
                    f"No user_profiling found with id {pid} for user {uid}",
                )
                return {
                    "message": (
                        f"No user_profiling found with id {pid} "
                        f"for user {uid}"
                    ),
                }

            (
                metadata,
                update_data,
                error_msg,
            ) = self._process_content_for_update(
                content_before,
                content_after,
            )
            if error_msg:
                return {"message": error_msg}

            await self.user_profiling_pool.update(
                memory_id=pid,
                data=update_data,
                metadata=metadata,
            )
            return {
                "message": (
                    f"User profiling with id {pid} updated successfully "
                    f"for user {uid}"
                ),
            }

        except Exception as e:
            logger.error(f"Error in direct_update_profile for user {uid}: {e}")
            return {"message": f"Error updating profiling: {str(e)}"}

    async def direct_confirm_profile(self, uid: str, pid: str = None):
        """
        Directly confirm a user profile in the user profiling pool.

        Args:
            uid (str): The user ID.
            pid (str, optional): The profiling ID to update.

        Returns:
            dict: The result of the confirm operation or a message if not
                found.
        """
        if pid is None:
            logger.warning(
                "No profiling_id provided, skipping direct_confirm_profile",
            )
            return {
                "message": (
                    "No profiling_id provided, "
                    "skipping direct_confirm_profile"
                ),
            }

        try:
            profilings = await self.get_memory(
                uid=uid,
                memory_from="user_profiling_pool",
            )
            user_profiling = profilings["profiling"].get("results", [])

            if not user_profiling:
                logger.warning(f"No user_profiling found for user {uid}")
                return {"message": f"No user_profiling found for user {uid}"}

            profiling_ids = [item["id"] for item in user_profiling]

            if pid not in profiling_ids:
                logger.warning(
                    f"No user_profiling found with id {pid} for user {uid}",
                )
                return {
                    "message": (
                        f"No user_profiling found with id {pid} "
                        f"for user {uid}"
                    ),
                }
            data = user_profiling[profiling_ids.index(pid)]["memory"]
            metadata = deepcopy(
                user_profiling[profiling_ids.index(pid)]["metadata"],
            )
            metadata["is_confirmed"] = 1

            await self.user_profiling_pool.update(
                memory_id=pid,
                data=data,
                metadata=metadata,
            )
            return {
                "status": "success",
                "data": {
                    "pid": pid,
                    "uid": uid,
                    "content": data,
                    "metadata": {
                        "session_id": (
                            metadata["session_id"]
                            if "session_id" in metadata
                            else None
                        ),
                        "is_confirmed": metadata["is_confirmed"],
                    },
                },
            }

        except Exception as e:
            logger.error(
                f"Error in direct_confirm_profile for user {uid}: {e}",
            )
            return {"message": f"Error confirming profiling: {str(e)}"}

    async def record_action(
        self,
        uid: str,
        action: str,
        session_id: Optional[str] = None,
        reference_time: Optional[str] = None,
        action_message_id: Optional[str] = None,
        data: Optional[Any] = None,
        session_content=None,
        **kwargs,
    ):
        """
        record the action of the user
        Args:
            uid (str): the user id
            action (str): the action
            session_id (str): the session id
            reference_time (str): the reference time
            action_message_id (str): the action message id
            data (Any): the user edit or chat content
            session_content (list): the session content
        Returns:
            dict: the result of the action
        """
        try:
            logger.info(
                f"record_action called with: uid={uid}, action={action}, "
                f"session_id={session_id}, "
                f"action_message_id={action_message_id}",
            )
            logger.info(
                f"session_content length: "
                f"{len(session_content) if session_content else 0}",
            )

            # Handle actions that require direct method calls
            if action == "COLLECT_SESSION":
                return await self._handle_collect_session(
                    uid,
                    session_content,
                    reference_time,
                    session_id,
                )
            elif action == "UNCOLLECT_SESSION":
                return await self._handle_uncollect_session(uid, session_id)
            elif action == "COLLECT_TOOL":
                return await self._handle_collect_tool(
                    uid,
                    session_content,
                    action_message_id,
                    reference_time,
                    session_id,
                )
            elif action == "UNCOLLECT_TOOL":
                if action_message_id is None:
                    raise ValueError(
                        "action_message_id is required for UNCOLLECT_TOOL",
                    )
                return await self._handle_uncollect_tool(
                    uid,
                    session_id,
                    action_message_id,
                )

            # Action handlers that use lambdas (no arguments needed)
            action_handlers: Dict[
                str,
                Callable[[], Coroutine[Any, Any, Any]],
            ] = {
                "LIKE": lambda: self._handle_feedback(
                    uid,
                    session_id,
                    action_message_id,
                    session_content,
                    reference_time,
                    "like",
                ),
                "DISLIKE": lambda: self._handle_feedback(
                    uid,
                    session_id,
                    action_message_id,
                    session_content,
                    reference_time,
                    "dislike",
                ),
                "CANCEL_LIKE": lambda: self._handle_cancel_feedback(
                    uid,
                    session_id,
                    action_message_id,
                    "like",
                ),
                "CANCEL_DISLIKE": lambda: self._handle_cancel_feedback(
                    uid,
                    session_id,
                    action_message_id,
                    "dislike",
                ),
                "EDIT_ROADMAP": lambda: self._handle_edit(
                    uid,
                    data,
                    reference_time,
                    session_id,
                    action_message_id,
                    "EDIT_ROADMAP",
                ),
                "EDIT_FILE": lambda: self._handle_edit(
                    uid,
                    data,
                    reference_time,
                    session_id,
                    action_message_id,
                    "EDIT_FILE",
                ),
                "START_CHAT": lambda: self._handle_chat(
                    uid,
                    session_content,
                    data,
                    reference_time,
                    session_id,
                    action_message_id,
                    "START_CHAT",
                ),
                "FOLLOWUP_CHAT": lambda: self._handle_chat(
                    uid,
                    session_content,
                    data,
                    reference_time,
                    session_id,
                    action_message_id,
                    "FOLLOWUP_CHAT",
                ),
                "BREAK_CHAT": lambda: self._handle_chat(
                    uid,
                    session_content,
                    data,
                    reference_time,
                    session_id,
                    action_message_id,
                    "BREAK_CHAT",
                ),
            }

            handler = action_handlers.get(action)
            if handler is None:
                if action in ["EXECUTE_SHELL_COMMAND", "BROWSER_OPERATION"]:
                    logger.info(
                        f"Processing {action} action - not yet implemented",
                    )
                    return None
                else:
                    raise ValueError(f"Unknown action {action}")

            return await handler()

        except Exception as e:
            import traceback

            logger.error(f"Error in record_action: {str(e)}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            logger.error(
                f"Context: uid={uid}, action={action}, "
                f"session_id={session_id}, "
                f"action_message_id={action_message_id}",
            )
            raise

    async def _handle_collect_session(
        self,
        uid: str,
        session_content,
        reference_time: Optional[str],
        session_id: Optional[str],
    ):
        """Handle COLLECT_SESSION operation with optimized parallel
        processing"""
        logger.info("Processing Collect_Session action")

        # Parallel processing: formatting and abstraction
        abstract_content = await self.process_collection_action(
            session_content=format_session_content(session_content),
            abstract_type="one_step",
        )

        # Parallel add to two pools
        results = await self._parallel_add_to_pools(
            uid=uid,
            content=abstract_content,
            reference_time=reference_time,
            session_id=session_id,
            action_type="SESSION",
        )

        logger.info(f"record_action results: {results}")
        return results

    async def _handle_uncollect_session(
        self,
        uid: str,
        session_id: Optional[str],
    ):
        """Handle UNCOLLECT_SESSION operation"""
        logger.info("Processing UnCollectSession action")
        results = await self.record_uncollect_session(
            uid=uid,
            session_id=session_id,
        )
        logger.info(f"record_action results: {results}")
        return results

    async def _handle_collect_tool(
        self,
        uid: str,
        session_content,
        action_message_id: Optional[str],
        reference_time: Optional[str],
        session_id: Optional[str],
    ):
        """Handle COLLECT_TOOL operation"""
        logger.info("Processing CollectTool action")
        collect_tool_content = await self.process_collection_tool_action(
            session_content=session_content,
            action_message_id=action_message_id,
        )

        results = await self._parallel_add_to_pools(
            uid=uid,
            content=collect_tool_content,
            reference_time=reference_time,
            session_id=session_id,
            action_type="TOOL",
            action_message_id=action_message_id,
        )

        logger.info(f"record_action results: {results}")
        return results

    async def _handle_uncollect_tool(
        self,
        uid: str,
        session_id: Optional[str],
        action_message_id: str,
    ):
        """Handle UNCOLLECT_TOOL operation"""
        logger.info("Processing UnCollectTool action")
        results = await self.record_uncollect_tool(
            uid=uid,
            session_id=session_id,
            action_message_id=action_message_id,
        )
        logger.info(f"record_action results: {results}")
        return results

    async def _handle_feedback(
        self,
        uid: str,
        session_id: Optional[str],
        action_message_id: Optional[str],
        session_content,
        reference_time: Optional[str],
        feedback_type: str,
    ):
        """Handle LIKE/DISLIKE operation"""
        logger.info(f"Processing {feedback_type.upper()} action")

        if action_message_id is None:
            logger.warning(
                f"action_message_id is None for {feedback_type} action",
            )
            return {
                f"{feedback_type.upper()} results": (
                    "No message ID provided, skipping action."
                ),
            }

        message = await self.process_like_unlike_message_action(
            session_content=session_content,
            action_message_id=action_message_id,
            feedback_type=feedback_type,
        )

        results = await self._parallel_add_to_pools(
            uid=uid,
            content=message,
            reference_time=reference_time,
            session_id=session_id,
            action_type=feedback_type.upper(),
            action_message_id=action_message_id,
        )

        logger.info(f"record_action results: {results}")
        return results

    async def _handle_cancel_feedback(
        self,
        uid: str,
        session_id: Optional[str],
        action_message_id: Optional[str],
        feedback_type: str,
    ):
        """Handle CANCEL_LIKE/CANCEL_DISLIKE operation"""
        logger.info(f"Processing CANCEL_{feedback_type.upper()} action")

        if action_message_id is None:
            logger.warning(
                f"action_message_id is None for CANCEL_{feedback_type} action",
            )
            return {
                f"Cancel {feedback_type.upper()} results": (
                    "No message ID provided, skipping cancel action."
                ),
            }

        results = await self.record_cancel_like_unlike(
            uid=uid,
            session_id=session_id,
            action_message_id=action_message_id,
            action_type=feedback_type,
        )
        logger.info(f"record_action results: {results}")
        return results

    async def _handle_edit(
        self,
        uid: str,
        data: Any,
        reference_time: Optional[str],
        session_id: Optional[str],
        action_message_id: Optional[str],
        edit_type: str,
    ):
        """Handle EDIT_ROADMAP/EDIT_FILE operation"""
        logger.info(f"Processing {edit_type} action")

        # Validate data
        if edit_type == "EDIT_ROADMAP":
            if (
                data is None
                or "previous" not in data
                or data["previous"] is None
                or "current" not in data
                or data["current"] is None
            ):
                logger.warning(
                    f"Skipping {edit_type} action as no previous or "
                    f"current data provided.",
                )
                return {"candidates": None, "profiling": None}
        elif edit_type == "EDIT_FILE":
            if "operation_data" not in data or data["operation_data"] is None:
                logger.warning(
                    f"Skipping {edit_type} action as no operation data "
                    f"provided.",
                )
                return {"candidates": None, "profiling": None}

        preference_message = await self.process_edit_action(
            user_edit=data,
            edit_type=edit_type,
        )
        if preference_message is None:
            logger.warning(
                "Skipping edit action as no message was provided or "
                "processed.",
            )
            return {"candidates": None, "profiling": None}

        results = await self.record_edit(
            uid=uid,
            preference_message=preference_message,
            reference_time=reference_time,
            session_id=session_id,
            action_message_id=action_message_id,
        )
        return results

    async def _handle_chat(
        self,
        uid: str,
        session_content,
        data: Any,
        reference_time: Optional[str],
        session_id: Optional[str],
        action_message_id: Optional[str],
        chat_type: str,
    ):
        """Handle START_CHAT/FOLLOWUP_CHAT/BREAK_CHAT operation"""
        logger.info(f"Processing {chat_type} action")

        user_query: Optional[str] = None
        if data is not None and "query" in data:
            query_value = data["query"]
            if isinstance(query_value, str):
                user_query = query_value

        preference_message = await self.process_chat_action(
            session_content=session_content,
            chat_type=chat_type,
            user_query=user_query,
            action_message_id=action_message_id,
        )

        if preference_message is None:
            logger.warning(
                "Skipping chat action as no message was provided or "
                "processed.",
            )
            return None

        results = await self.record_chat(
            uid=uid,
            preference_message=preference_message,
            reference_time=reference_time,
            session_id=session_id,
            action_message_id=action_message_id,
        )
        logger.info(f"record_chat results: {results}")
        return results

    async def _parallel_add_to_pools(
        self,
        uid: str,
        content: list,
        reference_time: Optional[str] = None,
        session_id: Optional[str] = None,
        action_type: str = "NORMAL",
        action_message_id: Optional[str] = None,
        memory_type: Optional[str] = None,
    ):
        """Parallel add content to candidate_pool and user_profiling_pool"""
        if content is None or len(content) == 0:
            return {f"{action_type} results": "No content provided, skipping!"}

        metadata = {}
        if session_id:
            metadata["session_id"] = session_id
        if reference_time:
            metadata["reference_time"] = reference_time
        if action_message_id:
            metadata["message_id"] = action_message_id
        metadata["action_type"] = action_type

        tasks = [
            self.add_memory_to_candidate_pool(
                uid=uid,
                content=content,
                metadata=metadata,
                memory_type=memory_type,
            ),
            self.add_memory_to_user_profiling_pool(
                uid=uid,
                content=content,
                metadata=metadata,
                memory_type=memory_type,
            ),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        candidate_result = (
            results[0]
            if not isinstance(results[0], Exception)
            else {"error": str(results[0])}
        )
        profiling_result = (
            results[1]
            if not isinstance(results[1], Exception)
            else {"error": str(results[1])}
        )

        return {"candidates": candidate_result, "profiling": profiling_result}

    async def record_collect_session(
        self,
        uid: str,
        session_content: list,
        reference_time: Optional[str] = None,
        memory_type: Optional[str] = None,
        session_id: Optional[str] = None,
        **_kwargs,
    ):
        """Optimized record_collect_session using parallel processing"""
        if session_content is None or len(session_content) == 0:
            return {
                "CollectSession results": (
                    "No session content provided, skipping collection!"
                ),
            }

        return await self._parallel_add_to_pools(
            uid=uid,
            content=session_content,
            reference_time=reference_time,
            session_id=session_id,
            action_type="SESSION",
            memory_type=memory_type,
        )

    async def record_uncollect_session(
        self,
        uid: str,
        session_id: Optional[str],
    ):
        """Optimized record_uncollect_session using background tasks"""
        if session_id is None:
            return {
                "UnCollectSession results": (
                    "No session id provided, skipping uncollecting session!"
                ),
            }

        filter_memories = await self.get_memory(
            uid=uid,
            filters={"session_id": session_id, "action_type": "SESSION"},
        )
        candidates = filter_memories["candidates"].get("results", [])
        profiling = filter_memories["profiling"].get("results", [])

        tasks = []

        # Reset candidate pool metadata
        if candidates:
            asyncio.create_task(
                self._safe_background_task(
                    self.candidate_pool.reset_metadata(
                        [c["id"] for c in candidates],
                    ),
                    f"reset_session_{session_id}_candidates",
                    uid,
                ),
            )

        # Delete records in profiling pool
        if profiling:
            delete_tasks = [
                self.user_profiling_pool.delete(p["id"]) for p in profiling
            ]
            tasks.extend(delete_tasks)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        return {
            "UnCollectSession results": (
                f"Session {session_id} has been uncollected successfully "
                f"from user profiling pool."
            ),
        }

    async def record_collect_tool(
        self,
        uid: str,
        tool_collection_content: list,
        reference_time: Optional[str] = None,
        memory_type: Optional[str] = None,
        session_id: Optional[str] = None,
        action_message_id: Optional[str] = None,
    ):
        """Optimized record_collect_tool using parallel processing"""
        if (
            tool_collection_content is None
            or len(tool_collection_content) == 0
        ):
            return {
                "CollectTool results": (
                    "No tool collection content provided, "
                    "skipping collection!"
                ),
            }
        return await self._parallel_add_to_pools(
            uid=uid,
            content=tool_collection_content,
            reference_time=reference_time,
            session_id=session_id,
            action_type="TOOL",
            action_message_id=action_message_id,
            memory_type=memory_type,
        )

    async def record_uncollect_tool(
        self,
        uid: str,
        session_id: Optional[str],
        action_message_id: str,
    ):
        """Optimized record_uncollect_tool using background tasks"""
        if not action_message_id:
            return {
                "UnCollectTool results": (
                    "No message ID provided. Skipping uncollect operation."
                ),
            }

        filter_dict = {"message_id": action_message_id, "action_type": "TOOL"}

        if session_id:
            filter_dict["session_id"] = session_id

        filter_memories = await self.get_memory(uid=uid, filters=filter_dict)
        candidates = filter_memories["candidates"].get("results", [])
        profiling = filter_memories["profiling"].get("results", [])

        tasks = []

        # Reset candidate pool metadata
        if candidates:
            asyncio.create_task(
                self._safe_background_task(
                    self.candidate_pool.reset_metadata(
                        [c["id"] for c in candidates],
                    ),
                    f"reset_tool_{action_message_id}_candidates",
                    uid,
                ),
            )

        # Delete records in profiling pool
        if profiling:
            delete_tasks = [
                self.user_profiling_pool.delete(p["id"]) for p in profiling
            ]
            tasks.extend(delete_tasks)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        return {
            "UnCollectTool results": (
                f"Tool message {action_message_id} was successfully "
                f"removed from the user profiling pool."
            ),
        }

    async def record_like_unlike(
        self,
        uid: str,
        content: list,
        reference_time: Optional[str] = None,
        memory_type: Optional[str] = None,
        session_id: Optional[str] = None,
        action_message_id: Optional[str] = None,
        action_type: str = "like",
    ):
        """Optimized record_like_unlike using parallel processing"""
        return await self._parallel_add_to_pools(
            uid=uid,
            content=content,
            reference_time=reference_time,
            session_id=session_id,
            action_type=action_type.upper(),
            action_message_id=action_message_id,
            memory_type=memory_type,
        )

    async def record_cancel_like_unlike(
        self,
        uid: str,
        session_id: Optional[str],
        action_message_id: str,
        action_type: str,
    ):
        """Optimized record_cancel_like_unlike using background tasks"""
        if action_message_id is None:
            return {
                f"Cancel {action_type.upper()} results": (
                    "No message ID provided, skipping cancel action."
                ),
            }

        filter_dict = {
            "message_id": action_message_id,
            "action_type": action_type.upper(),
        }

        if session_id:
            filter_dict["session_id"] = session_id

        filter_memories = await self.get_memory(uid=uid, filters=filter_dict)
        candidates = filter_memories["candidates"].get("results", [])
        profiling = filter_memories["profiling"].get("results", [])

        # Parallel delete operation
        tasks = []

        # Reset candidate pool metadata
        if candidates:
            asyncio.create_task(
                self._safe_background_task(
                    self.candidate_pool.reset_metadata(
                        [c["id"] for c in candidates],
                    ),
                    f"reset_{action_type}_{action_message_id}_candidates",
                    uid,
                ),
            )

        # Delete records in profiling pool
        if profiling:
            delete_tasks = [
                self.user_profiling_pool.delete(p["id"]) for p in profiling
            ]
            tasks.extend(delete_tasks)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        return {
            "Cancel results": (
                f"{action_type.capitalize()} action for message "
                f"{action_message_id} has been successfully canceled and "
                f"removed from user profiling pool."
            ),
        }

    async def record_edit(
        self,
        uid: str,
        preference_message: dict,
        reference_time: Optional[str] = None,
        memory_type: Optional[str] = None,
        session_id: Optional[str] = None,
        action_message_id: Optional[str] = None,
    ):
        """Optimized record_edit using parallel processing"""
        results = []

        for preference in preference_message.get("analysis_result", []):
            preference_type = preference.get("type")
            if not preference_type:
                continue

            message = [
                {"role": "user", "content": preference.get("user_preference")},
            ]

            if preference_type == "implicit":
                result = await self.add_memory(
                    uid,
                    content=message,
                    session_id=session_id,
                    metadata={"action_type": "EDIT"},
                    extract_facts=False,
                )
                results.append(result)
            elif preference_type == "explicit":
                result = await self._parallel_add_to_pools(
                    uid=uid,
                    content=message,
                    reference_time=reference_time,
                    session_id=session_id,
                    action_type="EDIT",
                    action_message_id=action_message_id,
                    memory_type=memory_type,
                )
                results.append(result)

            logger.info(
                f"record_EDIT_content called with: uid={uid}, "
                f"content={message}, reference_time={reference_time}, "
                f"session_id={session_id}, preference_type={preference_type}",
            )

        if not results:
            logger.info(
                "No preference is found in the message. Skipping record_edit.",
            )

        return results

    async def record_chat(
        self,
        uid: str,
        preference_message: dict,
        reference_time: Optional[str] = None,
        memory_type: Optional[str] = None,
        session_id: Optional[str] = None,
        action_message_id: Optional[str] = None,
    ):
        """Optimized record_chat using parallel processing"""
        preference_type = preference_message.get("type")
        logger.info(f"record_chat preference_type: {preference_type}")
        if preference_type == "irrelevant":
            return {
                "message": (
                    "No preference is found in the message. "
                    "Skipping record_chat."
                ),
            }

        message = [
            {
                "role": "user",
                "content": preference_message.get("user_preference"),
            },
        ]

        if preference_type == "implicit":
            result = await self.add_memory(
                uid,
                content=message,
                session_id=session_id,
                metadata={"action_type": "CHAT"},
                extract_facts=False,
            )
        elif preference_type == "explicit":
            result = await self._parallel_add_to_pools(
                uid=uid,
                content=message,
                reference_time=reference_time,
                session_id=session_id,
                action_type="CHAT",
                action_message_id=action_message_id,
                memory_type=memory_type,
            )

        logger.info(
            f"record_CHAT_content called with: uid={uid}, "
            f"content={message}, reference_time={reference_time}, "
            f"session_id={session_id}, preference_type={preference_type}",
        )

        return result

    async def check_collection_health(self, uid: Optional[str] = None):
        """
        Check the health of the Qdrant collection and provide diagnostic
        information.

        Args:
            uid (str, optional): User ID for logging purposes.
                Defaults to None.

        Returns:
            dict: Collection health information
        """
        try:
            # Get collection info
            collection_info = await asyncio.to_thread(
                self.candidate_pool.vector_store.col_info,
            )

            health_info = {
                "collection_name": (
                    self.candidate_pool.vector_store.collection_name
                ),
                "points_count": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
                "status": "healthy",
                "user_id": uid,
            }

            logger.info(
                f"Collection health check passed"
                f"{f' for user {uid}' if uid else ''}: {health_info}",
            )

            # Get collection info
            collection_info = await asyncio.to_thread(
                self.user_profiling_pool.vector_store.col_info,
            )

            health_info = {
                "collection_name": (
                    self.user_profiling_pool.vector_store.collection_name
                ),
                "points_count": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
                "status": "healthy",
                "user_id": uid,
            }

            logger.info(
                f"Collection health check passed"
                f"{f' for user {uid}' if uid else ''}: {health_info}",
            )

            # Get collection info
            collection_info = await asyncio.to_thread(
                self.user_info_pool.vector_store.col_info,
            )

            health_info = {
                "collection_name": (
                    self.user_info_pool.vector_store.collection_name
                ),
                "points_count": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
                "status": "healthy",
                "user_id": uid,
            }

            logger.info(
                f"Collection health check passed"
                f"{f' for user {uid}' if uid else ''}: {health_info}",
            )

            return health_info

        except Exception as e:
            logger.error(
                f"Collection health check failed"
                f"{f' for user {uid}' if uid else ''}: {e}",
            )
            return {
                "collection_name_candidate_pool": (
                    self.candidate_pool.vector_store.collection_name
                ),
                "collection_name_user_profiling_pool": (
                    self.user_profiling_pool.vector_store.collection_name
                ),
                "status": "unhealthy",
                "error": str(e),
                "user_id": uid,
            }

    async def reset_collection(self, uid: Optional[str] = None):
        """
        Manually reset the Qdrant collection to fix corruption issues.

        Args:
            uid (str, optional): User ID for logging purposes.
                Defaults to None.
        """
        try:
            logger.warning(
                f"Manually resetting Qdrant collection"
                f"{f' for user {uid}' if uid else ''}...",
            )
            await asyncio.to_thread(self.candidate_pool.vector_store.reset)
            await asyncio.to_thread(
                self.user_profiling_pool.vector_store.reset,
            )
            await asyncio.to_thread(self.user_info_pool.vector_store.reset)
            logger.info(
                f"Successfully reset Qdrant collection"
                f"{f' for user {uid}' if uid else ''}",
            )
            return {"message": "Collection reset successfully"}
        except Exception as e:
            logger.error(
                f"Failed to reset Qdrant collection"
                f"{f' for user {uid}' if uid else ''}: {e}",
            )
            raise ValueError(f"Failed to reset collection: {e}") from e

    async def process_collection_action(
        self,
        session_content: list,
        abstract_type: str = "one_step",
    ):
        """
        Abstracts a collection session into summarized messages using
        the specified abstraction method.
        Args:
            session_content (list): List of session messages to be
                processed.
            abstract_type (str, optional): Abstraction method. Options:
                "one_step", "multi_levels", "agent_levels",
                "subtask_levels". Defaults to "one_step".
        Returns:
            list: Abstracted messages.
        """
        if session_content is None:
            return []
        try:
            if (
                "message" in session_content[0]
                or "messages" in session_content[0]
            ):
                # meaning the session_content is not formatted correctly
                session_content = format_session_content(session_content)

            if abstract_type == "one_step":
                extracted_results = (
                    await (
                        self.candidate_pool.one_step_extract_CollectionSession(
                            session_content,
                        )
                    )
                )
            elif abstract_type in [
                "multi_levels",
                "agent_levels",
                "subtask_levels",
            ]:
                extracted_results = await self.candidate_pool.multi_levels_extract_CollectionSession(  # noqa: E501  # pylint: disable=line-too-long
                    session_content,
                    abstract_type=abstract_type,
                )
            else:
                raise ValueError(
                    f"Invalid abstract method: {abstract_type}",
                )
            logger.info(f"Extracted results: {extracted_results}")
            messages = process_extracted_workflows_from_session_content_under_collection_action(  # noqa: E501  # pylint: disable=line-too-long
                extracted_results,
            )
            return messages
        except Exception as e:
            logger.error(f"Error in abstract CollectionSession: {str(e)}")
            raise ValueError(
                f"Error in process CollectionSession: {str(e)}",
            ) from e

    async def process_collection_tool_action(
        self,
        session_content: list,
        action_message_id: Optional[str] = None,
    ):
        """
        Generate a user message summarizing a preferred tool usage process
        within a session.
        Args:
            session_content (list): List of session messages.
            action_message_id (Optional[str]): The message ID corresponding
                to the tool usage.
        Returns:
            list: A list containing a single user message summarizing the
                preferred tool usage process.
        """
        messages = []
        if action_message_id is None:
            logger.warning(
                "action_message_id is None in process_collection_tool_action",
            )
            return messages

        tool_message = None
        for message in session_content:
            if message["id"] == action_message_id:
                tool_message = message
                break

        if tool_message is None:
            logger.warning(
                f"Could not find tool message with id: {action_message_id}",
            )
            return messages

        summary = await self.candidate_pool.get_summary(
            session_content=session_content,
        )

        if summary is None or summary.get("task") == "Unknown Task Type":
            logger.warning(
                f"Could not find task summary for session content: "
                f"{session_content}",
            )
            return messages

        task_content = summary.get(
            "task",
            session_content[0]["message"]["content"],
        )
        messages = [
            {
                "role": "user",
                "content": (
                    f"I prefer the following tool usage process and "
                    f"prefer to use the tool: "
                    f'{tool_message["message"]["tool_name"]} when solving '
                    f"the task: "
                    f"#task:"
                    f"{task_content}"
                    f"\n"
                    f"#tool_use_results:"
                    f'{tool_message["message"]["content"]}'
                ),
            },
        ]

        logger.info(f"Generated tool usage summary message: {messages}")
        return messages

    async def process_like_unlike_message_action(
        self,
        session_content: list,
        action_message_id: str,
        feedback_type: str,  # "like" or "dislike"
    ):
        """
        Generate a user feedback message for a specific session message,
        supporting both 'like' and 'unlike' actions.
        Args:
            session_content (list): List of session messages.
            action_message_id (str): The ID of the message to provide
                feedback on.
            feedback_type (str): Feedback type, either "like" or "dislike".
        Returns:
            list: A list containing a single user feedback message.
        """
        messages = []
        if action_message_id is None:
            logger.warning(
                f"action_message_id is None in "
                f"process_session_content_under_{feedback_type}_action",
            )
            return messages

        target_message = None
        for message in session_content:
            if message["id"] == uuid.UUID(action_message_id):
                target_message = message
                break

        if target_message is None:
            logger.warning(
                f"Could not find message with id: {action_message_id}",
            )
            return messages

        summary = await self.candidate_pool.get_summary(
            session_content=session_content,
        )

        if summary is None or summary.get("task") == "Unknown Task Type":
            logger.warning(
                f"Could not find task summary for session content: "
                f"{session_content}",
            )
            return messages

        message_type = target_message["message"].get("type")
        if (
            message_type == "tool_call"
            or "tool_name" in target_message["message"]
        ):
            task_text = summary.get(
                "task",
                session_content[0]["message"]["content"],
            )
            tool_name = target_message["message"].get(
                "tool_name",
                "UnknownTool",
            )
            tool_result = target_message["message"].get("content", "")

            if feedback_type == "like":
                content = (
                    f"I appreciate the following tool usage process and "
                    f"prefer to use the tool: {tool_name} "
                    f"when solving the task: #task:{task_text}\n"
                    f"#tool_use_results:{tool_result}"
                )
            elif feedback_type == "dislike":
                content = (
                    f"I do not prefer the following tool usage process and "
                    f"would avoid using the tool: {tool_name} "
                    f"when solving the task: #task:{task_text}\n"
                    f"#tool_use_results:{tool_result}"
                )
            else:
                raise ValueError(
                    f"Invalid feedback_type: {feedback_type}, only 'like' "
                    f"or 'dislike' are supported",
                )

            messages = [{"role": "user", "content": content}]
        else:
            messages = await self.candidate_pool.extract_like_unlike_message(
                message=target_message,
                task_summary=summary,
                message_type=feedback_type,
            )

        logger.info(f"messages: {messages}")
        return messages

    async def process_edit_action(
        self,
        user_edit: Any,
        edit_type: str,
    ) -> dict:
        """
        Extract user edit intent information based on the edit type.

        Args:
            user_edit (Any): The user edit data. For "EditRoadMap", it
                should be a dict; for "EditFile", it should be a string.
            edit_type (str): The type of edit action, either "EditRoadMap"
                or "EditFile".

        Returns:
            dict: The extracted user edit intent results. Returns an empty
                dict if extraction fails or input is invalid.
        """
        # breakpoint()
        try:
            extracted_results = {}
            if edit_type == "EDIT_ROADMAP":
                if not isinstance(user_edit, dict):
                    logger.warning(f"user_edit is not a dict: {user_edit}")
                else:
                    extracted_results = (
                        await self.candidate_pool.extract_user_edit_intent(
                            user_edit=user_edit,
                            edit_type=edit_type,
                        )
                    )
            elif edit_type == "EDIT_FILE":
                if not isinstance(user_edit, dict):
                    logger.warning(f"user_edit is not a dict: {user_edit}")
                else:
                    operation_data = user_edit["operation_data"]
                    if isinstance(operation_data, str):
                        user_edit["operation_data"] = {
                            "content": operation_data,
                        }
                    elif isinstance(operation_data, list):
                        user_edit["operation_data"] = {
                            "content": "\n".join(operation_data),
                        }
                    elif not isinstance(operation_data, dict):
                        logger.warning(
                            f"operation_data is not a dict or a string or "
                            f"a list: {operation_data}",
                        )
                        return extracted_results

                    extracted_results = (
                        await self.candidate_pool.extract_user_edit_intent(
                            user_edit=user_edit,
                            edit_type=edit_type,
                        )
                    )
            if extracted_results is None:
                extracted_results = {}
            return extracted_results
        except Exception as e:
            logger.error(f"Error in abstract {edit_type}: {str(e)}")
            raise ValueError(f"Error in process {edit_type}: {str(e)}") from e

    async def process_chat_action(
        self,
        session_content: list,
        chat_type: str,
        user_query: Optional[str] = None,
        action_message_id: Optional[str] = None,
    ) -> dict:
        """
        Extract user chat intent information based on the chat type and
        the specified action message ID.

        Args:
            session_content (list): The list of session messages, each as
                a dict containing message details.
            chat_type (str): The type of chat action, e.g., "StartChat",
                "BreakChat", "FollowupChat".
            user_query (str, optional): The user query for the chat
                action.
            action_message_id (Optional[str]): The message ID for which
                to extract the chat intent.

        Returns:
            dict: The extracted user chat intent results. Returns an empty
                dict if extraction fails or input is invalid.
        """
        try:
            extracted_results = {}

            if user_query is None:
                logger.warning(
                    f"user_query is None in "
                    f"process_chat_action_under_{chat_type}_action",
                )
                if action_message_id is None:
                    logger.warning(
                        f"action_message_id is None in "
                        f"process_chat_action_under_{chat_type}_action",
                    )
                    return extracted_results

                target_message = None
                for message in session_content:
                    if message["id"] == action_message_id:
                        target_message = message
                        break

                if target_message is None:
                    logger.warning(
                        f"Could not find message with id: {action_message_id}",
                    )
                    return extracted_results

                whole_contents = []
                for message_obj in session_content:
                    message = message_obj["message"]
                    name = (
                        message["name"] if message["name"] else message["role"]
                    )
                    content = message["content"]
                    whole_contents.append(f"{name}: {content}")
                whole_contents = "\n".join(whole_contents)
                name_or_role = (
                    target_message["message"]["name"]
                    if target_message["message"]["name"]
                    else target_message["message"]["role"]
                )
                chat_message = (
                    f"{name_or_role}: "
                    f"{target_message['message']['content']}"
                )
            else:
                whole_contents = []
                for message_obj in session_content:
                    message = message_obj["message"]
                    name = (
                        message["name"] if message["name"] else message["role"]
                    )
                    content = message["content"]
                    whole_contents.append(f"{name}: {content}")
                if not whole_contents:
                    whole_contents.append(f"user: {user_query}")
                whole_contents = "\n".join(whole_contents)
                chat_message = f"user: {user_query}"

            extracted_results = await self.candidate_pool.extract_chat_intent(
                session_content=whole_contents,
                chat_type=chat_type,
                chat_message=chat_message,
            )
            if extracted_results is None:
                extracted_results = {}
            return extracted_results

        except Exception as e:
            logger.error(f"Error in abstract {chat_type}: {str(e)}")
            raise ValueError(f"Error in process {chat_type}: {str(e)}") from e

    async def _safe_background_task(
        self,
        coro,
        task_name: str,
        uid: str = None,
    ):
        """safe background task"""
        try:
            await coro
            logger.info(
                f"Background task {task_name} completed successfully"
                f"{f' for user {uid}' if uid else ''}",
            )
        except Exception as e:
            logger.error(
                f"Background task {task_name} failed"
                f"{f' for user {uid}' if uid else ''}: {e}",
            )

    def _is_qdrant_corruption_error(self, error: Exception) -> bool:
        """check if the Qdrant database corruption"""
        error_str = str(error).lower()
        return (
            "operands could not be broadcast together with shapes" in error_str
            or ("index" in error_str and "out of bounds" in error_str)
        )

    async def _reset_all_collections(self, uid: str):
        """restart all collections"""
        try:
            await asyncio.gather(
                asyncio.to_thread(self.candidate_pool.vector_store.reset),
                asyncio.to_thread(self.user_profiling_pool.vector_store.reset),
                asyncio.to_thread(self.user_info_pool.vector_store.reset),
                return_exceptions=True,
            )
            logger.info(f"Successfully reset all collections for user {uid}")
        except Exception as e:
            logger.error(f"Failed to reset collections for user {uid}: {e}")
            raise

    async def _handle_qdrant_corruption(
        self,
        uid: str,
        operation_func,
        *args,
        **kwargs,
    ):
        """Unified retry mechanism for handling Qdrant corruption errors"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                return await operation_func(*args, **kwargs)
            except ValueError as e:
                if (
                    self._is_qdrant_corruption_error(e)
                    and attempt < max_retries - 1
                ):
                    logger.warning(
                        f"Qdrant corruption detected (attempt "
                        f"{attempt + 1}) for user {uid}: {e}",
                    )
                    await self._reset_all_collections(uid)
                    continue
                if self._is_qdrant_corruption_error(e):
                    raise ValueError(
                        f"Qdrant collection corruption detected and reset "
                        f"failed after {max_retries} attempts. "
                        f"Original error: {e}",
                    ) from e
                raise

    async def _safely_resolve_coroutines(self, data: dict) -> dict:
        if not isinstance(data, dict):
            return data

        result = deepcopy(data)
        if "results" in result and hasattr(result["results"], "__await__"):
            logger.warning("Found coroutine in results, awaiting...")
            result["results"] = await result["results"]

        return result
