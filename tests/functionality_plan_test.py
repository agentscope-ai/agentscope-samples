# -*- coding: utf-8 -*-
import os
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from agentscope.message import Msg

# 设置环境变量
os.environ["DASHSCOPE_API_KEY"] = "test_api_key"

# 导入被测脚本
import functionality.plan.main_manual_plan as main_manual_plan

@pytest.mark.asyncio
async def test_plan_notebook_initialization() -> None:
    """验证 PlanNotebook 初始化"""
    with patch("functionality.plan.main_manual_plan.PlanNotebook", autospec=True) as mock_notebook:
        await main_manual_plan.main()
        mock_notebook.assert_called_once()

@pytest.mark.asyncio
async def test_subtasks_registration() -> None:
    """验证子任务注册"""
    with patch("functionality.plan.main_manual_plan.PlanNotebook.create_plan", autospec=True) as mock_plan:
        await main_manual_plan.main()
        mock_plan.assert_called_once()

@pytest.mark.asyncio
async def test_manual_plan_execution() -> None:
    """验证手动计划执行"""
    with patch("functionality.plan.main_manual_plan.UserAgent", autospec=True) as mock_user:
        mock_user.return_value.__call__.side_effect = lambda x: Msg(
            "user", "exit", "user"
        )
        await main_manual_plan.main()
        mock_user.assert_called_once()

if __name__ == "__main__":
    asyncio.run(pytest.main(["-v", __file__]))