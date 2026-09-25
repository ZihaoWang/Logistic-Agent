"""Policy slot protocol for the MCP gateway pipeline."""

from typing import Any, Protocol

from pydantic import BaseModel

from agent_platform.models.execution import ExecutionContext
from agent_platform.models.tools import ToolResult


class BasePolicySlot(Protocol):
    """Policy hook inserted before backend calls."""

    async def check(
        self,
        tool_name: str,
        arguments: BaseModel,
        context: ExecutionContext | None = None,
    ) -> ToolResult[Any] | None:
        """Return a ToolResult to stop, or None to call the backend.

        Parameters:
            tool_name: Registered MCP tool name.
            arguments: Validated tool input model.
            context: Optional execution context for governed calls.

        Returns:
            ToolResult to short-circuit the pipeline, or None to continue.
        """
        ...

    async def record_success(
        self,
        tool_name: str,
        arguments: BaseModel,
        context: ExecutionContext | None = None,
    ) -> None:
        """Record post-success side effects such as approval consumption."""
        ...
