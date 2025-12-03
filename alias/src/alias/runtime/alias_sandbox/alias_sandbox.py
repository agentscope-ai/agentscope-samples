# -*- coding: utf-8 -*-
import io
from typing import Optional, Union, Tuple

from loguru import logger
from agentscope_runtime.sandbox.utils import build_image_uri
from agentscope_runtime.sandbox.registry import SandboxRegistry
from agentscope_runtime.sandbox.enums import SandboxType
from agentscope_runtime.sandbox.box.base import BaseSandbox
from agentscope_runtime.sandbox.box.gui import GUIMixin


@SandboxRegistry.register(
    build_image_uri("runtime-sandbox-alias"),
    sandbox_type="alias",
    security_level="high",
    timeout=30,
    description="Alias Sandbox",
)
class AliasSandbox(GUIMixin, BaseSandbox):
    def __init__(  # pylint: disable=useless-parent-delegation
        self,
        sandbox_id: Optional[str] = None,
        timeout: int = 3000,
        base_url: Optional[str] = None,
        bearer_token: Optional[str] = None,
        sandbox_type: SandboxType = "alias",
    ):
        super().__init__(
            sandbox_id=sandbox_id,
            timeout=timeout,
            base_url=base_url,
            bearer_token=bearer_token,
            sandbox_type=sandbox_type,
        )

    def download_file(
        self,
        file_path: str,
    ) -> Optional[Union[Tuple[bytes, str], dict]]:
        """
        Retrieve a file from the /workspace directory.

        Args:
            file_path: Path to the file within /workspace
        """
        try:
            # pylint: disable=protected-access
            client = self.manager_api._establish_connection(
                self.sandbox_id,
            )

            endpoint = f"{client.base_url}/workspace/files"
            params = {"file_path": file_path}

            response = client.session.get(
                endpoint,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            content = response.content
            mime_type = response.headers.get(
                "Content-Type",
                "application/octet-stream",
            )
            return content, mime_type

        except Exception as e:
            logger.error(f"An error occurred while retrieving the file: {e}")
            return None

    def upload_file(self, file_path: str, content: bytes) -> bool:
        """
        Upload a binary file to the /workspace directory.

        Args:
            file_path: Path to the file within /workspace
            content: Binary content of the file to upload

        Returns:
            bool: True if upload was successful, False otherwise
        """
        try:
            # pylint: disable=protected-access
            client = self.manager_api._establish_connection(
                self.sandbox_id,
            )

            endpoint = f"{client.base_url}/workspace/upload"
            # Use the full file_path as filename
            # since backend uses file.filename
            # Ensure path is relative to /workspace
            if file_path.startswith("/workspace/"):
                filename = file_path[len("/workspace/") :]
            elif file_path.startswith("/"):
                filename = file_path[1:]
            else:
                filename = file_path

            files = {
                "file": (
                    filename,
                    io.BytesIO(content),
                    "application/octet-stream",
                ),
            }

            original_content_type = client.session.headers.get("Content-Type")
            if "Content-Type" in client.session.headers:
                del client.session.headers["Content-Type"]

            logger.debug(
                f"Uploading file to {endpoint}, filename: {filename}, "
                f"size: {len(content)}",
            )

            try:
                response = client.session.post(
                    endpoint,
                    files=files,
                    timeout=self.timeout,
                )
            finally:
                # Restore original Content-Type if it existed
                if original_content_type:
                    client.session.headers[
                        "Content-Type"
                    ] = original_content_type

            # Log response for debugging
            logger.debug(f"Response status: {response.status_code}")
            if response.status_code != 200:
                logger.debug(f"Response text: {response.text}")

            response.raise_for_status()

            result = response.json()
            logger.info(
                f"File uploaded successfully: {file_path}, "
                f"size: {result.get('file_size', len(content))}",
            )
            return True
        except Exception as e:
            logger.error(f"An error occurred while uploading the file: {e}")
            # Log response details for debugging
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.text
                    logger.error(f"Response details: {error_detail}")
                except Exception:
                    pass
            return False
