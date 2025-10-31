# -*- coding: utf-8 -*-
from alias_sandbox import AliasSandbox

with AliasSandbox() as sandbox:
    print(sandbox.sandbox_id)
    print(sandbox.run_ipython_cell("import time\ntime.sleep(1)"))
    input("Press Enter to continue...")
