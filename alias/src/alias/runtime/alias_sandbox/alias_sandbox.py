# -*- coding: utf-8 -*-
from typing import Optional

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
            sandbox_id,
            timeout,
            base_url,
            bearer_token,
            sandbox_type,
        )
