"""Scripted BaseLlm implementation for deterministic e2e tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types


class ScriptedLlm(BaseLlm):
    """Return predetermined function calls and final text for tests."""

    model: str = "scripted-test"
    steps: list[dict[str, Any]]
    step_index: int = 0

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r"scripted-test.*"]

    async def generate_content_async(
        self,
        llm_request: LlmRequest,
        stream: bool = False,
    ) -> AsyncGenerator[LlmResponse, None]:
        """Yield the next scripted model step."""
        if self.step_index >= len(self.steps):
            yield LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="Done.")],
                ),
            )
            return

        step = self.steps[self.step_index]
        self.step_index += 1

        if "function_call" in step:
            function_call = step["function_call"]
            yield LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name=function_call["name"],
                                args=function_call["args"],
                            ),
                        ),
                    ],
                ),
            )
            return

        text = str(step.get("text", ""))
        yield LlmResponse(
            content=types.Content(role="model", parts=[types.Part(text=text)]),
        )
