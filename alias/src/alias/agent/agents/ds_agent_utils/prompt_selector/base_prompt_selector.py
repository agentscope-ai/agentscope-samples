# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from typing import Dict, List


class PromptSelector(ABC):
    """Abstract Base Class for Prompt Selector"""

    def __init__(self, available_prompts: Dict[str, str]):
        """
        Args:
            available_prompts: Dictionary of available prompts in the format
            {scenario_name: prompt_content}
            e.g., {"data_analyze": "...", "forecast": "..."}
        """
        self.available_prompts = available_prompts

    @abstractmethod
    async def select(self, input_data: str) -> List[str]:
        """
        Get the most suitable prompts based on the input
        Args:
            input: User input or task description
        Returns:
            Selected prompt list (in order of priority),
            returns scenario names list
            e.g., ["data_analyze", "forecast"]
        """

    def get_prompt_by_scenario(self, scenario: str) -> str:
        """
        Get prompt content by scenario name
        Args:
            scenario: Scenario name
        Returns:
            Prompt content, returns empty string if scenario does not exist
        """
        return self.available_prompts.get(scenario, "")

    def get_all_scenarios(self) -> List[str]:
        """Get a list of all available scenario names"""
        return list(self.available_prompts.keys())
