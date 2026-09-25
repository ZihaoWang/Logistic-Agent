"""Platform error model shared by tools and the agent runtime."""

from typing import Literal

from pydantic import BaseModel, Field

ErrorCategory = Literal[
    "validation",
    "authentication",
    "authorization",
    "policy",
    "approval",
    "budget",
    "timeout",
    "transport",
    "backend",
    "contract",
    "model",
    "internal",
]


class PlatformError(BaseModel):
    """Typed error returned inside a failed ToolResult.

    Usage:
        Created by the MCP gateway pipeline when validation, backend, or
        transport failures occur.

    Fields:
        code: Required stable machine-readable error code.
        category: Required error family for routing and metrics.
        message: Required short human-readable message.
        retryable: Required flag for whether a retry could succeed.
        details: Optional small structured facts about the failure.
    """

    code: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Stable machine-readable error code.",
    )
    category: ErrorCategory = Field(
        ...,
        description="Required. Error family for routing and metrics.",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Required. Short human-readable message.",
    )
    retryable: bool = Field(
        ...,
        description="Required. Whether a later retry could succeed.",
    )
    details: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict,
        description="Optional. Small structured facts about the failure.",
    )
