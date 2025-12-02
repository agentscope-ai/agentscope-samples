# -*- coding: utf-8 -*-
import uuid
from typing import List, Optional, Tuple, Union, Dict, Any

from loguru import logger

from alias.server.cache.state_cache import StateCache
from alias.server.dao.state_dao import StateDao
from alias.server.exceptions.service import StateNotFoundError
from alias.server.models.state import State
from alias.server.schemas.common import PaginationParams
from alias.server.services.base_service import BaseService
from alias.server.utils.timestamp import get_current_time


class StateService(BaseService[State]):
    _model_cls = State
    _dao_cls = StateDao
    _cache_cls = StateCache

    async def _validate_exists(self, instance_id: uuid.UUID) -> None:
        state = await self.get(instance_id)
        if not state:
            raise StateNotFoundError(extra_info={"state_id": instance_id})

    async def _validate_update(
        self,
        instance_id: uuid.UUID,
        obj_in: Union[Dict[str, Any], State],
    ) -> None:
        state = await self.get(instance_id)
        if not state:
            raise StateNotFoundError(extra_info={"state_id": instance_id})

    async def _validate_delete(self, instance_id: uuid.UUID) -> None:
        state = await self.get(instance_id)
        if not state:
            raise StateNotFoundError(extra_info={"state_id": instance_id})

    async def list_states(
        self,
        user_id: uuid.UUID,
        pagination: Optional[PaginationParams] = None,
    ) -> Tuple[int, List[State]]:
        filters = {"user_id": user_id}
        total = await self.count_by_fields(filters=filters)
        states = await self.paginate(
            pagination=pagination,
            filters=filters,
        )
        return total, states

    async def create_state(
        self,
        conversation_id: uuid.UUID,
        content: str,
    ) -> State:
        state = await self.get_state(conversation_id)
        if state:
            logger.info(
                f"Created state through update state: {conversation_id}",
            )
            return await self.update_state(
                conversation_id=conversation_id,
                content=content,
            )

        state = State(
            conversation_id=conversation_id,
            content=content,
        )
        state = await self.create(state)
        await self.set_cache(conversation_id, state)
        logger.info(f"Created state: {state.id}")
        return state

    async def get_state(self, conversation_id: uuid.UUID) -> Optional[State]:
        state = await self.get_cache(conversation_id)
        if not state:
            state = await self.get_last_by_field(
                "conversation_id",
                conversation_id,
            )
            if state:
                await self.set_cache(conversation_id, state)
        return state

    async def update_state(
        self,
        conversation_id: uuid.UUID,
        content: str,
    ) -> State:
        state = await self.get_state(conversation_id)
        if not state:
            raise StateNotFoundError(
                extra_info={"conversation_id": conversation_id},
            )
        state.content = content
        state.update_time = get_current_time()
        await self.set_cache(conversation_id, state)
        return await self.update(state.id, state)

    async def delete_state(self, conversation_id: uuid.UUID) -> None:
        state = await self.get_state(conversation_id=conversation_id)
        if state:
            await self.delete(state.id)
            await self.clear_cache(conversation_id)
