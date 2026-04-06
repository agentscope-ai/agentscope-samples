# -*- coding: utf-8 -*-

from alias.agent.tools.toolkit_hooks.text_post_hook import TextPostHook


class LongTextPostHook(TextPostHook):
    def __init__(self, sandbox):
        super().__init__(sandbox, budget=8194 * 10, auto_save=False)
