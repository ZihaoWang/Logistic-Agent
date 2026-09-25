"""Passthrough policy slot for ungoverned tool calls."""

from typing import Any

from pydantic import BaseModel

from agent_platform.models.execution import ExecutionContext
from agent_platform.models.tools import ToolResult


class PassthroughPolicySlot:
    """No-op policy slot used when governance is not wired."""

    async def check(
        self,
        tool_name: str,
        arguments: BaseModel,
        context: ExecutionContext | None = None,
    ) -> ToolResult[Any] | None:
        """Always allow the pipeline to continue."""
        _ = (tool_name, arguments, context)
        return None

    async def record_success(
        self,
        tool_name: str,
        arguments: BaseModel,
        context: ExecutionContext | None = None,
    ) -> None:
        """No-op for passthrough mode."""
        _ = (tool_name, arguments, context)
