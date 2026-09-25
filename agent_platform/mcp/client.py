"""MCP client wrapper that always returns ToolResult envelopes."""

from typing import Any

from fastmcp import FastMCP
from fastmcp.client import Client
from pydantic import ValidationError

from agent_platform.mcp.protocol import (
    CONTRACT_INPUT_INVALID,
    INTERNAL,
    TOOL_TIMEOUT,
    build_error,
    build_failed_result,
)
from agent_platform.mcp.registry import TOOL_REGISTRY, parse_tool_result_data
from agent_platform.models.tools import ToolResult


class McpClient:
    """Call MCP tools and normalize responses into ToolResult envelopes."""

    def __init__(self, server: FastMCP) -> None:
        """Store the in-memory FastMCP server instance.

        Parameters:
            server: FastMCP server created by create_mcp().
        """
        self._server = server
        self._client = Client(server)

    async def list_tools(self) -> list[str]:
        """Return registered MCP tool names.

        Returns:
            Sorted list of tool names exposed by the server.
        """
        async with self._client:
            tools = await self._client.list_tools()
        return sorted(tool.name for tool in tools)

    async def call(self, name: str, arguments: dict[str, Any]) -> ToolResult[Any]:
        """Call one MCP tool and return a validated ToolResult envelope.

        Parameters:
            name: MCP tool name.
            arguments: Raw tool arguments.

        Returns:
            ToolResult envelope for success or failure.
        """
        if name not in TOOL_REGISTRY:
            return build_failed_result(
                name,
                0,
                build_error(
                    INTERNAL,
                    "internal",
                    f"unknown tool: {name}",
                    retryable=False,
                ),
            )

        try:
            async with self._client:
                raw_result = await self._client.call_tool(name, arguments)
        except TimeoutError:
            return build_failed_result(
                name,
                0,
                build_error(
                    TOOL_TIMEOUT,
                    "timeout",
                    "tool call timed out",
                    retryable=True,
                ),
            )
        except Exception as exc:  # noqa: BLE001
            message = str(exc).lower()
            if "validation" in message or "invalid" in message or "required" in message:
                return build_failed_result(
                    name,
                    0,
                    build_error(
                        CONTRACT_INPUT_INVALID,
                        "validation",
                        "tool arguments failed input validation",
                        retryable=False,
                        details={"reason": str(exc)},
                    ),
                )
            return build_failed_result(
                name,
                0,
                build_error(
                    INTERNAL,
                    "internal",
                    f"mcp call failed: {exc}",
                    retryable=False,
                ),
            )

        payload: Any = raw_result.structured_content
        if payload is None and raw_result.data is not None:
            data = raw_result.data
            if hasattr(data, "model_dump"):
                payload = data.model_dump(mode="json")
            elif isinstance(data, dict):
                payload = data

        if payload is None:
            return build_failed_result(
                name,
                0,
                build_error(
                    INTERNAL,
                    "internal",
                    "mcp tool returned no structured content",
                    retryable=False,
                ),
            )

        try:
            result = ToolResult[Any].model_validate(payload)
        except ValidationError as exc:
            return build_failed_result(
                name,
                0,
                build_error(
                    INTERNAL,
                    "internal",
                    "mcp tool returned an invalid ToolResult envelope",
                    retryable=False,
                    details={"error_count": len(exc.errors())},
                ),
            )

        if result.status == "success" and result.data is not None:
            try:
                parse_tool_result_data(name, result.data)
            except ValidationError as exc:
                return build_failed_result(
                    name,
                    result.metadata.latency_ms,
                    build_error(
                        "CONTRACT_OUTPUT_INVALID",
                        "contract",
                        "tool data failed output validation",
                        retryable=False,
                        details={"error_count": len(exc.errors())},
                    ),
                )

        if result.metadata.tool_name != name:
            result = result.model_copy(
                update={"metadata": result.metadata.model_copy(update={"tool_name": name})},
            )
        return result
