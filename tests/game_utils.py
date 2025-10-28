# -*- coding: utf-8 -*-
import numpy as np
from ..games.game_werewolves import utils


def test_majority_vote() -> None:
    """验证多数投票逻辑"""
    votes = ["Player1", "Player1", "Player2"]
    result, _ = utils.majority_vote(votes)
    assert result == "Player1"


def test_names_to_str_single() -> None:
    """验证单个名称格式化"""
    assert utils.names_to_str(["Player1"]) == "Player1"


def test_names_to_str_multiple() -> None:
    """验证多个名称格式化"""
    assert utils.names_to_str(["Player1", "Player2"]) == "Player1 and Player2"


def test_players_role_mapping() -> None:
    """验证角色映射正确性"""
    players = utils.Players()
    mock_agent = utils.EchoAgent()
    mock_agent.name = "Player1"

    players.add_player(mock_agent, "werewolf")
    assert players.name_to_role["Player1"] == "werewolf"
    assert len(players.werewolves) == 1
