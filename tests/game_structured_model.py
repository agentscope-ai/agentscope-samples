# tests/game_structured_model.py
# -*- coding: utf-8 -*-
from games.game_werewolves import structured_model
from agentscope.agent import ReActAgent
from agentscope.model import ChatModelBase
from agentscope.formatter import FormatterBase
from unittest.mock import MagicMock


def test_vote_model_generation() -> None:
    """Test VoteModel generates correct fields"""
    # Create mock dependencies
    mock_model = MagicMock(spec=ChatModelBase)
    mock_formatter = MagicMock(spec=FormatterBase)

    # Create agents with required arguments
    agents = [
        ReActAgent(
            name=f"Player{i}",
            sys_prompt=f"Vote system prompt {i}",
            model=mock_model,
            formatter=mock_formatter
        ) for i in range(3)
    ]

    VoteModel = structured_model.get_vote_model(agents)
    assert "vote" in VoteModel.model_fields
    assert (
        VoteModel.model_fields["vote"].description
        == "The name of the player you want to vote for"
    )


def test_witch_poison_model_fields() -> None:
    """Test WitchPoisonModel fields"""
    # Create mock dependencies
    mock_model = MagicMock(spec=ChatModelBase)
    mock_formatter = MagicMock(spec=FormatterBase)

    # Create agent with required arguments
    agents = [
        ReActAgent(
            name="Player1",
            sys_prompt="Poison system prompt",
            model=mock_model,
            formatter=mock_formatter
        )
    ]

    PoisonModel = structured_model.get_poison_model(agents)
    assert "poison" in PoisonModel.model_fields
    assert "name" in PoisonModel.model_fields