from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

Priority = Literal["low", "medium", "high", "urgent"]


class MessageState(BaseModel):
    """LangGraph state for one message as it moves through the pipeline."""

    id: str
    timestamp: datetime
    sender: str
    group_id: str
    raw_text: str
    is_task: Optional[bool] = None
    title: Optional[str] = None
    due_date: Optional[str] = None
    assignee: Optional[str] = None
    priority: Optional[Priority] = None
    needs_review: bool = False
    error: Optional[str] = None


class ClassificationExtraction(BaseModel):
    """Structured output contract for the single Gemini classify+extract call."""

    is_task: bool
    title: Optional[str] = None
    due_date: Optional[str] = None
    assignee: Optional[str] = None
    priority: Optional[Priority] = None
