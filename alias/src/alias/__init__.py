# -*- coding: utf-8 -*-
"""Alias - Beta version"""

__version__ = "0.2.0"

__all__ = ["agent", "runtime", "__version__"]

# Import submodules to make them accessible via alias.agent, alias.runtime
# Import at the end to avoid circular import issues
from . import agent  # noqa: E402, F401
from . import runtime  # noqa: E402, F401
