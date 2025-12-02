# -*- coding: utf-8 -*-
import os
import copy
import base64
import inspect
from typing import Callable, Optional, Literal, Union, Coroutine, Any
from loguru import logger
from agentscope.module import StateModule
from agentscope.message import Msg

from alias.agent.agents._alias_agent_base import AliasAgentBase
from alias.agent.agents.dr_agent_utils.deep_research_task import (
    DRTaskBase,
    DEEPRESEARCH_TASKS_TYPES,
)
from alias.agent.agents.dr_agent_utils.deep_research_worker_builder import (
    get_deep_research_worker_builder,
)
from alias.agent.agents.dr_agent_utils.deep_research_worker_response import (
    DRWorkerResponse,
)
from alias.agent.tools.sandbox_util import get_workspace_file


class DeepResearchTreeNode(StateModule):
    def __init__(
        self,
        task_type: Literal["general", "finance"],
        current_executable: Optional[DRTaskBase] = None,
        level: int = 0,
        max_depth: int = 1,
        worker_builder_type: str = "default",
        parent_executable: Optional["DRTaskBase"] = None,
        report_dir: str = "/workspace",
        pre_execute_hook: Union[
            Callable[["DeepResearchTreeNode"], None],
            Callable[["DeepResearchTreeNode"], Coroutine[Any, Any, Any]],
            None,
        ] = None,
    ):
        super().__init__()
        self.task_type = task_type
        self.level = level
        self.worker_builder = get_deep_research_worker_builder(
            worker_builder_type if task_type == "general" else task_type,
        )
        self.worker = None
        self.current_executable: DRTaskBase = current_executable
        self.max_depth = max_depth

        # parent node
        self.parent_executable: DRTaskBase = parent_executable
        # children nodes
        self.children_nodes: list[DeepResearchTreeNode] = []

        # node key execution result
        self.node_execution_result = {}
        # node report for detailed digested information
        self.report_dir = report_dir
        self.node_report_path = (
            os.path.join(
                report_dir,
                self.current_executable.name + ".md",
            )
            if self.current_executable
            else ""
        )
        self.node_report = ""

        self.register_state("task_type")
        self.register_state("level")
        self.register_state("max_depth")
        self.register_state("node_execution_result")
        self.register_state("node_report_path")
        self.register_state("node_report")
        self.register_state(
            "worker",
            custom_to_json=lambda _: _.state_dict()
            if isinstance(_, AliasAgentBase)
            else None,
            # if worker not initialized, load the inform as stat dict and
            # build real worker later in self.execute(...)
            custom_from_json=lambda _: self.worker.load_state_dict(_)
            if isinstance(self.worker, AliasAgentBase)
            else _,
        )
        self.register_state(
            "current_executable",
            custom_to_json=lambda _: _.model_dump()
            if isinstance(_, DRTaskBase)
            else None,
            custom_from_json=lambda x: DEEPRESEARCH_TASKS_TYPES[
                self.task_type
            ].model_validate(x)
            if x
            else None,
        )
        self.register_state(
            "children_nodes",
            custom_to_json=lambda lst: [node.state_dict() for node in lst]
            if lst
            else [],
            custom_from_json=lambda lst: [
                DeepResearchTreeNode.reconstruct_from_state_dict(
                    x,
                    self.task_type,
                )
                for x in lst
            ]
            if lst
            else [],
        )

        self.pre_execute_hook = pre_execute_hook

    async def execute(
        self,
        master_agent: AliasAgentBase,
        generate_node_report: bool = True,
    ):
        assert issubclass(
            self.current_executable.get_worker_response_model(),
            DRWorkerResponse,
        ), "worker response model must be subclass of DRWorkerResponse"

        # execute pre execute hook (support both sync and async)
        if self.pre_execute_hook:
            if inspect.iscoroutinefunction(self.pre_execute_hook):
                await self.pre_execute_hook(self)
            else:
                self.pre_execute_hook(self)

        logger.info(f"Executing TreeNode: {self.current_executable.id}")

        logger.debug(f"Worker type 1: {type(self.worker)}")

        # For nodes building agent during the deep research process
        if self.worker is None and master_agent is None:
            raise ValueError(
                "No master agent specified but need to build worker",
            )
        if isinstance(self.worker, dict):
            worker_dict = copy.deepcopy(self.worker)
            self.worker = self.worker_builder(master_agent)
            self.worker.load_state_dict(worker_dict)
        elif self.worker is None:
            self.worker = self.worker_builder(master_agent)

        if self.worker is None:
            raise ValueError(
                "worker is not properly initialized in tree node execution",
            )

        logger.debug(f"Worker type 2: {type(self.worker)}")
        logger.debug(f"{self.worker}")

        # execute deep research worker
        result: Msg = await self.worker(
            self.current_executable.task_to_init_msg(),
            structured_model=(
                self.current_executable.get_worker_response_model()
            ),
        )

        # TODO: error handling
        structure_response = result.metadata
        logger.info(f"Worker structure response: {structure_response}")
        # record node execution information
        self.node_execution_result = structure_response or {}
        self.node_execution_result["response"] = result.get_text_content()

        self.current_executable.state = (
            structure_response.get("current_status", "abandoned")
            if structure_response
            else "abandoned"
        )

        if self.current_executable.state != "done":
            self.current_executable.state = "abandoned"

        logger.debug(self.current_executable.state)
        logger.debug(structure_response)

        # ask the agent to generate detailed report
        if generate_node_report:
            await self.agent_generate_report()

        if structure_response is not None and self.level + 1 < self.max_depth:
            subtasks = self.current_executable.build_children_nodes(
                structure_response,
            )
            for subtask in subtasks:
                self.children_nodes.append(
                    DeepResearchTreeNode(
                        task_type=self.task_type,
                        level=self.level + 1,
                        current_executable=subtask,
                        parent_executable=self.current_executable,
                        max_depth=self.max_depth,
                        report_dir=self.report_dir,
                        # only first execute runs pre_execute_hook
                        # pre_execute_hook=self.pre_execute_hook,
                    ),
                )

            ids = [node.current_executable.id for node in self.children_nodes]
            logger.info(
                "Building tree nodes" f"{ids}",
            )

    async def agent_generate_report(self):
        report_request = Msg(
            name="user",
            content=(
                "Generate a detailed report for me for the original query."
                "The report should be in markdown format and "
                "contain the following parts:"
                "1) a clear, detailed conclusion for the given task;"
                "2) detailed and comprehensive digestion and analysis of "
                "the gathered information;"
                "3) faithful record and document the source of the "
                "key information (e.g., URL of the webpage).\n"
                "The report MUST BE generated and written to "
                f"{self.node_report_path} "
            ),
            role="user",
        )
        await self.worker(report_request)

        file_content = get_workspace_file(
            self.worker.toolkit.sandbox,
            self.node_report_path,
        )
        self.node_report = base64.b64decode(file_content).decode("utf-8")

    def to_demo_dict(self) -> dict:
        """
        Convert the tree to a json structure for demo
        """
        return {
            "status": self.current_executable.state,
            "level": self.level,
            "id": self.current_executable.id,
            "name": self.current_executable.name,
            "description": self.current_executable.description,
            "node_report": self.node_report,
            "decomposed": [_.to_demo_dict() for _ in self.children_nodes],
            "evaluation_details": self.node_execution_result,
            "auxiliary_info": self.current_executable.metadata,
        }

    def to_synopsis_dict(self) -> dict:
        return {
            "status": self.current_executable.state,
            "level": self.level,
            "id": self.current_executable.id,
            "name": self.current_executable.name,
            "description": self.current_executable.description,
            "decomposed": [_.to_synopsis_dict() for _ in self.children_nodes],
        }

    def to_task_list(self) -> list:
        current_list = [
            {
                "state": self.current_executable.state,
                "description": self.current_executable.description,
            },
        ]
        for _ in self.children_nodes:
            current_list += _.to_task_list()
        return current_list

    @classmethod
    def reconstruct_from_state_dict(
        cls,
        state_dict: dict,
        task_type: Literal["general", "finance"],
    ) -> Optional["DeepResearchTreeNode"]:
        """
        Reconstruct a DeepResearchTreeNode from a state dict.

        Args:
            state_dict (dict): The state dictionary to reconstruct from
            task_type (str): The task type to reconstruct from

        Returns:
            Reconstructed DeepResearchTreeNode instance,
            or None if state_dict is empty
        """
        if not state_dict:
            return None
        # Create a new DeepResearchTreeNode instance
        node = cls(task_type)

        # Load the rest of the state using load_state_dict
        # This will handle decomposed_executables recursively
        logger.debug(f"builder function: {node.worker_builder}")
        node.load_state_dict(state_dict)
        logger.debug(node.worker)
        return node
