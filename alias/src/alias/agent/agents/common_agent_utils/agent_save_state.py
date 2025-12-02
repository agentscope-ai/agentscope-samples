# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field


class AliasAgentStates(BaseModel):
    agent_states: dict[str, dict] = Field(
        default_factory=dict,
        description="a dictionary of `agent_name` to `agent state` (as dict) ",
    )
