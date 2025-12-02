# -*- coding: utf-8 -*-
# pylint: disable=E0213
"""
Data structures about the roadmap for complicated tasks
"""
from datetime import datetime
from typing import List, Literal, Tuple, Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator


def get_current_time_message() -> str:
    """
    Returns the current time as a formatted string.

    Returns:
        str: The current time formatted as 'YYYY-MM-DD HH:MM:SS'.
    """
    return f"Current time is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


class Update(BaseModel):
    """Represents an update record from a worker during task execution.

    This class tracks progress updates from workers as they work on subtasks,
    including status changes, progress summaries, and execution details.

    Attributes:
        reason_for_status (str): Explanation for the current status.
        task_done (bool): Whether the task has been completed.
        subtask_progress_summary (str): Summary of progress made.
        next_step (str): Description of planned next actions.
        worker (str): Identifier of the worker providing the update.
        attempt_idx (int): Index of the current attempt.
    """

    reason_for_status: str
    task_done: bool
    subtask_progress_summary: str
    next_step: str
    worker: str
    attempt_idx: int

    @field_validator(
        "subtask_progress_summary",
        "reason_for_status",
        "next_step",
        "worker",
        mode="before",
    )
    def _stringify(cls, v: Any) -> str:
        """ensure the attributes are string"""
        if v is None:
            return ""
        return str(v)


class WorkerInfo(BaseModel):
    """Contains information about a worker agent assigned to a subtask.

    This class stores metadata about worker agents, including their
    capabilities, creation type, and configuration details.

    Attributes:
        worker_name (str):
            Name identifier of the worker.
        status (str):
            Current status of the worker.
        create_type (Literal["built-in", "dynamic-built"]):
            How the worker was created.
        description (str):
            Description of the worker's purpose and capabilities.
        tool_lists (List[str]):
            List of tools available to this worker.
        sys_prompt (str):
            System prompt used to configure the worker.
    """

    worker_name: str = ""
    status: str = ""
    create_type: Literal["built-in", "dynamic-built"] = "dynamic-built"
    description: str = ""
    # for dynamically create worker agents
    tool_lists: List[str] = Field(default_factory=list)
    sys_prompt: str = ""

    @field_validator(
        "worker_name",
        "status",
        mode="before",
    )
    def _stringify(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)


class SubTaskSpecification(BaseModel):
    """
    Details of a subtask within a larger task decomposition.

    Attributes:
        description (str)
        input_intro(str)
        exact_input(str)
        expected_output(str)
        desired_auxiliary_tools(str)
    """

    description: str = Field(
        ...,
        description="Description of the subtask.",
    )
    input_intro: str = Field(
        ...,
        description="Introduction or context for the subtask input.",
    )
    exact_input: str = Field(
        ...,
        description="The exact input data or parameters for the subtask.",
    )
    expected_output: str = Field(
        ...,
        description="The expected output data or parameters for the subtask.",
    )
    desired_auxiliary_tools: str = Field(
        ...,
        description="Tools that would be helpful for this subtask.",
    )

    @field_validator(
        "description",
        "input_intro",
        "exact_input",
        "expected_output",
        "desired_auxiliary_tools",
        mode="before",
    )
    def _stringify(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)


class SubTaskStatus(BaseModel):
    """
    Represents the status and details of a subtask within a
    larger task decomposition.

    This class tracks individual subtasks, their execution status,
    assigned workers, and progress updates throughout the execution lifecycle.

    Attributes:
        state (Literal["todo", "in_progress", "done", "abandoned"]):
            Current execution status.
        updates (List[Update]):
            List of progress updates from workers.
        attempt (int):
            Number of execution attempts for this subtask.
        workers (List[WorkerInfo]):
            List of workers assigned to this subtask.
    """

    subtask_specification: SubTaskSpecification = Field(
        default_factory=SubTaskSpecification,
    )
    state: Literal["todo", "in_progress", "done", "abandoned"] = "todo"
    updates: List[Update] = Field(
        default_factory=list,
        description=(
            "List of updates from workers. "
            "MUST be empty list when initialized."
        ),
    )
    attempt: int = 0
    workers: List[WorkerInfo] = Field(
        default_factory=list,
        description=(
            "List of workers that have been assigned to this subtask."
            "MUST be EMPTY when initialize the subtask."
        ),
    )


class RoadMap(BaseModel):
    """Represents a roadmap for task decomposition and execution tracking.

    This class manages the overall task breakdown, containing the original task
    description and a list of decomposed subtasks with their execution status.

    Attributes:
        original_task (str):
            The original task description before decomposition.
        decomposed_tasks (List[SubTaskStatus]):
            List of subtasks created from the original task.
    """

    original_task: str = ""
    decomposed_tasks: List[SubTaskStatus] = Field(default_factory=list)

    def next_unfinished_subtask(
        self,
    ) -> Tuple[Optional[int], Optional[SubTaskStatus]]:
        """Find the next subtask that is not yet completed.

        Iterates through the decomposed tasks to find the first subtask
        with status "Planned" or "In-process".

        Returns:
            Tuple[Optional[int], Optional[SubTaskStatus]]: A tuple containing:
                - The index of the next unfinished subtask
                    (None if all tasks are done)
                - The SubTaskStatus object of the next unfinished subtask
                    (None if all tasks are done)
        """
        for i, subtask in enumerate(self.decomposed_tasks):
            if subtask.state in ["todo", "in_progress"]:
                return i, subtask
        return None, None


class PlannerNoteBook(BaseModel):
    """
    Represents a planner notebook.

    Attributes:
        time (str): The current time message.
        user_input (List[str]): List of user inputs.
        detail_analysis_for_plan (str): Detailed analysis for the plan.
        roadmap (RoadMap): The roadmap associated with the planner.
        files (Dict[str, str]): Dictionary of files related to the planner.
        full_tool_list (dict[str, dict]): Full schema of tools.
    """

    time: str = Field(default_factory=get_current_time_message)
    user_input: List[str] = Field(default_factory=list)
    detail_analysis_for_plan: str = (
        "Unknown. Please call `build_roadmap_and_decompose_task` to analyze."
    )
    roadmap: RoadMap = Field(default_factory=RoadMap)
    files: Dict[str, str] = Field(default_factory=dict)
    full_tool_list: list[dict] = Field(default_factory=list)
