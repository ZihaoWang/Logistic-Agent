"""Base class for MCP tool backend fetchers."""

from typing import Any

from pydantic import BaseModel

from mcp_server.backend.base import BaseLogisticsClient


class BaseTool:
    """Fetch backend data for one MCP tool."""

    name: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]

    def __init__(self, backend: BaseLogisticsClient) -> None:
        """Store the backend client.

        Parameters:
            backend: Client used to call logistics-api.
        """
        self._backend = backend

    async def fetch(self, validated_input: BaseModel) -> dict[str, Any]:
        """Call the backend and return JSON shaped for output validation.

        Parameters:
            validated_input: Validated tool input model.

        Returns:
            Dict suitable for output model validation.

        Raises:
            BackendCallError: When the backend call fails.
        """
        raise NotImplementedError
