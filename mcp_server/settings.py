"""Settings for the MCP gateway server."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class McpServerSettings(BaseSettings):
    """Environment-backed settings for mcp-gateway.

    Usage:
        Loaded from environment variables or .env for local development.

    Fields:
        logistics_api_url: Required base URL for logistics-api.
        host: Optional bind host; defaults to 127.0.0.1.
        port: Optional bind port; defaults to 8001.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    logistics_api_url: str = Field(
        default="http://localhost:8002",
        alias="LOGISTICS_API_URL",
        description="Required. Base URL for logistics-api.",
    )
    host: str = Field(
        default="127.0.0.1",
        alias="MCP_HOST",
        description="Optional. Bind host; defaults to 127.0.0.1.",
    )
    port: int = Field(
        default=8001,
        alias="MCP_PORT",
        ge=1,
        le=65535,
        description="Optional. Bind port; defaults to 8001.",
    )
