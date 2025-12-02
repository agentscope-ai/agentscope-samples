# -*- coding: utf-8 -*-
from typing import Literal
from pydantic import BaseModel, Field


class DRWorkerResponse(BaseModel):
    current_status: Literal[
        "todo",
        "in_progress",
        "done",
        "abandoned",
    ] = Field(
        description="The state of the current task.",
        default="todo",
    )
    current_task_summary: str = Field(
        description="Description of the status of current task status.",
        default="",
    )
    follow_ups: list[str] = Field(
        description=(
            "Actionable description of the follow-up sub-tasks to obtain "
            "more information, focused research question/direction. "
            "Always try to add AT LEAST 3 subtasks that can help to analyze "
            "the question deeper and generate more comprehensive report."
        ),
    )


class HypothesisResponse(DRWorkerResponse):
    current_hypothesis_eval: float = Field(
        description=(
            "Generate evaluation(confidence score) for the current hypothesis."
            "The value should be a confidence score between 0 and 1."
        ),
    )

    current_status: Literal[
        "todo",
        "in_progress",
        "done",
        "abandoned",
    ] = Field(
        description="The state of the current hypothesis.",
    )

    follow_ups: list[str] = Field(
        description=(
            "Statements of the follow-up sub-hypotheses. "
            "Try to add 2-4 sub-hypotheses for deeper investigation."
        ),
    )
