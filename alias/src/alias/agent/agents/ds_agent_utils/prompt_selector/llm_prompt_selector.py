# -*- coding: utf-8 -*-
import os
from typing import Dict, List
from pydantic import BaseModel, Field
from loguru import logger
from agentscope.message import Msg
from agentscope._utils._common import _create_tool_from_base_model
from alias.agent.agents.ds_agent_utils.utils import model_call_with_retry
from alias.agent.agents.ds_agent_utils.ds_config import PROMPT_DS_BASE_PATH
from .base_prompt_selector import (
    PromptSelector,
)
from alias.agent.agents.ds_agent_utils import (  # pylint: disable=wrong-import-order,line-too-long  # noqa: E501
    get_prompt_from_file,
)


class LLMPromptSelector(PromptSelector):
    """LLM-based Intelligent Prompt Selector"""

    def __init__(
        self,
        model,
        formatter,
        available_prompts: Dict[str, str],
    ):
        super().__init__(available_prompts)
        self.model = model
        self.formatter = formatter

    async def select(self, input_data: str) -> List[str]:
        """
        Use LLM to select the most suitable prompt scenarios based on input

        Args:
            input: User input or task description

        Returns:
            Selected scenario names list (sorted by priority)
        """
        if not input_data or not self.available_prompts:
            return []

        try:
            # Construct selection prompt
            system_prompt = self._build_selection_prompt()
            user_content = f"User input: {input_data}"

            class ScenarioModel(BaseModel):
                scenarios: List[str] = Field(
                    default_factory=list,
                    description=(
                        "List of matched scenario names."
                        "Return an empty list if no matches."
                    ),
                    json_schema_extra={
                        "type": "array",
                        "items": {"type": "string"},
                        "example": ["data_analysis"],
                    },
                )
                reasoning: str = Field(
                    description=(
                        "Detailed reasoning for selecting these scenarios."
                    ),
                )

            format_tool = _create_tool_from_base_model(ScenarioModel)

            res = await model_call_with_retry(
                self.model,
                self.formatter,
                [
                    Msg("system", system_prompt, "system"),
                    Msg("user", user_content, "user"),
                ],
                tool_json_schemas=[format_tool],
                tool_choice=format_tool["function"]["name"],
            )

            selected_scenarios = res.content[-1]["input"]["scenarios"]

            # Validate selected scenarios
            valid_scenarios = [
                s for s in selected_scenarios if s in self.available_prompts
            ]

            if valid_scenarios:
                input_preview = (
                    input_data[:50].replace("\n", " ").replace("\t", " ")
                )
                logger.info(
                    f"LLMPromptSelector selected scenarios: {valid_scenarios} "
                    f"for input: {input_preview}...",
                )
                return valid_scenarios
            else:
                logger.warning(
                    f"LLMPromptSelector found no valid scenarios, "
                    f"returning empty list for input: {input_data[:50]}...",
                )
                return []

        except Exception as e:
            logger.error(
                f"LLMPromptSelector selection failed: {str(e)} "
                f"for input: {input_data[:50]}...",
            )
            return []

    def _build_selection_prompt(self) -> str:
        """Build system prompt for scenario selection"""
        scenarios_info = []
        for scenario, description in self.available_prompts.items():
            scenarios_info.append(f"- {scenario}: {description}")

        scenarios_list = "\n".join(scenarios_info)

        prompt = get_prompt_from_file(
            os.path.join(
                PROMPT_DS_BASE_PATH,
                "_scenario_selected_prompt.md",
            ),
            False,
        )
        prompt = prompt.format(scenarios_list=scenarios_list)
        return prompt
