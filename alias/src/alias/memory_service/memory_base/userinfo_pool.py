# -*- coding: utf-8 -*-
import asyncio
import ast
import re
from typing import Any, List

from mem0.memory.setup import setup_config

from alias.memory_service.profiling_utils.logging_utils import setup_logging

from .base_vec_memory import BaseAsyncVectorMemory
from .prompt import EXTRACT_USER_INFO

logger = setup_logging()

setup_config()


class AsyncVectorUserInfoMemory(BaseAsyncVectorMemory):
    async def get_user_info_memory(self, content: Any) -> List[str]:
        """
        Extracts the User Info Memory from the given content.
        """
        try:
            memory_content = self._preprocess_content(content)
            user_prompt = (
                f"Please extract the user information from the following "
                f"content: \n'{memory_content}'"
            )

            await asyncio.sleep(2)
            user_info_response = await asyncio.to_thread(
                self.llm.generate_response,
                messages=[
                    {"role": "system", "content": EXTRACT_USER_INFO},
                    {"role": "user", "content": user_prompt},
                ],
            )

            facts = self._format_llm_output_to_list(user_info_response)
            return facts

        except Exception as exc:
            logger.warning(f"Error in get_user_info_memory: {exc}")
            return []

    def _format_llm_output_to_list(self, llm_output: str) -> List[str]:
        """
        Convert LLM output into a Python list of strings.
        """
        if not llm_output or not isinstance(llm_output, str):
            return []

        cleaned = llm_output.strip()
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)
        else:
            return []

        try:
            parsed_list = ast.literal_eval(cleaned)
            if isinstance(parsed_list, list):
                return [str(item).strip() for item in parsed_list]
            return []
        except (SyntaxError, ValueError):
            return []
