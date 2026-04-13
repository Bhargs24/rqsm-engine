"""Unit tests for in-memory conversation runtime."""
import io

from fastapi import UploadFile

from app.document.segmenter import SemanticUnit
from app.roles.role_assignment import RoleAssignment, RoleScore
from app.roles.role_templates import RoleType, role_library
from app.session.runtime import ConversationRuntime
from app.state_machine.conversation_state import ConversationState


class DummyProcessor:
    """Simple fake processor for runtime tests."""

    def __init__(self, units):
        self._units = units

    def process_document(self, _path):
        return self._units


class DummyAssigner:
    """Simple fake assigner for runtime tests."""

    def __init__(self, assignments):
        self._assignments = assignments

    def assign_roles(self, _semantic_units, balance_roles=True):
        return self._assignments


def _make_unit(position: int, text: str) -> SemanticUnit:
    return SemanticUnit(
        id=f"S0_{position}",
        title="Intro",
        text=text,
        document_section="body",
        position=position,
        similarity_score=0.9,
        word_count=len(text.split()),
        metadata={},
    )


def _make_assignment(unit: SemanticUnit, role: RoleType) -> RoleAssignment:
    return RoleAssignment(
        semantic_unit=unit,
        assigned_role=role,
        role_template=role_library.get_role(role),
        score=RoleScore(
            role_type=role,
            total_score=0.8,
            structural_score=0.8,
            lexical_score=0.8,
            topic_score=0.8,
        ),
        confidence=0.8,
    )


def test_runtime_full_flow_with_fallback(monkeypatch):
    """Runtime supports start, message, interrupt, resume, and next flow in memory."""
    unit0 = _make_unit(0, "Machine learning models learn patterns from data.")
    unit1 = _make_unit(1, "Neural networks contain layers and activation functions.")
    assignments = [
        _make_assignment(unit0, RoleType.EXPLAINER),
        _make_assignment(unit1, RoleType.SUMMARIZER),
    ]

    runtime = ConversationRuntime()
    runtime._llm_available = False

    monkeypatch.setattr(runtime, "_get_processor", lambda: DummyProcessor([unit0, unit1]))
    monkeypatch.setattr(runtime, "_get_assigner", lambda: DummyAssigner(assignments))

    upload = UploadFile(filename="doc.txt", file=io.BytesIO(b"hello"))
    session = runtime.create_session_from_uploaded_file(upload)

    assert session.state_machine.context.current_state == ConversationState.READY
    assert session.state_machine.context.total_units == 2

    start = runtime.start_conversation(session.session_id)
    assert start["unit_index"] == 0
    assert start["role"] == RoleType.EXPLAINER.value
    assert "fallback mode" in start["response"] or "new section" in start["response"]

    reply = runtime.send_user_message(session.session_id, "can you clarify this?")
    assert reply["unit_index"] == 0
    assert reply["role"] == RoleType.EXPLAINER.value

    interrupt = runtime.interrupt(session.session_id)
    assert interrupt["success"] is True
    assert interrupt["state"]["current_state"] == "interrupted"

    interruption_response = runtime.answer_interruption(
        session.session_id,
        "what are common mistakes here?",
    )
    assert interruption_response["can_resume"] is True
    assert interruption_response["state"]["current_state"] == "interrupted"

    resumed = runtime.resume(session.session_id)
    assert resumed["success"] is True
    assert resumed["state"]["current_state"] == "engaged"

    advanced = runtime.advance_to_next_unit(session.session_id)
    assert advanced["completed"] is False
    assert advanced["unit_index"] == 1
    assert advanced["role"] == RoleType.SUMMARIZER.value

    completed = runtime.advance_to_next_unit(session.session_id)
    assert completed["completed"] is True
    assert completed["state"]["current_state"] == "completed"


def test_runtime_missing_session_raises_keyerror():
    """Getting unknown session raises KeyError for API layer mapping."""
    runtime = ConversationRuntime()

    try:
        runtime.get_session("missing")
        assert False, "Expected KeyError"
    except KeyError:
        assert True
