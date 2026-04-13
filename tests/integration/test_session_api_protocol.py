"""Protocol-level API tests for session conversation flow."""
import io

from fastapi import UploadFile
from fastapi.testclient import TestClient

from app.document.segmenter import SemanticUnit
from app.main import app, _runtime
from app.roles.role_assignment import RoleAssignment, RoleScore
from app.roles.role_templates import RoleType, role_library


class DummyProcessor:
    def __init__(self, units):
        self._units = units

    def process_document(self, _path):
        return self._units


class DummyAssigner:
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


def test_session_api_full_protocol(monkeypatch):
    unit0 = _make_unit(0, "Machine learning models learn patterns from data.")
    unit1 = _make_unit(1, "Neural networks contain layers and activation functions.")
    assignments = [
        _make_assignment(unit0, RoleType.EXPLAINER),
        _make_assignment(unit1, RoleType.SUMMARIZER),
    ]

    _runtime._sessions.clear()
    _runtime._llm_available = False
    monkeypatch.setattr(_runtime, "_get_processor", lambda: DummyProcessor([unit0, unit1]))
    monkeypatch.setattr(_runtime, "_get_assigner", lambda: DummyAssigner(assignments))

    client = TestClient(app)

    upload = client.post("/sessions/document", files={"file": ("doc.txt", b"hello")})
    assert upload.status_code == 200, upload.text
    data = upload.json()
    assert data["total_units"] == 2
    session_id = data["session_id"]

    start = client.post(f"/sessions/{session_id}/start")
    assert start.status_code == 200, start.text
    start_data = start.json()
    assert start_data["role"] == RoleType.EXPLAINER.value

    msg = client.post(f"/sessions/{session_id}/message", json={"message": "clarify this"})
    assert msg.status_code == 200, msg.text

    interrupt = client.post(f"/sessions/{session_id}/interrupt", json={})
    assert interrupt.status_code == 200, interrupt.text
    assert interrupt.json()["success"] is True

    intr_msg = client.post(
        f"/sessions/{session_id}/interrupt/message",
        json={"message": "what is a common mistake?"},
    )
    assert intr_msg.status_code == 200, intr_msg.text

    resume = client.post(f"/sessions/{session_id}/resume", json={"from_start": False})
    assert resume.status_code == 200, resume.text
    resume_data = resume.json()
    assert resume_data["success"] is True
    assert "response" in resume_data

    nxt = client.post(f"/sessions/{session_id}/next", json={})
    assert nxt.status_code == 200, nxt.text

    state = client.get(f"/sessions/{session_id}")
    assert state.status_code == 200, state.text
