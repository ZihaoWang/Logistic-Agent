"""Policy slot placeholder for Phase 3 enforcement."""

from typing import Any, Protocol

from pydantic import BaseModel

from agent_platform.models.tools import ToolResult


class BasePolicySlot(Protocol):
    """Policy hook inserted before backend calls."""

    async def check(self, tool_name: str, arguments: BaseModel) -> ToolResult[Any] | None:
        """Return a ToolResult to stop, or None to call the backend.

        Parameters:
            tool_name: Registered MCP tool name.
            arguments: Validated tool input model.

        Returns:
            ToolResult to short-circuit the pipeline, or None to continue.
        """
        ...


class PassthroughPolicySlot:
    """No-op policy slot used in Phase 2."""

    async def check(self, tool_name: str, arguments: BaseModel) -> ToolResult[Any] | None:
        """Always allow the pipeline to continue.

        Parameters:
            tool_name: Registered MCP tool name.
            arguments: Validated tool input model.

        Returns:
            None so the backend call proceeds.
        """
        _ = (tool_name, arguments)
        return None
