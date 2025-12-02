# -*- coding: utf-8 -*-

import uuid

from alias.server.dao.base_dao import BaseDAO
from alias.server.models.user import User
from alias.server.utils.request_context import request_context_var
from alias.server.utils.timestamp import get_current_time


class UserDao(BaseDAO[User]):
    _model_class = User

    async def update_last_login_info(
        self,
        user_id: uuid.UUID,
    ) -> User:
        """Update the last login info of the user."""
        user = await self.get(user_id)
        ip_address = request_context_var.get().ip_address
        update_data = {}
        if ip_address:
            update_data["last_login_ip"] = ip_address
        update_data["last_login_time"] = get_current_time()
        user = await self.update(user_id, update_data)
        return user
