# -*- coding: utf-8 -*-
from games.game_werewolves import utils


def test_majority_vote() -> None:
    """Test majority vote logic"""
    votes = ["Player1", "Player1", "Player2"]
    result, _ = utils.majority_vote(votes)
    assert result == "Player1"


def test_names_to_str_single() -> None:
    """Test single name formatting"""
    assert utils.names_to_str(["Player1"]) == "Player1"


def test_players_role_mapping() -> None:
    """Test role mapping correctness"""
    players = utils.Players()
    mock_agent = utils.EchoAgent()
    mock_agent.name = "Player1"

    players.add_player(mock_agent, "werewolf")
    assert players.name_to_role["Player1"] == "werewolf"
    assert len(players.werewolves) == 1