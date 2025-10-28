# -*- coding: utf-8 -*-
import os
import pytest
from agentscope.agent import ReActAgent
from games.game_werewolves import main


def test_get_official_agents() -> None:
    """验证玩家初始化"""
    agent = main.get_official_agents("Player1")
    assert isinstance(agent, ReActAgent)
    assert agent.name == "Player1"


def test_get_official_agents_with_custom_prompt() -> None:
    """验证玩家提示词包含角色说明"""
    agent = main.get_official_agents("Player2")
    assert "werewolf" in agent.sys_prompt.lower()
    assert "villager" in agent.sys_prompt.lower()
