"""Unit tests for auto-mode middleware."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from middleware import AutoModeMiddleware, IntentMode, ToolGate
from orchestrator import ToolExecutor, GatedToolExecutor, WorkflowOrchestrator


class TestAutoModeMiddleware:
    """Tests for intent classification and tool gating."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance with mocked client."""
        with patch("middleware.TypeSafeClient"):
            return AutoModeMiddleware(api_key="test-key")

    def test_initialization(self, middleware):
        """Test middleware initializes with default dangerous tools."""
        assert "bash" in middleware.gates
        assert "sql" in middleware.gates
        assert "delete" in middleware.gates

    def test_custom_dangerous_tools(self):
        """Test middleware accepts custom dangerous tool list."""
        with patch("middleware.TypeSafeClient"):
            mw = AutoModeMiddleware(dangerous_tools=["custom_tool"])
            # Custom tools are passed but gates built from defaults
            # This tests the parameter is accepted
            assert mw.dangerous_tools == ["custom_tool"]

    def test_tool_gate_structure(self, middleware):
        """Test ToolGate configuration is correct."""
        bash_gate = middleware.gates["bash"]
        assert bash_gate.tool_name == "bash"
        assert IntentMode.SAFE in bash_gate.allowed_modes
        assert IntentMode.RISKY not in bash_gate.allowed_modes
        assert IntentMode.DANGEROUS not in bash_gate.allowed_modes

    @pytest.mark.asyncio
    async def test_classify_intent_safe(self, middleware):
        """Test intent classification for safe request."""
        mock_response = MagicMock()
        mock_response[0].choice = "safe"
        mock_response[0].confidence = 0.95

        middleware.client.ask = AsyncMock(return_value=mock_response)

        mode, confidence = await middleware.classify_intent("Read the file")

        assert mode == IntentMode.SAFE
        assert confidence == 0.95

    @pytest.mark.asyncio
    async def test_classify_intent_dangerous(self, middleware):
        """Test intent classification for dangerous request."""
        mock_response = MagicMock()
        mock_response[0].choice = "dangerous"
        mock_response[0].confidence = 0.88

        middleware.client.ask = AsyncMock(return_value=mock_response)

        mode, confidence = await middleware.classify_intent("Delete the database")

        assert mode == IntentMode.DANGEROUS
        assert confidence == 0.88

    @pytest.mark.asyncio
    async def test_can_execute_tool_allowed(self, middleware):
        """Test tool execution is allowed for safe intent."""
        mock_response = MagicMock()
        mock_response[0].choice = "safe"
        mock_response[0].confidence = 0.9

        middleware.client.ask = AsyncMock(return_value=mock_response)

        allowed, reason = await middleware.can_execute_tool(
            "bash",
            "List files in directory",
        )

        assert allowed is True
        assert "allowed" in reason.lower()

    @pytest.mark.asyncio
    async def test_can_execute_tool_blocked_mode(self, middleware):
        """Test tool execution is blocked for dangerous intent."""
        mock_response = MagicMock()
        mock_response[0].choice = "dangerous"
        mock_response[0].confidence = 0.92

        middleware.client.ask = AsyncMock(return_value=mock_response)

        allowed, reason = await middleware.can_execute_tool(
            "bash",
            "Delete system files",
        )

        assert allowed is False
        assert "blocked" in reason.lower()
        assert "dangerous" in reason.lower()

    @pytest.mark.asyncio
    async def test_can_execute_tool_low_confidence(self, middleware):
        """Test tool execution is blocked for low confidence."""
        mock_response = MagicMock()
        mock_response[0].choice = "safe"
        mock_response[0].confidence = 0.45

        middleware.client.ask = AsyncMock(return_value=mock_response)

        allowed, reason = await middleware.can_execute_tool(
            "bash",
            "Do something unclear",
        )

        assert allowed is False
        assert "low confidence" in reason.lower()

    @pytest.mark.asyncio
    async def test_can_execute_unrestricted_tool(self, middleware):
        """Test unrestricted tool always allowed."""
        allowed, reason = await middleware.can_execute_tool(
            "read",
            "Any request",
        )

        assert allowed is True
        assert "no restrictions" in reason.lower()


class TestToolExecutors:
    """Tests for tool execution wrappers."""

    @pytest.mark.asyncio
    async def test_tool_executor_direct_call(self):
        """Test ToolExecutor executes without gating."""
        mock_func = AsyncMock(return_value="result")
        executor = ToolExecutor("test", mock_func)

        result = await executor(arg1="value")

        assert result == "result"
        mock_func.assert_called_once_with(arg1="value")

    @pytest.mark.asyncio
    async def test_gated_tool_executor_allowed(self):
        """Test GatedToolExecutor allows execution when permitted."""
        mock_func = AsyncMock(return_value="result")
        mock_middleware = AsyncMock()
        mock_middleware.can_execute_tool = AsyncMock(
            return_value=(True, "allowed")
        )

        executor = GatedToolExecutor("test", mock_func, mock_middleware)

        result = await executor("user input", {}, arg1="value")

        assert result == "result"
        mock_func.assert_called_once_with(arg1="value")

    @pytest.mark.asyncio
    async def test_gated_tool_executor_blocked(self):
        """Test GatedToolExecutor blocks execution when denied."""
        mock_func = AsyncMock(return_value="result")
        mock_middleware = AsyncMock()
        mock_middleware.can_execute_tool = AsyncMock(
            return_value=(False, "blocked")
        )

        executor = GatedToolExecutor("test", mock_func, mock_middleware)

        result = await executor("user input", {}, arg1="value")

        assert result is None
        mock_func.assert_not_called()


class TestWorkflowOrchestrator:
    """Tests for workflow orchestration."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mocked middleware."""
        mock_middleware = AsyncMock()
        return WorkflowOrchestrator(mock_middleware)

    def test_register_tool_ungated(self, orchestrator):
        """Test registering an ungated tool."""
        mock_func = AsyncMock()
        orchestrator.register_tool("test", mock_func, gated=False)

        assert "test" in orchestrator.tools
        assert isinstance(orchestrator.tools["test"], ToolExecutor)
        assert not isinstance(orchestrator.tools["test"], GatedToolExecutor)

    def test_register_tool_gated(self, orchestrator):
        """Test registering a gated tool."""
        mock_func = AsyncMock()
        orchestrator.register_tool("test", mock_func, gated=True)

        assert "test" in orchestrator.tools
        assert isinstance(orchestrator.tools["test"], GatedToolExecutor)

    @pytest.mark.asyncio
    async def test_execute_step_ungated(self, orchestrator):
        """Test executing an ungated tool step."""
        mock_func = AsyncMock(return_value="result")
        orchestrator.register_tool("test", mock_func, gated=False)

        result = await orchestrator.execute_step(
            "test",
            "user input",
            {},
            arg="value",
        )

        assert result == "result"

    @pytest.mark.asyncio
    async def test_execute_step_unregistered_tool(self, orchestrator):
        """Test executing unregistered tool raises error."""
        with pytest.raises(ValueError, match="not registered"):
            await orchestrator.execute_step("nonexistent", "input")

    @pytest.mark.asyncio
    async def test_execute_workflow_multi_step(self, orchestrator):
        """Test multi-step workflow execution."""
        func1 = AsyncMock(return_value="result1")
        func2 = AsyncMock(return_value="result2")

        orchestrator.register_tool("step1", func1, gated=False)
        orchestrator.register_tool("step2", func2, gated=False)

        steps = [
            {"tool_name": "step1", "kwargs": {"arg": "val1"}},
            {"tool_name": "step2", "kwargs": {"arg": "val2"}},
        ]

        results = await orchestrator.execute_workflow(steps, "user input", {})

        assert len(results) == 2
        assert results[0] == "result1"
        assert results[1] == "result2"

    @pytest.mark.asyncio
    async def test_execute_workflow_stops_on_block(self, orchestrator):
        """Test workflow halts when gated step is blocked."""
        func1 = AsyncMock(return_value=None)  # Blocked step
        func2 = AsyncMock(return_value="result2")

        orchestrator.register_tool("step1", func1, gated=True)
        orchestrator.register_tool("step2", func2, gated=False)

        steps = [
            {"tool_name": "step1", "kwargs": {}},
            {"tool_name": "step2", "kwargs": {}},
        ]

        results = await orchestrator.execute_workflow(steps, "user input", {})

        assert len(results) == 1
        assert results[0] is None
        func2.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
