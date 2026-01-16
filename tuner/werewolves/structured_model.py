# -*- coding: utf-8 -*-
# flake8: noqa: E501
"""The structured output models used in the werewolf game."""
from typing import Literal

from pydantic import BaseModel, Field
from agentscope.agent import AgentBase


class DiscussionModel(BaseModel):
    """The output format for discussion."""

    reach_agreement: bool = Field(
        description="Whether you have reached an agreement or not",
    )


class PublicDiscussionModel(BaseModel):
    """The output format for public discussion with private reasoning.

    This model separates private reasoning from public statements to prevent
    accidental information leakage (e.g., werewolves revealing their identity).
    """

    reasoning: str = Field(
        description=(
            "Your PRIVATE reasoning and analysis. This will NOT be shown to "
            "other players. You can freely think about your strategy, analyze "
            "other players' behaviors, and plan your next move here. "
            "If you are a werewolf, you can think about how to hide your identity. "
            "If you are a villager, you can analyze who might be the werewolf."
        ),
    )

    statement: str = Field(
        description=(
            "Your PUBLIC statement to all players. This WILL be visible to everyone. "
            "Be careful not to reveal sensitive information (e.g., your true role if "
            "you are a werewolf). "
            "Your statement should be strategic and help your team win."
        ),
    )


def get_vote_model(agents: list[AgentBase]) -> type[BaseModel]:
    """Get the vote model by player names."""

    class VoteModel(BaseModel):
        """The vote output format."""

        vote: Literal[tuple(_.name for _ in agents)] = Field(  # type: ignore
            description="The name of the player you want to vote for",
        )

    return VoteModel


class WitchResurrectModel(BaseModel):
    """The output format for witch resurrect action."""

    resurrect: bool = Field(
        description="Whether you want to resurrect the player",
    )


def get_poison_model(agents: list[AgentBase]) -> type[BaseModel]:
    """Get the poison model by player names."""

    class WitchPoisonModel(BaseModel):
        """The output format for witch poison action."""

        poison: bool = Field(
            description="Do you want to use the poison potion",
        )
        name: Literal[  # type: ignore
            tuple(_.name for _ in agents)
        ] | None = Field(
            description="The name of the player you want to poison, if you "
            "don't want to poison anyone, just leave it empty",
            default=None,
        )

    return WitchPoisonModel


def get_seer_model(agents: list[AgentBase]) -> type[BaseModel]:
    """Get the seer model by player names."""

    class SeerModel(BaseModel):
        """The output format for seer action."""

        name: Literal[tuple(_.name for _ in agents)] = Field(  # type: ignore
            description="The name of the player you want to check",
        )

    return SeerModel
