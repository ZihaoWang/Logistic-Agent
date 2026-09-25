"""Identity and delegation models for agent governance."""

from datetime import datetime

from pydantic import BaseModel, Field

SHIPMENT_RECOVERY_AGENT = "shipment-recovery-agent"
INVESTIGATION_AGENT = "investigation-agent"

SHIPMENT_RECOVERY_SCOPES: frozenset[str] = frozenset(
    {
        "shipment:read",
        "port:read",
        "route:read",
        "shipment:write",
        "reroute:request",
    }
)

INVESTIGATION_SCOPES: frozenset[str] = frozenset(
    {
        "shipment:read",
        "port:read",
        "route:read",
    }
)


class ActorIdentity(BaseModel):
    """Human or service actor on whose behalf an agent runs.

    Usage:
        Embedded in DelegationContext for every tool call.

    Fields:
        actor_id: Required stable actor identifier.
        actor_type: Optional actor kind; defaults to user.
        display_name: Optional human-readable label.
    """

    actor_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Stable actor identifier.",
    )
    actor_type: str = Field(
        default="user",
        min_length=1,
        max_length=32,
        description="Optional. Actor kind; defaults to user.",
    )
    display_name: str | None = Field(
        default=None,
        max_length=128,
        description="Optional. Human-readable label.",
    )


class DelegationContext(BaseModel):
    """User-to-agent delegation with scoped permissions.

    Usage:
        Attached to ExecutionContext for policy evaluation.

    Fields:
        actor: Required human actor identity.
        delegated_to: Required agent identity receiving delegation.
        scopes: Optional granted scopes; defaults to empty set.
        issued_at: Required delegation issue timestamp in UTC.
        expires_at: Optional delegation expiry timestamp in UTC.
    """

    actor: ActorIdentity = Field(
        ...,
        description="Required. Human actor identity.",
    )
    delegated_to: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Required. Agent identity receiving delegation.",
    )
    scopes: set[str] = Field(
        default_factory=set,
        description="Optional. Granted scopes; defaults to empty set.",
    )
    issued_at: datetime = Field(
        ...,
        description="Required. Delegation issue timestamp in UTC.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Optional. Delegation expiry timestamp in UTC.",
    )
