# -*- coding: utf-8 -*-
# tests/evaluation_test.py
import asyncio

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any, Tuple, Callable

from agentscope.message import Msg
from agentscope.model import DashScopeChatModel
from agentscope.agent import ReActAgent
from agentscope.evaluate import Task, ACEPhone, SolutionOutput, ACEBenchmark
from agentscope.tool import Toolkit

# Import the main module from the correct path
from evaluation.ace_bench import main as ace_main


class TestReActAgentSolution:
    """Test suite for the ReAct agent solution function"""

    @pytest.fixture
    def mock_task(self) -> Task:
        """Create a mock ACEBench task"""
        task = Mock(spec=Task)
        task.input = "Test input query"
        task.metadata = {
            "tools": self._create_mock_tools(),
            "phone": Mock(spec=ACEPhone),
        }
        return task

    @pytest.fixture
    def mock_pre_hook(self) -> Mock:
        """Create a mock pre-hook function"""
        return Mock()

    def _create_mock_tools(self) -> List[Tuple[Callable, Dict[str, Any]]]:
        """Create mock tool functions with schemas"""

        def mock_tool(*args, **kwargs):
            return "tool_response"

        tool_schema = {
            "name": "mock_tool",
            "description": "A mock tool for testing",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1": {"type": "string"},
                    "param2": {"type": "number"},
                },
                "required": ["param1"],
            },
        }

        return [(mock_tool, tool_schema)]

    @pytest.mark.asyncio
    async def test_agent_initialization(
        self,
        mock_task: Task,
        mock_pre_hook: Mock,
    ) -> None:
        """Test ReAct agent initialization with valid configuration"""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            # Run the solution function
            await ace_main.react_agent_solution(mock_task, mock_pre_hook)

            # Verify agent creation
            assert mock_task.metadata["tools"] is not None
            assert len(mock_task.metadata["tools"]) > 0

    @pytest.mark.asyncio
    async def test_tool_registration(
        self,
        mock_task: Task,
        mock_pre_hook: Mock,
    ) -> None:
        """Test tool registration in the toolkit"""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            with patch(
                "evaluation.ace_bench.main.Toolkit",
            ) as mock_toolkit_class:
                mock_toolkit = Mock(spec=Toolkit)
                mock_toolkit_class.return_value = mock_toolkit

                # Run the solution function
                await ace_main.react_agent_solution(mock_task, mock_pre_hook)

                # Verify tool registration calls
                tools = mock_task.metadata["tools"]
                assert mock_toolkit.register_tool_function.call_count == len(
                    tools,
                )

                # Verify all tools were registered
                for tool, schema in tools:
                    mock_toolkit.register_tool_function.assert_any_call(
                        tool,
                        json_schema=schema,
                    )

    @pytest.mark.asyncio
    async def test_agent_interaction(
        self,
        mock_task: Task,
        mock_pre_hook: Mock,
    ) -> None:
        """Test agent interaction with input messages"""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            with patch(
                "evaluation.ace_bench.main.ReActAgent",
            ) as mock_agent_class:
                mock_agent = Mock(spec=ReActAgent)
                mock_agent_class.return_value = mock_agent

                # Set up async response
                mock_agent.__call__ = AsyncMock()

                # Create input message
                msg_input = Msg("user", mock_task.input, role="user")

                # Run the solution function
                await ace_main.react_agent_solution(mock_task, mock_pre_hook)

                # Verify agent interaction
                mock_agent.print.assert_called_once_with(msg_input)
                mock_agent.__call__.assert_called_once_with(msg_input)

    @pytest.mark.asyncio
    async def test_solution_output(
        self,
        mock_task: Task,
        mock_pre_hook: Mock,
    ) -> None:
        """Test solution output format and content"""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            # Mock memory and phone responses
            mock_memory = AsyncMock()
            mock_memory.get_memory.return_value = [
                Msg(
                    "assistant",
                    "Test response",
                    role="assistant",
                    content=[
                        {
                            "type": "tool_use",
                            "content": {
                                "name": "mock_tool",
                                "arguments": {"param1": "test", "param2": 42},
                            },
                        },
                    ],
                ),
            ]

            mock_phone = Mock(spec=ACEPhone)
            mock_phone.get_current_state.return_value = {"status": "completed"}

            # Patch the phone in task metadata
            mock_task.metadata["phone"] = mock_phone

            # Patch the agent's memory property
            with patch.object(ReActAgent, "memory", mock_memory):
                # Run the solution function
                solution = await ace_main.react_agent_solution(
                    mock_task,
                    mock_pre_hook,
                )

                # Verify solution output
                assert isinstance(solution, SolutionOutput)
                assert solution.success is True
                assert solution.output == {"status": "completed"}
                assert len(solution.trajectory) == 1
                assert solution.trajectory[0]["name"] == "mock_tool"

    @pytest.mark.asyncio
    async def test_error_handling(
        self,
        mock_task: Task,
        mock_pre_hook: Mock,
    ) -> None:
        """Test error handling in the solution function"""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test_key"}):
            # Mock a failure case
            with patch(
                "evaluation.ace_bench.main.Toolkit.register_tool_function",
                side_effect=Exception("Registration error"),
            ):
                with pytest.raises(Exception) as exc_info:
                    await ace_main.react_agent_solution(
                        mock_task,
                        mock_pre_hook,
                    )

                assert "Registration error" in str(exc_info.value)


class TestMainFunction:
    """Test suite for the main function"""

    @pytest.fixture
    def mock_args(self) -> Mock:
        """Create mock command-line arguments"""
        args = Mock()
        args.data_dir = "/test/data"
        args.result_dir = "/test/results"
        args.n_workers = 2
        return args

    def test_directory_validation(self, mock_args: Mock) -> None:
        """Test directory validation in main function"""
        with patch(
            "evaluation.ace_bench.main.ArgumentParser.parse_args",
            return_value=mock_args,
        ):
            with patch("os.makedirs") as mock_makedirs:
                # Run main function
                asyncio.run(ace_main.main())

                # Verify directory creation
                mock_makedirs.assert_any_call("/test/data", exist_ok=True)
                mock_makedirs.assert_any_call("/test/results", exist_ok=True)

    @pytest.mark.asyncio
    async def test_evaluator_initialization(self, mock_args: Mock) -> None:
        """Test evaluator initialization"""
        with patch(
            "evaluation.ace_bench.main.ArgumentParser.parse_args",
            return_value=mock_args,
        ):
            with patch(
                "evaluation.ace_bench.main.RayEvaluator",
            ) as mock_evaluator_class:
                mock_evaluator = Mock()
                mock_evaluator_class.return_value = mock_evaluator

                # Run main function
                await ace_main.main()

                # Verify evaluator initialization
                mock_evaluator_class.assert_called_once()
                call_args = mock_evaluator_class.call_args[1]
                assert call_args["n_workers"] == 2
                assert isinstance(call_args["benchmark"], ACEBenchmark)
                assert call_args["benchmark"].data_dir == "/test/data"

    @pytest.mark.asyncio
    async def test_evaluation_execution(self, mock_args: Mock) -> None:
        """Test evaluation execution"""
        with patch(
            "evaluation.ace_bench.main.ArgumentParser.parse_args",
            return_value=mock_args,
        ):
            with patch(
                "evaluation.ace_bench.main.RayEvaluator",
            ) as mock_evaluator_class:
                mock_evaluator = Mock()
                mock_evaluator.run = AsyncMock()
                mock_evaluator_class.return_value = mock_evaluator

                # Run main function
                await ace_main.main()

                # Verify evaluation execution
                mock_evaluator.run.assert_called_once_with(
                    ace_main.react_agent_solution,
                )
