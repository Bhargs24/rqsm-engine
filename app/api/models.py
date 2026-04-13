"""Request and response models for conversational API endpoints."""
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SessionCreateResponse(BaseModel):
    """Returned after document ingest and role assignment."""

    session_id: str
    filename: str
    total_units: int
    roles_assigned: int
    state: Dict[str, Any]


class StartConversationResponse(BaseModel):
    """Returned when conversation starts and first tutor response is generated."""

    session_id: str
    role: str
    unit_index: int
    total_units: int
    response: str
    state: Dict[str, Any]


class UserMessageRequest(BaseModel):
    """User message payload for normal engaged conversation flow."""

    message: str = Field(..., min_length=1)


class UserMessageResponse(BaseModel):
    """Generated tutor response for a user message."""

    session_id: str
    role: str
    unit_index: int
    response: str
    state: Dict[str, Any]


class InterruptResponse(BaseModel):
    """Result of clicking interrupt in UI."""

    session_id: str
    success: bool
    message: str
    interrupted_at_unit: Optional[int] = None
    state: Dict[str, Any]


class InterruptMessageRequest(BaseModel):
    """User interruption question payload."""

    message: str = Field(..., min_length=1)


class InterruptMessageResponse(BaseModel):
    """Tutor response to interruption question while in interrupted state."""

    session_id: str
    role: str
    interrupted_unit: int
    response: str
    can_resume: bool
    state: Dict[str, Any]


class ResumeResponse(BaseModel):
    """Result of resuming conversation after interruption."""

    session_id: str
    success: bool
    message: str
    resuming_from_unit: Optional[int] = None
    state: Dict[str, Any]


class NextUnitResponse(BaseModel):
    """Result of advancing to the next unit."""

    session_id: str
    success: bool
    completed: bool
    unit_index: int
    response: Optional[str] = None
    role: Optional[str] = None
    state: Dict[str, Any]


class SessionStateResponse(BaseModel):
    """Detailed in-memory session state for frontend polling."""

    session_id: str
    filename: str
    total_units: int
    current_unit_index: int
    current_role: Optional[str]
    state: Dict[str, Any]
