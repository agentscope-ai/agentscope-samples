# -*- coding: utf-8 -*-
import os
import json
import time
from typing import Tuple

import dotenv
from agentscope.message import Msg

from .utils import model_call_with_retry, get_prompt_from_file


from .ds_config import PROMPT_DS_BASE_PATH

dotenv.load_dotenv()


class ReportGenerator:
    def __init__(self, model, formatter, memory_log: str):
        self.model = model
        self.formatter = formatter
        self.log = memory_log
        self.REPORT_GENERATION_PROMPT = get_prompt_from_file(
            os.path.join(PROMPT_DS_BASE_PATH, "_log_to_markdown_prompt.md"),
            False,
        )
        self.BRIEF_RESPONSE_TEMPLATE = get_prompt_from_file(
            os.path.join(PROMPT_DS_BASE_PATH, "_brief_response_template.md"),
            False,
        )
        self.DETAILED_REPORT_TEMPLATE = get_prompt_from_file(
            os.path.join(PROMPT_DS_BASE_PATH, "_detailed_report_template.md"),
            False,
        )
        self.MARKDOWN_TO_HTML_PROMPT = get_prompt_from_file(
            os.path.join(PROMPT_DS_BASE_PATH, "_markdown_to_html_prompt.md"),
            False,
        )

    async def _log_to_markdown(self) -> str:
        start_time = time.time()
        user_prompt = self.REPORT_GENERATION_PROMPT.format(
            log=self.log,
            BRIEF_RESPONSE_TEMPLATE=self.BRIEF_RESPONSE_TEMPLATE,
            DETAILED_REPORT_TEMPLATE=self.DETAILED_REPORT_TEMPLATE,
        )
        system_prompt = (
            "You are a helpful assistant that generates a detailed "
            "insight report."
        )
        msgs = [
            Msg(
                "system",
                system_prompt,
                "system",
            ),
            Msg("user", user_prompt, "user"),
        ]

        res = await model_call_with_retry(
            self.model,
            self.formatter,
            msgs=msgs,
            msg_name="Report Generation",
        )

        raw_response = res.content[0]["text"]

        # TODO: More robust response cleaning
        if raw_response.strip().startswith("```json"):
            cleaned = raw_response.strip()[len("```json") :].lstrip("\n")
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].rstrip()
            response = cleaned
        else:
            response = raw_response.strip()
        end_time = time.time()
        # print(response)
        print(f"Log to markdown took {end_time - start_time} seconds")
        return response

    async def _convert_to_html(self, markdown_content: str) -> str:
        start_time = time.time()
        user_prompt = self.MARKDOWN_TO_HTML_PROMPT.format(
            markdown_content=markdown_content,
        )
        msgs = [
            Msg(
                "system",
                "You are a helpful assistant that converts markdown to html.",
                "system",
            ),
            Msg("user", user_prompt, "user"),
        ]
        response = await model_call_with_retry(
            self.model,
            self.formatter,
            msgs=msgs,
            msg_name="Markdown to HTML Conversion",
        )
        end_time = time.time()
        print(f"Convert to html took {end_time - start_time} seconds")
        return response.content[0]["text"]

    async def generate_report(self) -> Tuple[str, str]:
        markdown_response = await self._log_to_markdown()

        #  responseFormat: {
        #     "is_brief_response": True,
        #     "brief_response": brief_response_content,
        #     "report_content": detailed_report_content
        #  }

        try:
            markdown_content = json.loads(markdown_response)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Response content: {markdown_response}")
            raise

        if (
            str(markdown_content.get("is_brief_response", False)).lower()
            == "true"
        ):
            # During brief response mode,
            # directly return the brief response to the user.
            return markdown_content["brief_response"], ""
        else:
            # In detailed report mode,
            # convert the detailed report to HTML and return it to the user;
            # if a brief summary of the report is needed,
            # it can be obtained through markdown_content["brief_response"].
            return markdown_content[
                "brief_response"
            ], await self._convert_to_html(markdown_content["report_content"])
