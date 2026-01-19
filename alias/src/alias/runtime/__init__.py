# -*- coding: utf-8 -*-
"""Runtime module for Alias"""

__all__ = ["alias_sandbox", "runtime_compat"]

# Import submodule to make it accessible via alias.runtime.alias_sandbox
from . import alias_sandbox  # noqa: E402, F401
from . import runtime_compat  # noqa: E402, F401
