"""Request and response models for conversational API endpoints."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GroupMessage(BaseModel):
    """One voice's turn inside a group exchange.

    A topic opener typically returns 3 of these (primary + 2 chime-ins); a
    reply to a user message typically returns 2 (primary reply + 1 chime-in).
    The frontend renders each as its own role-coloured bubble.
    """

    role: str
    text: str
    is_nudge: bool = False


class UnitPreview(BaseModel):
    """Frontend-friendly snapshot of a semantic unit."""

    index: int
    title: str
    word_count: int
    section_type: str
    preview: str


class DocumentInsights(BaseModel):
    """Summary of what the processor extracted and segmented."""

    total_words: int
    avg_words_per_unit: float
    avg_cohesion: float
    sections: Dict[str, int]
    unit_previews: list[UnitPreview]


class SessionCreateResponse(BaseModel):
    """Returned after document ingest and role assignment."""

    session_id: str
    filename: str
    total_units: int
    roles_assigned: int
    session_mode: str = "study_group"
    selected_roles: List[str] = Field(default_factory=list)
    debate_personas: Optional[List[Dict[str, Any]]] = None
    state: Dict[str, Any]
    insights: DocumentInsights


class StartConversationResponse(BaseModel):
    """Returned when conversation starts and first tutor response is generated."""

    session_id: str
    role: str
    unit_index: int
    total_units: int
    response: str  # last message's text (back-compat)
    messages: List[GroupMessage] = Field(default_factory=list)
    auto_nudge: bool = False
    state: Dict[str, Any]


class UserMessageRequest(BaseModel):
    """User message payload for normal engaged conversation flow."""

    message: str = Field(..., min_length=1)


class UserMessageResponse(BaseModel):
    """Generated tutor response for a user message."""

    session_id: str
    role: str
    unit_index: int
    response: str  # last message's text (back-compat)
    messages: List[GroupMessage] = Field(default_factory=list)
    auto_nudge: bool = False
    state: Dict[str, Any]


class InterruptRequest(BaseModel):
    """Optional payload for interrupt action."""

    pass


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
    messages: List[GroupMessage] = Field(default_factory=list)
    can_resume: bool
    state: Dict[str, Any]


class ResumeResponse(BaseModel):
    """Result of resuming conversation after interruption."""

    session_id: str
    success: bool
    message: Optional[str] = None
    resuming_from_unit: Optional[int] = None
    unit_index: Optional[int] = None
    role: Optional[str] = None
    response: Optional[str] = None
    messages: List[GroupMessage] = Field(default_factory=list)
    state: Dict[str, Any]


class ResumeRequest(BaseModel):
    """Resume payload with restart option for current topic."""

    from_start: bool = False


class NextUnitRequest(BaseModel):
    """Optional payload for advancing to next unit."""

    pass


class NextUnitResponse(BaseModel):
    """Result of advancing to the next unit."""

    session_id: str
    success: bool
    completed: bool
    unit_index: int
    total_units: Optional[int] = None
    response: Optional[str] = None
    role: Optional[str] = None
    messages: List[GroupMessage] = Field(default_factory=list)
    auto_nudge: bool = False
    state: Dict[str, Any]


class SessionStateResponse(BaseModel):
    """Detailed in-memory session state for frontend polling."""

    session_id: str
    filename: str
    total_units: int
    current_unit_index: int
    current_role: Optional[str]
    session_mode: str = "study_group"
    selected_roles: Optional[List[str]] = None
    debate_personas: Optional[List[Dict[str, Any]]] = None
    state: Dict[str, Any]
