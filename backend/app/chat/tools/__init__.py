"""Tool registry — maps Python handlers to OpenAI function-calling schemas.

A tool handler receives parsed JSON `args` and a `ToolContext` (tenant scope
+ DB session) and returns a `ToolResult`. The registry exports the OpenAI
schema list and dispatches calls by name.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy.orm import Session


@dataclass
class ToolContext:
    tenant_id: str
    session: Session


@dataclass
class ToolResult:
    payload: dict
    # Citations only set by the KB search tool; agent collects these.
    citations: list[dict] = field(default_factory=list)
    # Renderable artifacts (e.g. chart specs) the UI displays under the reply.
    artifacts: list[dict] = field(default_factory=list)


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSONSchema
    handler: Callable[[dict, ToolContext], ToolResult]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def openai_schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    def dispatch(self, name: str, args: dict, ctx: ToolContext) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")
        return tool.handler(args, ctx)

    def has(self, name: str) -> bool:
        return name in self._tools


def build_default_registry() -> ToolRegistry:
    """Assemble the registry with all production tools."""
    from app.chat.tools.alerts_tool import ALERT_TOOLS
    from app.chat.tools.cameras_tool import CAMERA_TOOLS
    from app.chat.tools.charts_tool import CHART_TOOLS
    from app.chat.tools.kb_tool import KB_TOOLS

    registry = ToolRegistry()
    for tool in (*KB_TOOLS, *ALERT_TOOLS, *CAMERA_TOOLS, *CHART_TOOLS):
        registry.register(tool)
    return registry
