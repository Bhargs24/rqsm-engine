"""Real (non-mocked) pipeline audit using sample document through API endpoints."""
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app, _runtime


def test_real_pipeline_upload_and_start_flow():
    _runtime._sessions.clear()
    # Force deterministic fallback for response generation while keeping real document pipeline.
    _runtime._llm_available = False

    sample_path = Path("sample_docs/machine_learning_intro.txt")
    assert sample_path.exists(), "Expected sample document for real-pipeline test"

    client = TestClient(app)

    with sample_path.open("rb") as f:
        upload = client.post(
            "/sessions/document",
            files={"file": (sample_path.name, f.read())},
        )

    assert upload.status_code == 200, upload.text
    upload_data = upload.json()
    assert upload_data["total_units"] > 0
    session_id = upload_data["session_id"]

    start = client.post(f"/sessions/{session_id}/start")
    assert start.status_code == 200, start.text
    start_data = start.json()
    assert start_data["unit_index"] == 0
    assert isinstance(start_data["response"], str)
    assert len(start_data["response"]) > 0

    state = client.get(f"/sessions/{session_id}")
    assert state.status_code == 200, state.text
    state_data = state.json()
    assert state_data["total_units"] == upload_data["total_units"]
