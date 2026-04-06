# -*- coding: utf-8 -*-
import os
import time
from typing import Tuple

import dotenv
from pydantic import BaseModel, Field

from agentscope.message import Msg

from .utils import model_call_with_retry, get_prompt_from_file
from .ds_config import PROMPT_DS_BASE_PATH

dotenv.load_dotenv()


class ReportResponse(BaseModel):
    is_brief_response: bool = Field(
        ...,
        description=(
            "True if the response is a brief response; "
            "False if it includes a detailed report."
        ),
    )

    brief_response: str = Field(
        ...,
        description=(
            "The brief response content. "
            "When 'is_brief_response' is True, this field contains the full "
            "brief response following the Brief Response Template. "
            "When 'is_brief_response' is False, this field contains a concise "
            "markdown summary of the detailed report, highlighting key "
            "findings and insights."
        ),
        json_schema_extra={
            "example": (
                "The analysis shows a 15% increase in user engagement "
                "after the feature update."
            ),
        },
    )

    report_content: str = Field(
        ...,
        description=(
            "The detailed markdown report content following the "
            "Detailed Report Template. This field MUST be an empty "
            "string ('') when 'is_brief_response' is True. It MUST contain "
            "the full detailed report when 'is_brief_response' is False."
        ),
        json_schema_extra={
            "example": "### User Task Description...\n"
            "### Associated Data Sources...\n"
            "### Research Conclusion...\n### Task1...### Task2...",
        },
    )


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
            structured_model=ReportResponse,
        )

        end_time = time.time()
        print(f"Log to markdown took {end_time - start_time} seconds")

        return res.content[-1]["input"]

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

    async def generate_report(self) -> Tuple[str, str, str]:
        """
        responseFormat: {
           "is_brief_response": True,
           "brief_response": brief_response_content,
           "report_content": detailed_report_content
        }
        """
        markdown_content = await self._log_to_markdown()

        if (
            str(markdown_content.get("is_brief_response", False)).lower()
            == "true"
        ):
            # During brief response mode,
            # directly return the brief response to the user.
            return markdown_content.get("brief_response", ""), "", ""
        else:
            # In detailed report mode,
            # convert the detailed report to HTML and return it to the user;
            # if a brief summary of the report is needed,
            # it can be obtained through markdown_content["brief_response"].
            html_content = ""
            if os.getenv("ENABLE_HTML_REPORT", "ON").lower() != "off":
                html_content = await self._convert_to_html(
                    markdown_content.get("report_content", ""),
                )
            return (
                markdown_content.get("brief_response", ""),
                markdown_content.get("report_content", ""),
                html_content,
            )
