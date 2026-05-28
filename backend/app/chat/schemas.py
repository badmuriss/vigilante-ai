"""Pydantic models for the chat API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Citation(BaseModel):
    idx: int
    doc_title: str
    snippet: str
    document_id: str | None = None


class ToolCallSummary(BaseModel):
    tool: str
    args: dict = Field(default_factory=dict)


class ChartPoint(BaseModel):
    label: str
    value: float


class ChartArtifact(BaseModel):
    kind: str = "chart"
    chart_type: str  # bar | line | pie
    title: str
    data: list[ChartPoint] = Field(default_factory=list)


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None


class AssistantMessage(BaseModel):
    role: str = "assistant"
    content: str
    citations: list[Citation] = Field(default_factory=list)
    tool_calls: list[ToolCallSummary] = Field(default_factory=list)
    charts: list[ChartArtifact] = Field(default_factory=list)


class ChatMessageResponse(BaseModel):
    conversation_id: str
    assistant_message: AssistantMessage
    latency_ms: int


class ConversationMessage(BaseModel):
    role: str
    content: str
    citations: list[Citation] = Field(default_factory=list)
    tool_calls: list[ToolCallSummary] = Field(default_factory=list)
    charts: list[ChartArtifact] = Field(default_factory=list)


class ConversationSummary(BaseModel):
    id: str
    title: str | None
    channel: str
    updated_at: datetime
    last_message_preview: str


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]


class ConversationDetail(BaseModel):
    id: str
    title: str | None
    channel: str
    updated_at: datetime
    messages: list[ConversationMessage]
