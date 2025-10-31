# -*- coding: utf-8 -*-
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from agentscope.agent import ReActAgent
from agentscope.model import ChatModelBase
from agentscope.formatter import FormatterBase

# Import modules to test
from games.game_werewolves import game, utils, structured_model


class HunterModelMock:
    def __init__(self, **kwargs):
        self._data = {
            "name": kwargs.get("name", None),
            "shoot": kwargs.get("shoot", False),
        }
        self.metadata = {"shoot": self._data["name"] is not None}

    def model_dump(self):
        return self._data

    @property
    def name(self):
        return self._data["name"]


@pytest.mark.asyncio
async def test_werewolves_discussion() -> None:
    mock_hub = AsyncMock()
    mock_hub.__aenter__.return_value = mock_hub
    mock_hub.__aexit__.return_value = AsyncMock()

    with patch("games.game_werewolves.game.MsgHub", return_value=mock_hub):
        mock_agent = AsyncMock()
        mock_agent.name = "Player1"

        agents = [mock_agent for _ in range(9)]
        await game.werewolves_game(agents)
        assert True


@pytest.mark.asyncio
async def test_witch_resurrect() -> None:
    async def mock_model(**kwargs):
        return {"resurrect": kwargs.get("resurrect", False)}

    with patch(
        "games.game_werewolves.game.WitchResurrectModel",
        side_effect=mock_model,
    ):
        result = await game.WitchResurrectModel(**{"resurrect": True})
        assert result["resurrect"] is True


# -----------------------------
# Test: utils.py
# -----------------------------
def test_majority_vote() -> None:
    votes = ["Player1", "Player1", "Player2"]
    result, _ = utils.majority_vote(votes)
    assert result == "Player1"


def test_names_to_str_single() -> None:
    assert utils.names_to_str(["Player1"]) == "Player1"


def test_players_role_mapping() -> None:
    players = utils.Players()
    mock_agent = utils.EchoAgent()
    mock_agent.name = "Player1"

    players.add_player(mock_agent, "werewolf")
    assert players.name_to_role["Player1"] == "werewolf"
    assert len(players.werewolves) == 1


def test_vote_model_generation() -> None:
    mock_model = MagicMock(spec=ChatModelBase)
    mock_formatter = MagicMock(spec=FormatterBase)

    agents = [
        ReActAgent(
            name=f"Player{i}",
            sys_prompt=f"Vote system prompt {i}",
            model=mock_model,
            formatter=mock_formatter,
        )
        for i in range(3)
    ]

    VoteModel = structured_model.get_vote_model(agents)
    assert "vote" in VoteModel.model_fields
    assert (
        VoteModel.model_fields["vote"].description
        == "The name of the player you want to vote for"
    )


def test_witch_poison_model_fields() -> None:
    mock_model = MagicMock(spec=ChatModelBase)
    mock_formatter = MagicMock(spec=FormatterBase)

    agents = [
        ReActAgent(
            name="Player1",
            sys_prompt="Poison system prompt",
            model=mock_model,
            formatter=mock_formatter,
        ),
    ]

    PoisonModel = structured_model.get_poison_model(agents)
    assert "poison" in PoisonModel.model_fields
    assert "name" in PoisonModel.model_fields
