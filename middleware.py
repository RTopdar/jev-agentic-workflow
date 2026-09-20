"""Auto-mode middleware using TypeSafe/Jev for intent classification and tool gating."""

from typing import Any, Literal
from enum import Enum
from dataclasses import dataclass
from langchain_typesafe import TypeSafeClient
from langchain_typesafe.primitives import Choice, Noul


class IntentMode(str, Enum):
    """Intent classification for tool access control."""
    SAFE = "safe"
    RISKY = "risky"
    DANGEROUS = "dangerous"


@dataclass
class ToolGate:
    """Configuration for tool access control."""
    tool_name: str
    allowed_modes: set[IntentMode]
    reason: str


class AutoModeMiddleware:
    """
    Jev-powered middleware that classifies user intent and gates tool execution.

    Uses TypeSafe to classify requests as safe/risky/dangerous before allowing
    tool execution, implementing least-privilege access patterns.
    """

    def __init__(
        self,
        api_key: str | None = None,
        dangerous_tools: list[str] | None = None,
    ):
        """
        Initialize auto-mode middleware.

        Args:
            api_key: TypeSafe API key (falls back to TYPESAFE_API_KEY env var)
            dangerous_tools: List of tool names requiring explicit safety clearance
        """
        self.client = TypeSafeClient(api_key=api_key)
        self.dangerous_tools = dangerous_tools or ["bash", "sql", "delete"]
        self.gates = self._build_gates()

    def _build_gates(self) -> dict[str, ToolGate]:
        """Build tool access control rules."""
        return {
            "bash": ToolGate(
                tool_name="bash",
                allowed_modes={IntentMode.SAFE},
                reason="Shell execution requires explicit safe intent",
            ),
            "sql": ToolGate(
                tool_name="sql",
                allowed_modes={IntentMode.SAFE},
                reason="SQL changes require confirmed safe mode",
            ),
            "delete": ToolGate(
                tool_name="delete",
                allowed_modes={IntentMode.SAFE},
                reason="Deletions require confirmed safe mode",
            ),
        }

    async def classify_intent(
        self,
        user_input: str,
        context: dict[str, Any] | None = None,
    ) -> tuple[IntentMode, float]:
        """
        Classify user intent using Jev.

        Args:
            user_input: User's natural language request
            context: Optional context (recent actions, environment state)

        Returns:
            Tuple of (intent_mode, confidence)
        """
        state = {
            "request": user_input,
            **(context or {}),
        }

        intent_choice = Choice(
            instructions="Classify the user's intent regarding tool access and risk tolerance.",
            criteria={
                "safe": "Routine queries, reads, non-destructive changes within understood scope.",
                "risky": "Complex changes, external API calls, or actions with side effects.",
                "dangerous": "Destructive ops (delete/drop), system admin, credential access.",
            },
            question_id="intent_classification",
        )

        response = await self.client.ask(state=state, questions=[intent_choice])
        answer = response[0]

        mode = IntentMode(answer.choice)
        confidence = answer.confidence

        return mode, confidence

    async def can_execute_tool(
        self,
        tool_name: str,
        user_input: str,
        context: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        """
        Check if tool execution is allowed under current intent.

        Args:
            tool_name: Name of tool to execute
            user_input: User's request
            context: Optional context

        Returns:
            Tuple of (allowed, reason)
        """
        gate = self.gates.get(tool_name)
        if not gate:
            return True, f"No restrictions on {tool_name}"

        mode, confidence = await self.classify_intent(user_input, context)

        if mode not in gate.allowed_modes:
            return False, (
                f"{tool_name} blocked: intent classified as {mode.value} "
                f"(confidence: {confidence:.2%}). {gate.reason}"
            )

        if confidence < 0.6:
            return False, (
                f"{tool_name} blocked: low confidence ({confidence:.2%}) in intent classification. "
                "Please clarify your request."
            )

        return True, f"Tool allowed under {mode.value} mode (confidence: {confidence:.2%})"
