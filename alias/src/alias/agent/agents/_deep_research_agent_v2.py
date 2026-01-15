# -*- coding: utf-8 -*-
"""Deep Research Agent"""
# pylint: disable=too-many-lines, no-name-in-module
import json
import uuid
import os
import asyncio
from typing import Any, Optional, Callable, Literal
from loguru import logger
from pydantic import BaseModel, Field

from agentscope.formatter import FormatterBase
from agentscope.memory import MemoryBase
from agentscope.message import Msg, ToolUseBlock
from agentscope.model import ChatModelBase
from agentscope.tool import ToolResponse
from agentscope.message import TextBlock


from alias.agent.agents import AliasAgentBase
from alias.agent.tools import AliasToolkit, share_tools
from alias.agent.agents.common_agent_utils import (
    get_user_input_to_mem_pre_reply_hook,
    save_post_reasoning_state,
    save_post_action_state,
    agent_load_states_pre_reply_hook,
)
from alias.agent.agents.dr_agent_utils import (
    DeepResearchTreeNode,
    DRTaskBase,
    generate_html_visualization,
    calculate_tree_stats,
    BasicTask,
    DEEP_RESEARCH_SYSTEM_PROMPT,
    HypothesisDrivenTask,
)

# Load built-in prompts
_PROMPT_DIR = os.path.join(
    os.path.dirname(__file__),
    "dr_agent_utils",
    "built_in_prompt",
)

with open(
    os.path.join(_PROMPT_DIR, "prompt_initialize_hypotheses.md"),
    "r",
    encoding="utf-8",
) as _f:
    PROMPT_INITIALIZE_HYPOTHESES = _f.read()

with open(
    os.path.join(_PROMPT_DIR, "prompt_markdown_to_html.md"),
    "r",
    encoding="utf-8",
) as _f:
    PROMPT_MARKDOWN_TO_HTML = _f.read()


class DeepResearchAgent(AliasAgentBase):
    deep_research_master_tool_label: str = "deep_research_master"
    """The group label for deep research master tools"""

    def __init__(
        self,
        name: str,
        model: ChatModelBase,
        formatter: FormatterBase,
        memory: MemoryBase,
        toolkit: AliasToolkit,
        agent_working_dir: str,
        sys_prompt: Optional[str] = None,
        max_iters: int = 20,
        max_depth: int = 2,
        state_saving_dir: Optional[str] = None,
        session_service: Any = None,
        deep_research_task_type: type[DRTaskBase] = None,
        node_level_report: bool = True,
        max_clarification_chance: int = 3,
        enforce_mode: Literal["general", "finance", "auto"] = "auto",
    ):
        super().__init__(
            name=name,
            sys_prompt=sys_prompt
            if sys_prompt
            else DEEP_RESEARCH_SYSTEM_PROMPT,
            model=model,
            formatter=formatter,
            memory=memory,
            toolkit=toolkit,
            max_iters=max_iters,
            session_service=session_service,
            state_saving_dir=state_saving_dir,
        )
        self.max_depth = max_depth
        self.deep_research_task_type = deep_research_task_type or BasicTask
        self.deep_research_task_builder: Callable[
            [str],
            DRTaskBase,
        ] = self.deep_research_task_type.from_user_query
        self.deep_research_tree: DeepResearchTreeNode | None = None
        self.register_state(
            "deep_research_tree",
            custom_to_json=lambda x: x.state_dict() if x else None,
            custom_from_json=(
                lambda x: DeepResearchTreeNode.reconstruct_from_state_dict(
                    x,
                    x.get("task_type", "general"),
                )
                if x
                else None
            ),
        )
        self.node_level_report = node_level_report
        self.agent_working_dir = agent_working_dir
        self.deep_research_enforce_mode = enforce_mode

        # add hooks
        self.register_instance_hook(
            "pre_reply",
            "agent_load_states_pre_reply_hook",
            agent_load_states_pre_reply_hook,
        )
        self.register_instance_hook(
            "pre_reply",
            "get_user_input_to_mem_pre_reply_hook",
            get_user_input_to_mem_pre_reply_hook,
        )
        self.register_instance_hook(
            "post_reasoning",
            "save_post_reasoning_state",
            save_post_reasoning_state,
        )
        self.register_instance_hook(
            "post_acting",
            "save_post_action_state",
            save_post_action_state,
        )

        # prepare agent built-in tools
        self.toolkit.create_tool_group(
            self.deep_research_master_tool_label,
            description="Deep research main process master tools",
            active=True,
        )
        self.toolkit.register_tool_function(
            self.deep_research,
            group_name=self.deep_research_master_tool_label,
        )
        self.toolkit.register_tool_function(
            self.generate_final_report,
            group_name=self.deep_research_master_tool_label,
        )
        self.toolkit.register_tool_function(
            self.gathering_preliminary_information,
            group_name=self.deep_research_master_tool_label,
        )
        self.toolkit.register_tool_function(
            self.clarification,
            group_name=self.deep_research_master_tool_label,
        )
        self.toolkit.register_tool_function(
            self.revise_deep_research_tree,
            group_name=self.deep_research_master_tool_label,
        )
        self.agent_stop_function_names.append(
            "generate_final_report",
        )
        self.agent_stop_function_names.append(
            "clarification",
        )
        # TODO: add constraint in pre_reasoning hook
        self.max_clarification_chance = max_clarification_chance

    async def _generate_hypothesis(
        self,
        node: DeepResearchTreeNode,
    ):
        """Generate initial hypotheses for HypothesisDrivenTask"""

        from agentscope._utils._common import _get_timestamp

        sys_prompt = PROMPT_INITIALIZE_HYPOTHESES.format(
            current_date=_get_timestamp(),
        )

        instruction_msg = Msg(
            "system",
            content=[TextBlock(type="text", text=sys_prompt)],
            role="system",
        )
        user_msg = Msg(
            "user",
            content=[
                TextBlock(
                    type="text",
                    text=f"Research Question: "
                    f"{node.current_executable.description}\n\n"
                    f"Generate 2-4 key hypotheses.",
                ),
            ],
            role="user",
        )

        class HypothesesSchema(BaseModel):
            hypotheses: list[str] = Field(
                description="List of 2-4 testable hypotheses",
            )

        try:
            prompt = await self.formatter.format([instruction_msg, user_msg])
            res = await self.model(prompt, structured_model=HypothesesSchema)

            hypotheses = None
            if self.model.stream:
                async for content_chunk in res:
                    if (
                        content_chunk.metadata
                        and "hypotheses" in content_chunk.metadata
                    ):
                        hypotheses = content_chunk.metadata["hypotheses"]
            else:
                if res.metadata and "hypotheses" in res.metadata:
                    hypotheses = res.metadata["hypotheses"]

            if hypotheses:
                for hypothesis in hypotheses:
                    hypothesis_task = HypothesisDrivenTask(
                        description=f"Investigate hypothesis:{hypothesis}",
                        evidences=[],
                        parent_executable=node,
                        max_depth=node.max_depth,
                        deep_research_worker_builder=node.worker_builder,
                        level=node.level + 1,
                    )
                    node.children_nodes.append(
                        DeepResearchTreeNode(
                            task_type="finance",
                            current_executable=hypothesis_task,
                            level=node.level + 1,
                            parent_executable=None,
                            max_depth=self.max_depth,
                            report_dir=self.agent_working_dir,
                            pre_execute_hook=None,
                        ),
                    )
                node.current_executable.state = "done"

                await self.print(
                    Msg(
                        self.name,
                        content=f"✨ Generated {len(hypotheses)} hypotheses:\n"
                        + "\n".join(
                            [
                                f"  {i+1}. {h}"
                                for i, h in enumerate(hypotheses)
                            ],
                        ),
                        role="assistant",
                    ),
                )
        except Exception as e:
            logger.warning(f"Failed to generate hypotheses: {e}")

    def _get_next_executables(self) -> list[DeepResearchTreeNode]:
        # [for all deep research agents]
        # Tree exploration to get the next active/unfinished subtask/hypothesis
        # from self.deep_research_tree, where whose parent nodes are done or
        # abandoned (already taken care of)
        if self.deep_research_tree is None:
            return []

        ready_nodes: list[DeepResearchTreeNode] = []
        stack: list[DeepResearchTreeNode] = [self.deep_research_tree]
        parent_ready_states: set[str] = {"done", "abandoned"}

        while stack:
            node = stack.pop()

            parent_is_ready = (
                node.parent_executable is None
                or node.parent_executable.state in parent_ready_states
            )
            if (
                node.current_executable.state
                in [
                    "todo",
                    "in_progress",
                ]
                and parent_is_ready
                and node.level < self.max_depth
            ):
                ready_nodes.append(node)

            # traverse children regardless of current readiness, so we can pick
            # up active nodes deeper in the tree when their parents finish
            stack.extend(reversed(node.children_nodes))

        return ready_nodes

    async def deep_research(
        self,
        deep_research_query: str,
        query_category: Literal["general", "finance"] = "general",
        # pylint: disable=W0613
    ) -> ToolResponse:
        """
        If the user query is a complicated question,
        or required multiple rounds of online search,
        then use this `deep_research` tool to gather in-depth research results.
        Notice:
        Provide the `deep_research_query` carefully, as the deep research
        process will be a long process and heavily relies on this initial
        query. The `deep_research_query` query should perfectly align
        with the user's real intend. If you are not totally
        confident, you can use `gathering_preliminary_information`
        and `clarification` tools to gain more context and clarification.

        Args:
            deep_research_query (str):
                The refined query for deep research based on user input,
                necessary background knowledge gathering and clarification
                from user.
            query_category (Literal["general", "finance"]):
                The category that the user query falls in,
                either "general" or "finance".
        """
        self.toolkit.update_tool_groups(
            self.deep_research_master_tool_label,
            active=False,
        )
        if self.deep_research_enforce_mode != "auto":
            query_category = self.deep_research_enforce_mode

        # switch to finance hypothesis driven mode
        if query_category == "finance":
            self.deep_research_task_type = HypothesisDrivenTask
            self.deep_research_task_builder = (
                HypothesisDrivenTask.from_user_query
            )

        try:
            if self.deep_research_tree is None:
                self.deep_research_tree = DeepResearchTreeNode(
                    task_type=query_category,
                    level=0,
                    current_executable=self.deep_research_task_builder(
                        deep_research_query,
                    ),
                    parent_executable=None,
                    max_depth=self.max_depth,
                    report_dir=self.agent_working_dir,
                    pre_execute_hook=self._generate_hypothesis
                    if query_category == "finance"
                    else None,
                )
            next_executables = self._get_next_executables()
            while next_executables:
                for executable in next_executables:
                    await executable.execute(self, self.node_level_report)

                next_executables = self._get_next_executables()
                # TODO: deduplication: to avoid repeated search area

                next_tasks = [
                    t.current_executable.model_dump() for t in next_executables
                ]
                logger.info(
                    f"--- {[t.level for t in next_executables]} ---"
                    f"{next_tasks}",
                )
                await self._update_plan_presentation()
        except Exception as e:
            import traceback

            logger.info(f"----> ERROR: {e}")
            logger.error(traceback.format_exc())

        self.toolkit.update_tool_groups(
            self.deep_research_master_tool_label,
            active=True,
        )
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text="Successfully finish the result.",
                ),
            ],
            metadata={"success": True},
        )

    def _extract_descriptions_and_reports(self, node: dict) -> str:
        """
        Recursively extract 'description' and 'node_report' fields from
        research tree nodes.
        Returns a single long string with all descriptions and reports.
        """
        results = []
        # Extract description
        description = node.get("description", "") or node.get("objective", "")
        if description:
            results.append(f"Description: {description}")
        # Extract node_report
        node_report = node.get("node_report", "")
        if node_report:
            results.append(f"Report: {node_report}")
        # Recurse into children
        children = node.get("decomposed", [])
        for child in children:
            results.append(self._extract_descriptions_and_reports(child))
        return "\n\n\n".join([r for r in results if r])

    async def _generate_html_report(self, dr_tree_json: dict):
        """
        This tool will convert the useful information gathered in the
        deep research process and general a detailed report
        """
        stats = calculate_tree_stats(dr_tree_json)
        html_content = generate_html_visualization(dr_tree_json, stats)
        res = await self.toolkit.call_tool_function(
            tool_call=ToolUseBlock(
                id=str(uuid.uuid4()),
                type="tool_use",
                name="write_file",
                input={
                    "path": os.path.join(
                        self.agent_working_dir,
                        "deep_research_final_report" + ".html",
                    ),
                    "content": html_content,
                },
            ),
        )
        async for r in res:
            if r.metadata and r.metadata.get("is_last"):
                await self.print(
                    Msg(
                        self.name,
                        content="Successfully generate html content",
                        role="assistant",
                    ),
                )

    async def _generate_illustrated_report(self, markdown_content: str):
        """
        Convert markdown report to illustrated HTML.
        Uses LLM to generate data-rich HTML with embedded charts.
        """
        await self.print(
            Msg(
                self.name,
                content="Converting report to illustrated HTML with charts...",
                role="assistant",
            ),
        )

        # Build messages for LLM
        instruction_msg = Msg(
            "system",
            content=[TextBlock(type="text", text=PROMPT_MARKDOWN_TO_HTML)],
            role="system",
        )
        content_msg = Msg(
            "user",
            content=[
                TextBlock(
                    type="text",
                    text=(
                        f"Convert the following markdown content to"
                        f"an illustrated HTML document "
                        f"with data visualizations:\n\n {markdown_content}"
                    ),
                ),
            ],
            role="user",
        )

        # Call LLM to generate HTML
        prompt = await self.formatter.format([instruction_msg, content_msg])
        res = await self.model(prompt)

        if self.model.stream:
            msg = Msg(self.name, [], "assistant")
            async for content_chunk in res:
                msg.content = content_chunk.content
                # await self.print(msg, False)
            # await self.print(msg, True)

            # Add a tiny sleep to yield the last message object in the
            # message queue
            await asyncio.sleep(0.001)

        else:
            msg = Msg(self.name, list(res.content), "assistant")
            await self.print(msg, True)

        # Remove markdown code fences if present
        html_content = msg.content[0]["text"]

        # Write illustrated HTML to file
        illustrated_path = os.path.join(
            self.agent_working_dir,
            "deep_research_illustrated_report.html",
        )
        write_res = await self.toolkit.call_tool_function(
            tool_call=ToolUseBlock(
                id=str(uuid.uuid4()),
                type="tool_use",
                name="write_file",
                input={
                    "path": illustrated_path,
                    "content": html_content,
                },
            ),
        )

        async for r in write_res:
            if r.metadata and r.metadata.get("is_last"):
                await self.print(
                    Msg(
                        self.name,
                        content=f"Successfully generated "
                        f"illustrated HTML report at: {illustrated_path}",
                        role="assistant",
                    ),
                )

    async def _generate_markdown_report(
        self,
        dr_tree_json: dict,
        theme: str,
    ) -> Msg:
        """
        Generate detailed comprehensive report
        """
        deep_research_content = self._extract_descriptions_and_reports(
            dr_tree_json,
        )
        context_msg = Msg(
            "user",
            content=[TextBlock(type="text", text=deep_research_content)],
            role="user",
        )
        root_executable = self.deep_research_tree.current_executable
        instruction_msg = root_executable.build_final_report_system_msg(
            theme,
        )

        prompt = await self.formatter.format([instruction_msg, context_msg])
        res = await self.model(prompt)
        if self.model.stream:
            msg = Msg(self.name, [], "assistant")
            async for content_chunk in res:
                msg.content = content_chunk.content
                await self.print(msg, False)
            await self.print(msg, True)

            # Add a tiny sleep to yield the last message object in the
            # message queue
            await asyncio.sleep(0.001)

        else:
            msg = Msg(self.name, list(res.content), "assistant")
            await self.print(msg, True)

        return msg

    async def generate_final_report(
        self,
        theme: str,
        report_format: Literal[
            "process",
            "markdown",
            "illustrated",
            "all",
        ] = "all",
    ):
        """
        Generate a final, detailed and comprehensive report based on the
        information gathered from deep research process.

        Args:
            theme (str):
                The theme of the final report, should be faithful to the user
                query.
            report_format
            (Literal["process", "markdown", "illustrated", "all"]):
            Choose what format to generate.
        """
        # generate tree json
        dr_tree_json = self.deep_research_tree.to_demo_dict()

        # generate final report in markdown
        dr_tree_json["root_full_report"] = ""
        if report_format in ["markdown", "all"]:
            markdown_report_msg = await self._generate_markdown_report(
                dr_tree_json,
                theme,
            )
            dr_tree_json[
                "root_full_report"
            ] = markdown_report_msg.get_text_content()

        # generate final report in html
        if report_format in ["process", "all"]:
            await self._generate_html_report(dr_tree_json)

        # generate illustrated report (markdown to HTML with charts)
        if report_format in ["illustrated", "all"]:
            await self._generate_illustrated_report(
                dr_tree_json.get("root_full_report", ""),
            )

        # save deep research tree json
        res = await self.toolkit.call_tool_function(
            tool_call=ToolUseBlock(
                id=str(uuid.uuid4()),
                type="tool_use",
                name="write_file",
                input={
                    "path": os.path.join(
                        self.agent_working_dir,
                        "deep_research_tree" + ".json",
                    ),
                    "content": json.dumps(
                        dr_tree_json,
                        ensure_ascii=False,
                        indent=4,
                    ),
                },
            ),
        )
        async for r in res:
            if r.metadata and r.metadata.get("is_last"):
                await self.print(
                    Msg(
                        self.name,
                        content="Successfully generate html content",
                        role="assistant",
                    ),
                )

        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=dr_tree_json["root_full_report"],
                ),
            ],
            metadata={"success": True},
        )

    async def gathering_preliminary_information(
        self,
        search_tool_name: str,
    ) -> ToolResponse:
        """
        This tool is designed as a reflection step. When the user query
        is about some topics that you are not familiar with, you need to use
        this tool to select the most appropriate search tool
        from your available tool set and get the instruction for
        the next steps.

        Args:
            search_tool_name (str):
                The name of the search tool to gather preliminary information.
        """
        gathering_instruction = (
            f"The next step is to use `{search_tool_name}` to do preliminary"
            f"information gathering. When using the `{search_tool_name}`, "
            "if there is a parameter controlling the max number of return "
            "result, set the parameter so that AT MOST 5 results will "
            "be returned. "
            f"ONLY use `{search_tool_name}` ONCE!"
            "If you need to do more detailed research, use the "
            "`deep_research` tool."
        )
        return ToolResponse(
            content=[
                TextBlock(type="text", text=gathering_instruction),
            ],
            is_last=True,
            metadata={"success": True},
        )

    async def clarification(
        self,
        clarification_question: str,
        options: list[str],
    ):
        """
        WHENEVER you want to ask user for clarification, use this tool.
        Generate a question for user in order for more details or
        clarification about the ambiguities. Also provide some options
        as candidate answers for the user.

        Args:
            clarification_question (str):
                Question for user to clarify.
            options (list[str]):
                Candidate answers for a user to choose or serve as examples.
        """
        return_info = (
            "Successfully generated the clarification message."
            "You should refine your deep research query after receiving"
            "user's clarification."
        )
        print_msg = (
            f"Question: {clarification_question}\n"
            f"Options: {json.dumps(options, indent=4, ensure_ascii=False)}\n"
        )
        # TODO: service connection
        await self.print(
            Msg(
                self.name,
                content=[TextBlock(type="text", text=print_msg)],
                role="assistant",
            ),
        )
        self.max_clarification_chance -= 1
        return ToolResponse(
            content=[
                TextBlock(type="text", text=return_info),
            ],
            is_last=True,
            metadata={"success": True},
        )

    async def _identify_node(
        self,
        user_feedback: str,
    ) -> str | None:
        # tree synopsis check, identify the node
        system_prompt = (
            "You will be provided a deep research tree represented in JSON."
            "Try to identify which deep research node (select only ONE) "
            "is related to the user feedback. Output ONLY the id of the node, "
            "without any prefix."
        )
        tree_synopsis = self.deep_research_tree.to_synopsis_dict()
        user_feedback_prompt = (
            "The following is the deep research tree synopsis:\n"
            f"{tree_synopsis}\n\n"
            f"The following is the user feedback: {user_feedback}\n\n"
            "Try to identify the related node and return id."
        )
        prompt = await self.formatter.format(
            [
                Msg("system", system_prompt, "system"),
                Msg("user", user_feedback_prompt, "user"),
            ],
        )

        class RetrievedNodeID(BaseModel):
            most_related_node_id: str = Field(
                description="The id of the node that is most likely related"
                "to the user feedback.",
            )

        identified_id = None
        try:
            res = await self.model(
                prompt,
                structured_model=RetrievedNodeID,
            )
            if self.model.stream:
                msg = Msg(self.name, [], "assistant")
                async for content_chunk in res:
                    msg.content = content_chunk.content
                    if content_chunk.metadata:
                        identified_id = content_chunk.metadata.get(
                            "most_related_node_id",
                            "",
                        )
                # Add a tiny sleep to yield the last message object in the
                # message queue
                await asyncio.sleep(0.001)
            else:
                msg = Msg(self.name, list(res.content), "assistant")
                await self.print(msg, True)
                if res.metadata:
                    identified_id = res.metadata.get(
                        "most_related_node_id",
                        "",
                    )
            return identified_id
        except Exception:  # pylint: disable=W0703
            return identified_id

    async def _revise_node(
        self,
        identified_id: str,
        user_feedback: str,
    ) -> ToolResponse:
        if self.deep_research_tree is None:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="No deep research tree. "
                        "Please call `deep_research` tool first",
                    ),
                ],
            )
        related_tree_node = self._get_tree_node(
            identified_id,
            self.deep_research_tree,
        )
        if not related_tree_node:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="Fail to find corresponding tree node.",
                    ),
                ],
                metadata={"success": False},
            )
        # remove all children of the node
        related_tree_node.decomposed_executables = []
        # reset state
        related_tree_node.current_executable.state = "in_progress"
        # get node current context
        node_context = related_tree_node.to_synopsis_dict()
        # revise node description

        class NewDescription(BaseModel):
            new_description: str = Field(
                description="modified description",
            )

        system_prompt = (
            "You will be provided a deep research tree node in JSON."
            "Try to revise the description of the node so that "
            "the new description can resolved user's feedback."
        )
        user_feedback_prompt = (
            "The following is the deep research tree node context:\n"
            f"{node_context}\n\n"
            f"The following is the user feedback: {user_feedback}\n\n"
            "Try to identify the related node and return id."
        )
        prompt = await self.formatter.format(
            [
                Msg("system", system_prompt, "system"),
                Msg("user", user_feedback_prompt, "user"),
            ],
        )

        try:
            res = await self.model(
                prompt,
                structured_model=NewDescription,
            )
            new_description = ""
            if self.model.stream:
                msg = Msg(self.name, [], "assistant")
                async for content_chunk in res:
                    msg.content = content_chunk.content
                    if content_chunk.metadata:
                        new_description = content_chunk.metadata.get(
                            "new_description",
                            "",
                        )
                # Add a tiny sleep to yield the last message object in the
                # message queue
                await asyncio.sleep(0.001)
            else:
                msg = Msg(self.name, list(res.content), "assistant")
                await self.print(msg, True)
                if res.metadata:
                    new_description = res.metadata.get(
                        "new_description",
                        "",
                    )

            related_tree_node.description = new_description
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=(
                            "Successfully revised the new description."
                            "Current node state: \n"
                            f"{related_tree_node.to_synopsis_dict()}\n"
                        ),
                    ),
                    TextBlock(
                        type="text",
                        text="Next, you should call `deep_research` tool"
                        "to continue the search.",
                    ),
                ],
                metadata={"success": True},
            )
        except Exception as e:  # pylint: disable=W0703
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="Fail to generate new description for the"
                        f" deep research tree node. {e}",
                    ),
                ],
                metadata={"success": True},
            )

    async def revise_deep_research_tree(
        self,
        user_feedback: str,
    ):
        """
        Revise or reset the related deep research tree nodes after interrupted
        and received new user feedback.

        Args:
            user_feedback (str):
                User's feedback about changing the deep research plan.
        """
        identified_id = await self._identify_node(user_feedback)
        # tree node modification
        if identified_id:
            return await self._revise_node(identified_id, user_feedback)
        else:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="Fail to identify the related node and return id."
                        " Continue to `deep_research`.`",
                    ),
                ],
                metadata={"success": False},
            )

    def _get_tree_node(self, node_id: str, root: DeepResearchTreeNode):
        if root.current_executable.id == node_id:
            return root
        for node in root.children_nodes:
            res = self._get_tree_node(node_id, node)
            if res:
                return res
        return None

    async def _update_plan_presentation(self):
        if self.deep_research_tree:
            await self.session_service.create_plan(
                content={
                    "subtasks": self.deep_research_tree.to_task_list(),
                },
            )


def init_dr_toolkit(full_toolkit) -> AliasToolkit:
    deep_research_toolkit = AliasToolkit(full_toolkit.sandbox, add_all=False)
    dr_tool_list = [
        "tavily_search",
        "tavily_extract",
        "write_file",
        "create_directory",
        "list_directory",
        "read_file",
        "run_shell_command",
    ]
    share_tools(full_toolkit, deep_research_toolkit, dr_tool_list)
    logger.info("Init deep research toolkit")
    return deep_research_toolkit
