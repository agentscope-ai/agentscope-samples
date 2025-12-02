# -*- coding: utf-8 -*-
from io import BytesIO
import os
import base64
import tempfile
import requests
import dashscope
from agentscope.tool import ToolResponse
from agentscope.message import TextBlock

from alias.agent.tools.sandbox_util import (
    get_workspace_file,
)
from alias.runtime.alias_sandbox import AliasSandbox


def _get_binary_buffer(
    sandbox: AliasSandbox,
    audio_file_url: str,
):
    if audio_file_url.startswith(("http://", "https://")):
        response = requests.get(audio_file_url)
        response.raise_for_status()
        audio_buffer = BytesIO(response.content)
    else:
        audio_buffer = BytesIO(
            base64.b64decode(get_workspace_file(sandbox, audio_file_url)),
        )
    return audio_buffer


class DashScopeMultiModalTools:
    """
    A set of multi-modal tools based on DashScope models.
    Work with multi-modal content in sandbox and publicly accessible online.
    """

    def __init__(
        self,
        sandbox: AliasSandbox,
        dashscope_api_key: str,
    ):
        self.sandbox = sandbox
        self.api_key = dashscope_api_key

    def dashscope_audio_to_text(
        self,
        audio_file_url: str,
        language: str = "en",
    ) -> ToolResponse:
        """
        Convert an audio file to text using DashScope's transcription service.

        Args:
            audio_file_url (`str`):
                The file path or URL to the audio file that needs to be
                transcribed.
            language (`str`, defaults to `"en"`):
                The language of the input audio in
                `ISO-639-1 format \
                <https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes>`_
                (e.g., "en", "zh", "fr"). Improves accuracy and latency.

        Returns:
            `ToolResponse`:
                A ToolResponse containing the generated content
                (ImageBlock/TextBlock/AudioBlock) or error information if the
                operation failed.
        """

        try:
            # Handle different types of audio file URLs
            if audio_file_url.startswith(("http://", "https://")):
                # For web URLs, use the URL directly
                audio_source = audio_file_url
            else:
                # For local files, save to a temporary file
                audio_buffer = _get_binary_buffer(
                    sandbox=self.sandbox,
                    audio_file_url=audio_file_url,
                )

                # Create a temporary file
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=os.path.splitext(audio_file_url)[1],
                ) as temp_file:
                    temp_file.write(audio_buffer.getvalue())
                    audio_source = temp_file.name

            messages = [
                {
                    "role": "system",
                    "content": [
                        {
                            "text": "Transcript the content in the audio "
                            "to text.",
                        },
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "audio": audio_source,
                        },
                    ],
                },
            ]

            response = dashscope.MultiModalConversation.call(
                api_key=self.api_key,
                model="qwen3-asr-flash",
                messages=messages,
                asr_options={
                    "enable_lid": True,
                    "language": language,
                },
            )

            # Clean up temporary file if created
            if not audio_file_url.startswith(("http://", "https://")):
                try:
                    os.unlink(audio_source)
                except Exception as _:  # noqa: F841
                    pass

            content = response.output["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = content[0]["text"]
            if content is not None:
                return ToolResponse(
                    [
                        TextBlock(
                            type="text",
                            text=content,
                        ),
                    ],
                )
            else:
                return ToolResponse(
                    [
                        TextBlock(
                            type="text",
                            text="Error: Failed to generate text from audio",
                        ),
                    ],
                )
        except Exception as _:  # noqa: F841
            import traceback

            return ToolResponse(
                [
                    TextBlock(
                        type="text",
                        text="Error: Failed to transcribe audio: "
                        f"{traceback.format_exc()}",
                    ),
                ],
            )

    def dashscope_image_to_text(
        self,
        image_url: str,
        prompt: str = "Describe the image",
        model: str = "qwen-vl-plus",
    ) -> ToolResponse:
        """Generate text based on the given images.

        Args:
            image_url (`str`):
                The url of single or multiple images.
            prompt (`str`, defaults to 'Describe the image' ):
                The text prompt.
            model (`str`, defaults to 'qwen-vl-plus'):
                The model to use in DashScope MultiModal API.

        Returns:
            `ToolResponse`:
                A ToolResponse containing the generated content
                (ImageBlock/TextBlock/AudioBlock) or error information if the
                operation failed.
        """

        # Handle different types of image file URLs
        if image_url.startswith(("http://", "https://")):
            # For web URLs, use the URL directly
            image_source = image_url
        else:
            # For local files, save to a temporary file
            image_buffer = _get_binary_buffer(
                self.sandbox,
                image_url,
            )

            suffix = os.path.splitext(image_url)[1].lower() or ".png"
            # Create a temporary file
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            ) as temp_file:
                temp_file.write(image_buffer.getvalue())
                image_source = temp_file.name

        contents = []
        # Convert image paths according to the model requirements
        contents.append(
            {
                "image": image_source,
            },
        )
        # append text
        contents.append({"text": prompt})

        # currently only support one round of conversation
        # if multiple rounds of conversation are needed,
        # it would be better to implement an Agent class
        sys_message = {
            "role": "system",
            "content": [{"text": "You are a helpful assistant."}],
        }
        user_message = {
            "role": "user",
            "content": contents,
        }
        messages = [sys_message, user_message]
        try:
            response = dashscope.MultiModalConversation.call(
                model=model,
                messages=messages,
                api_key=self.api_key,
            )
            content = response.output["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = content[0]["text"]
            if content is not None:
                return ToolResponse(
                    [
                        TextBlock(
                            type="text",
                            text=content,
                        ),
                    ],
                )
            else:
                return ToolResponse(
                    [
                        TextBlock(
                            type="text",
                            text="Error: Failed to generate text",
                        ),
                    ],
                )
        except Exception as e:
            import traceback

            print(traceback.format_exc())
            return ToolResponse(
                [
                    TextBlock(
                        type="text",
                        text=f"Failed to generate text: {str(e)}",
                    ),
                ],
            )
