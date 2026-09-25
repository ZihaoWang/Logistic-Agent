"""Environment-backed settings for the policy engine."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PolicySettings(BaseSettings):
    """Configuration values used by policy evaluation.

    Usage:
        Loaded from environment variables or .env for local development.

    Fields:
        reroute_cost_limit_eur: Optional reroute cost ceiling; defaults to 2000.
        approval_ttl_seconds: Optional approval expiry window; defaults to 1800.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    reroute_cost_limit_eur: float = Field(
        default=2000.0,
        gt=0,
        alias="REROUTE_COST_LIMIT_EUR",
        description="Optional. Reroute cost ceiling in EUR; defaults to 2000.",
    )
    approval_ttl_seconds: int = Field(
        default=1800,
        ge=60,
        le=86400,
        alias="APPROVAL_TTL_SECONDS",
        description="Optional. Approval expiry window in seconds; defaults to 1800.",
    )
