# -*- coding: utf-8 -*-
from ..games.game_werewolves import prompt


def test_english_prompts_placeholders() -> None:
    """验证英文提示包含占位符"""
    assert "{name}" in prompt.EnglishPrompts.to_dead_player
    assert "{witch_name}" in prompt.EnglishPrompts.to_witch_resurrect


def test_chinese_prompts_placeholders() -> None:
    """验证中文提示包含占位符"""
    assert "{name}" in prompt.ChinesePrompts.to_dead_player
    assert "{witch_name}" in prompt.ChinesePrompts.to_witch_resurrect
