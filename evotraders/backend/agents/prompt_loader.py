# -*- coding: utf-8 -*-
"""
Prompt Loader - Unified management and loading of Agent Prompts
Supports Markdown and YAML formats
Uses simple string replacement, does not depend on Jinja2
"""
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class PromptLoader:
    """Unified Prompt loader"""

    def __init__(self, prompts_dir: Optional[Path] = None):
        """
        Initialize Prompt loader

        Args:
            prompts_dir: Prompts directory path,
                         defaults to prompts/ directory of current file
        """
        if prompts_dir is None:
            self.prompts_dir = Path(__file__).parent / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)

        # Cache loaded prompts
        self._prompt_cache: Dict[str, str] = {}
        self._yaml_cache: Dict[str, Dict] = {}

    def load_prompt(
        self,
        agent_type: str,
        prompt_name: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Load and render Prompt

        Args:
            agent_type: Agent type (analyst, portfolio_manager, risk_manager)
            prompt_name: Prompt file name (without extension)
            variables: Variable dictionary for rendering Prompt

        Returns:
            Rendered prompt string

        Examples:
            loader = PromptLoader()
            prompt = loader.load_prompt("analyst", "tool_selection",
            {"analyst_persona": "Technical Analyst"})
        """
        cache_key = f"{agent_type}/{prompt_name}"

        # Try to load from cache
        if cache_key not in self._prompt_cache:
            prompt_path = self.prompts_dir / agent_type / f"{prompt_name}.md"

            if not prompt_path.exists():
                raise FileNotFoundError(
                    f"Prompt file not found: {prompt_path}\n"
                    f"Please create the prompt file or check the path.",
                )

            with open(prompt_path, "r", encoding="utf-8") as f:
                self._prompt_cache[cache_key] = f.read()

        prompt_template = self._prompt_cache[cache_key]

        # If variables provided, use simple string replacement
        if variables:
            rendered = self._render_template(prompt_template, variables)
        else:
            rendered = prompt_template

        # Smart escaping: escape braces in JSON code blocks
        # rendered = self._escape_json_braces(rendered)
        return rendered

    def _render_template(
        self,
        template: str,
        variables: Dict[str, Any],
    ) -> str:
        """
        Render template using simple string replacement
        Supports {{ variable }} syntax (compatible with previous Jinja2 format)

        Args:
            template: Template string
            variables: Variable dictionary

        Returns:
            Rendered string
        """
        rendered = template

        # Replace {{ variable }} format
        for key, value in variables.items():
            # Support both {{ key }} and {{key}} formats
            pattern1 = f"{{{{ {key} }}}}"
            pattern2 = f"{{{{{key}}}}}"
            rendered = rendered.replace(pattern1, str(value))
            rendered = rendered.replace(pattern2, str(value))

        return rendered

    def _escape_json_braces(self, text: str) -> str:
        """
        Escape braces in JSON code blocks, treating them as literals

        Args:
            text: Text to process

        Returns:
            Processed text
        """

        def replace_code_block(match):
            code_content = match.group(1)
            # Escape all braces within code block
            escaped = code_content.replace("{", "{{").replace("}", "}}")
            return f"```json\n{escaped}\n```"

        # Replace all braces in JSON code blocks
        text = re.sub(
            r"```json\n(.*?)\n```",
            replace_code_block,
            text,
            flags=re.DOTALL,
        )
        return text

    def load_yaml_config(
        self,
        agent_type: str,
        config_name: str,
    ) -> Dict[str, Any]:
        """
        Load YAML configuration file

        Args:
            agent_type: Agent type
            config_name: Configuration file name (without extension)

        Returns:
            Configuration dictionary

        Examples:
            >>> loader = PromptLoader()
            >>> config = loader.load_yaml_config("analyst", "personas")
        """
        cache_key = f"{agent_type}/{config_name}"

        if cache_key not in self._yaml_cache:
            yaml_path = self.prompts_dir / agent_type / f"{config_name}.yaml"

            if not yaml_path.exists():
                raise FileNotFoundError(f"YAML config not found: {yaml_path}")

            with open(yaml_path, "r", encoding="utf-8") as f:
                self._yaml_cache[cache_key] = yaml.safe_load(f)

        return self._yaml_cache[cache_key]

    def clear_cache(self):
        """Clear cache (for hot reload)"""
        self._prompt_cache.clear()
        self._yaml_cache.clear()

    def reload_prompt(self, agent_type: str, prompt_name: str):
        """Reload specified prompt (force cache refresh)"""
        cache_key = f"{agent_type}/{prompt_name}"
        if cache_key in self._prompt_cache:
            del self._prompt_cache[cache_key]

    def reload_config(self, agent_type: str, config_name: str):
        """Reload specified configuration (force cache refresh)"""
        cache_key = f"{agent_type}/{config_name}"
        if cache_key in self._yaml_cache:
            del self._yaml_cache[cache_key]
