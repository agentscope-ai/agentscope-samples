# tests/evaluation_test.py
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any, Tuple, Callable

import pytest
from agentscope.evaluate import Task, ACEPhone, ACEBenchmark

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
        """Create a mock pre-hook function that returns None"""

        def pre_hook_return(*args, **kwargs):
            """Mock function that returns None (no modifications)"""
            return None

        mock = Mock()
        mock.__name__ = "save_logging"
        mock.side_effect = pre_hook_return  # ✅ Return None to avoid parameter pollution
        return mock

    def _create_mock_tools(self) -> List[Tuple[Callable, Dict[str, Any]]]:
        """Create mock tool functions with schemas"""

        def mock_tool(*args, **kwargs):
            return "tool_response"

        tool_schema = {
            "type": "function",
            "function": {
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
            },
        }

        return [(mock_tool, tool_schema)]

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
    def mock_args(self, tmpdir) -> Mock:
        """Create mock command-line arguments with temporary directories"""
        args = Mock()
        args.data_dir = str(tmpdir / "data")
        args.result_dir = str(tmpdir / "results")
        args.n_workers = 2
        return args

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
                mock_evaluator = AsyncMock()
                mock_evaluator_class.return_value = mock_evaluator

                # ✅ Simulate _download_data and _load_data
                with patch("agentscope.evaluate._ace_benchmark._ace_benchmark.ACEBenchmark._download_data"):
                    with patch("agentscope.evaluate._ace_benchmark._ace_benchmark.ACEBenchmark._load_data", return_value=[]):
                        # Run main function
                        await ace_main.main()

                # Verify evaluator initialization
                mock_evaluator_class.assert_called_once()
                call_args = mock_evaluator_class.call_args[1]
                assert call_args["n_workers"] == 2
                assert isinstance(call_args["benchmark"], ACEBenchmark)
                assert call_args["benchmark"].data_dir == mock_args.data_dir

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
                mock_evaluator = AsyncMock()
                mock_evaluator.run = AsyncMock()
                mock_evaluator_class.return_value = mock_evaluator

                # ✅ Simulate _download_data and _load_data
                with patch("agentscope.evaluate._ace_benchmark._ace_benchmark.ACEBenchmark._download_data"):
                    with patch("agentscope.evaluate._ace_benchmark._ace_benchmark.ACEBenchmark._load_data", return_value=[]):
                        # Run main function
                        await ace_main.main()

                # Verify evaluation execution
                mock_evaluator.run.assert_called_once_with(
                    ace_main.react_agent_solution,
                )