# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
import uuid
import copy
import os
from collections import OrderedDict
from pydantic import Field


from agentscope.plan import SubTask
from agentscope.message import Msg, TextBlock
from agentscope._utils._common import _get_timestamp
from alias.agent.agents.dr_agent_utils.deep_research_worker_response import (
    DRWorkerResponse,
    HypothesisResponse,
)

# Load built-in prompts
_PROMPT_PATH = os.path.join(
    os.path.dirname(__file__),
    "built_in_prompt",
    "prompt_final_report.md",
)
with open(_PROMPT_PATH, "r", encoding="utf-8") as _f:
    PROMPT_FINAL_REPORT = _f.read()


class DRTaskBase(SubTask, ABC):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    # metadata can be used to store all add
    metadata: OrderedDict = Field(default_factory=OrderedDict)

    # overwrite the SubTask class to provide default values
    name: str = Field(
        description=(
            "The subtask name, should be concise, descriptive and not"
            "exceed 10 words."
        ),
        default_factory=lambda: "Deep_Research_Task_" + str(uuid.uuid4())[:8],
    )
    expected_outcome: str = Field(
        description=(
            "The expected outcome of the subtask, which should be specific, "
            "concrete and measurable."
        ),
        default="",
    )

    @abstractmethod
    def task_to_init_msg(self) -> Msg:
        """
        Generate a message with a description of
        current subtask, and instructions for agent to do
        """

    @abstractmethod
    def get_worker_response_model(self) -> type[DRWorkerResponse]:
        """Return the response model class"""

    @abstractmethod
    def build_children_nodes(
        self,
        structure_response: DRWorkerResponse | dict,
    ) -> list["DRTaskBase"]:
        """
        Process worker response
        - must match the type from get_worker_response_model
        """

    @classmethod
    @abstractmethod
    def from_user_query(cls, user_query: str) -> "DRTaskBase":
        """
        Build a subtask instance from a user query
        """

    @abstractmethod
    def build_final_report_system_msg(self, theme: str) -> Msg:
        """
        Build a final report instruction message
        """


# ================= general deep research task =================


class BasicJudge(DRWorkerResponse):
    """
    Model for structured follow-up decompose judging output in deep research.
    """

    remain_knowledge_gaps: str = Field(
        description=(
            "Revise the knowledge gaps in the current (sub)task. "
            "Mark the gaps with sufficient information as `- [x]`, "
            "mark the unfilled gaps with `- []`."
        ),
        default="",
    )


class BasicTask(DRTaskBase):
    def task_to_init_msg(self) -> Msg:
        """
        Generate a message with a description of
        current subtask, and instructions for agent to do
        """
        prompt = (
            "## Background\n"
            f"Current time: {_get_timestamp()}"
            "## Current Task or Knowledge Gaps\n"
            f"{self.description}\n"
        )
        return Msg(
            name="user",
            content=[TextBlock(type="text", text=prompt)],
            role="user",
        )

    def get_worker_response_model(self) -> type[BasicJudge]:
        """Return the response model class"""
        return BasicJudge

    def build_children_nodes(
        self,
        structure_response: BasicJudge | dict,
    ) -> list["DRTaskBase"]:
        if isinstance(structure_response, dict):
            structure_response = BasicJudge(**structure_response)

        self.metadata[self.id] = {
            "current_task": self.description,
        }

        decomposed_executables = []
        for subtask in structure_response.follow_ups:
            decomposed_executables.append(
                BasicTask(
                    description=subtask,
                    metadata=copy.deepcopy(self.metadata),
                ),
            )

        return decomposed_executables

    @classmethod
    def from_user_query(cls, user_query: str) -> "BasicTask":
        return cls(description=user_query)

    def build_final_report_system_msg(self, theme: str) -> Msg:
        sys_prompt = (
            "You will be given a series `task and generated report`. "
            "You task to generate a comprehensive report based on this "
            f"given information, with the theme on {theme}."
            "The report should be in Markdown format and try to keep as much "
            "information, references (e.g. url) and extended thoughts "
            "as possible."
        )
        return Msg(
            name="system",
            content=[TextBlock(type="text", text=sys_prompt)],
            role="system",
        )


# ================= hypothesis driven deep research task =================


class HypothesisDrivenTask(DRTaskBase):
    evidences: list[str] = Field(
        description=("List of evidences for this current task(hypothesis)"),
        default_factory=list,
    )

    def task_to_init_msg(self) -> Msg:
        """
        Generate a message with a description of
        current hypothesis, and ask the agent to verify it
        """

        prompt = (
            "## Background\n"
            f"Current time: {_get_timestamp()}"
            "## Hypothesis/Task to Investigate\n"
            f"{self.description}\n"
            "## Your Task\n"
            "Investigate this Task by:\n"
            "1. Gathering relevant evidence and information\n"
            "2. Analyzing the credibility and relevance of sources\n"
            "3. Identifying contradictions, or gaps in the evidence\n"
            "When you have gathered sufficient information, "
            "provide your evaluation and identify specific "
            "sub-hypotheses(follow-ups) that need further investigation.\n"
        )
        return Msg(
            name="user",
            content=[TextBlock(type="text", text=prompt)],
            role="user",
        )

    def get_worker_response_model(self) -> type[HypothesisResponse]:
        """
        Get hypothesis-driven evaluation response model
        """
        return HypothesisResponse

    def build_children_nodes(
        self,
        structure_response: DRWorkerResponse | dict,
    ) -> list["DRTaskBase"]:
        """
        Construct decomposed executable list based on hypothesis eval results.
        """
        if isinstance(structure_response, dict):
            structure_response = HypothesisResponse.model_validate(
                structure_response,
            )

        # Store evaluation results in metadata
        self.metadata[self.id] = {
            "current_task": self.description,
            "evidences": self.evidences,
            "hypotheses_eval": structure_response.current_hypothesis_eval,
        }

        decomposed_executables = []

        # Generate child tasks from follow_ups (sub-hypotheses)
        for sub_hyp in structure_response.follow_ups:
            child_task = HypothesisDrivenTask(
                description=f"Investigate sub-hypotheses of "
                f"{self.description} - {sub_hyp}",
                evidences=[],
                metadata=copy.deepcopy(self.metadata),
            )
            decomposed_executables.append(child_task)

        return decomposed_executables

    @classmethod
    def from_user_query(cls, user_query: str) -> "HypothesisDrivenTask":
        """
        Construct hypothesis-driven task from user query
        """
        return cls(description=user_query)

    def build_final_report_system_msg(self, theme: str) -> Msg:
        """
        Build system message for generating hypothesis-driven final report.
        Integrates current node information via prompt template.
        """
        sys_prompt = PROMPT_FINAL_REPORT.format(original_task=theme)

        return Msg(
            name="system",
            content=[TextBlock(type="text", text=sys_prompt)],
            role="system",
        )


DEEPRESEARCH_TASKS_TYPES = {
    "general": BasicTask,
    "finance": HypothesisDrivenTask,
}
