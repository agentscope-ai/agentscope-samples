# -*- coding: utf-8 -*-
from ..games.game_werewolves import structured_model
from agentscope.agent import ReActAgent

def test_vote_model_generation() -> None:
    """验证VoteModel生成正确字段"""
    agents = [ReActAgent(name=f"Player{i}") for i in range(3)]
    VoteModel = structured_model.get_vote_model(agents)
    assert "vote" in VoteModel.model_fields
    assert VoteModel.model_fields["vote"].description == "The name of the player you want to vote for"

def test_witch_poison_model_fields() -> None:
    """验证WitchPoisonModel字段"""
    agents = [ReActAgent(name="Player1")]
    PoisonModel = structured_model.get_poison_model(agents)
    assert "poison" in PoisonModel.model_fields
    assert "name" in PoisonModel.model_fields