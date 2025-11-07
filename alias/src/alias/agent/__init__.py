# -*- coding: utf-8 -*-
"""Agent module for Alias"""

__all__ = ["agents", "tools", "mock", "utils"]

# Import submodules to make them accessible via alias.agent.agents, etc.
from . import agents  # noqa: E402, F401
from . import tools  # noqa: E402, F401
from . import mock  # noqa: E402, F401
from . import utils  # noqa: E402, F401
