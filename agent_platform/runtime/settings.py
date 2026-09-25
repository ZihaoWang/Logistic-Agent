"""Runtime configuration for the ADK agent."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeSettings(BaseSettings):
    """Environment-backed settings for the agent runtime."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    model_name: str = "gemini-2.5-flash-lite"
    max_concurrent_agent_runs: int = 4
    logistics_api_url: str = "http://127.0.0.1:8002"
    service_version: str = "0.1.0"
    model_input_cost_per_1k_tokens_usd: float = 0.000075
    model_output_cost_per_1k_tokens_usd: float = 0.0003
