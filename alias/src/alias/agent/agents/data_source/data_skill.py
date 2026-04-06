# -*- coding: utf-8 -*-
import os

from pathlib import Path
from typing import List

import frontmatter
from loguru import logger

from agentscope.tool._types import AgentSkill

from alias.agent.agents.ds_agent_utils.utils import get_prompt_from_file
from alias.agent.agents.data_source._typing import SourceType


class DataSkill(AgentSkill):
    """The source type of the skill."""

    type: List[SourceType]


class DataSkillManager:
    """Data Skill Selector Based on Data Source Type"""

    _default_skill_path_base = os.path.join(
        Path(__file__).resolve().parent.parent,
        "_built_in_skill/data",
    )

    def __init__(
        self,
    ):
        self.skills = self.register_skill_dir()

        self.source_type_2_skills = {}
        for skill in self.skills:
            for t in skill["type"]:
                self.source_type_2_skills[t] = skill

    def load(self, data_source_types: List[SourceType]) -> List[str]:
        """
        Load skills based on data source type

        Args:
            data_source_types: List of SourceType enum values

        Returns:
            Selected skill content list
        """
        if not data_source_types:
            return []

        selected_skills = []

        data_source_types = set(data_source_types)
        for source_type in data_source_types:
            try:
                # Get skill from source type mapping
                skill = self.source_type_2_skills.get(source_type, None)

                # Skip if no corresponding skill
                if not skill:
                    logger.warning(
                        "DataSkillSelector found no valid skill for data "
                        f"source type: {source_type}",
                    )
                else:
                    logger.info(
                        f"DataSkillSelector selected skill: {skill['name']} "
                        f"for data source type: {source_type}",
                    )

                skill_content = get_prompt_from_file(
                    skill["dir"],
                    return_json=False,
                )
                if skill_content:
                    selected_skills.append(skill_content)

            except Exception as e:
                logger.error(
                    f"DataSkillSelector selection failed: {str(e)} "
                    f"for data source type: {source_type}",
                )
                continue

        return selected_skills

    def register_skill_dir(self, skill_dir=_default_skill_path_base):
        """Load skills from all directories containing SKILL.md"""

        skills = []
        # Check the skill directory
        if not os.path.isdir(skill_dir):
            raise ValueError(
                f"The skill directory '{skill_dir}' does not exist or is "
                "not a directory.",
            )

        # Walk through all files and directories in skill_dir_base
        for root, dirs, _ in os.walk(skill_dir):
            # Process directories - look for SKILL.md
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                skill = self.register_skill(dir_path)
                if skill:
                    skills.append(skill)

        return skills

    def register_skill(self, path: str, name=None):
        """
        Register a new skill dynamically

        Args:
            name: Skill name
            path: Path to skill directory containing SKILL.md
        """
        try:
            # Resolve the skill path
            file_path = self._resolve_skill_path(path)
            if not file_path:
                raise FileNotFoundError("`SKILL.md` not found")

            # Parse the skill file
            skill = self._parse_skill_file(file_path, name)
            logger.info(
                f"Successfully registered skill '{skill['name']}' "
                f"from '{file_path}'",
            )

            return skill

        except Exception as e:
            logger.error(
                f"Failed to register skill '{skill['name']}' from "
                f"'{path}': {e}",
            )
            return None

    def _resolve_skill_path(self, path: str) -> str:
        """
        Resolve a skill path to the actual markdown file path

        Args:
            path: Path to skill markdown file or directory containing SKILL.md

        Returns:
            str: Path to the actual markdown file, or empty string if invalid
        """
        if os.path.isdir(path):
            skill_md_path = os.path.join(path, "SKILL.md")
            if not os.path.isfile(skill_md_path):
                logger.warning(f"Directory '{path}' does not contain SKILL.md")
                return ""
            return skill_md_path
        else:
            logger.warning(f"Invalid skill path: {path}")
            return ""

    def _parse_skill_file(self, file_path, name=None):
        """Parse a skill file and add it to skills_list"""

        # Check YAML Front Matter
        post = frontmatter.load(file_path)

        # Use directory name as skill name if not provided in YAML
        if name is None:
            dir_name = os.path.basename(os.path.dirname(file_path))
            name = post.get("name", dir_name)
        else:
            name = post.get("name", name)

        description = post.get("description", None)
        _type = post.get("type", None)

        if not name or not description or not _type:
            raise ValueError(
                f"The file '{file_path}' must have a YAML Front "
                "Matter including `name`, `description`, and `type` fields",
            )

        _type = _type if isinstance(_type, list) else [_type]
        if any(not SourceType.is_valid_source_type(t) for t in _type):
            raise ValueError(
                f"Type of file '{file_path}' must be a member "
                "(or a list of members) of SourceType",
            )

        name, description = str(name), str(description)
        _type = [SourceType(t) for t in _type]

        return DataSkill(
            name=name,
            description=description,
            type=_type,
            dir=file_path,
        )
