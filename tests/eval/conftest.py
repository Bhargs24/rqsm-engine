"""Shared fixtures and configuration for the evaluation harness."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Make sure the rqsm-engine package root is importable regardless of where
# pytest is invoked from. This mirrors what the regular test suite does.
_THIS = Path(__file__).resolve()
_PKG_ROOT = _THIS.parent.parent.parent  # rqsm-engine/
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))


# --- Paths --------------------------------------------------------------------

DATASETS_DIR = _THIS.parent / "datasets"
EVIDENCE_DIR = _THIS.parent / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def datasets_dir() -> Path:
    return DATASETS_DIR


@pytest.fixture(scope="session")
def evidence_dir() -> Path:
    return EVIDENCE_DIR


@pytest.fixture(scope="session")
def eval_documents(datasets_dir: Path) -> dict:
    """The three documents from Section 5.1.4: textbook, research paper, study guide."""
    return {
        "textbook": datasets_dir / "doc_textbook.txt",
        "research_paper": datasets_dir / "doc_research_paper.txt",
        "study_guide": datasets_dir / "doc_study_guide.txt",
    }


# --- Number-of-runs override -------------------------------------------------

def pytest_addoption(parser):
    """Allow the determinism harness to be re-run with N != 40 for fast smoke tests.

    Example
    -------
        # Full evidence run (matches Section 7.5.1 wording)
        pytest tests/eval/test_determinism.py --runs=40

        # Fast smoke check (~30s on a laptop)
        pytest tests/eval/test_determinism.py --runs=5
    """
    parser.addoption(
        "--runs",
        action="store",
        default="40",
        help="Number of replays per document for the determinism harness (default: 40).",
    )
    parser.addoption(
        "--evidence-tag",
        action="store",
        default=None,
        help="Optional label appended to evidence file names (useful when running multiple times).",
    )


@pytest.fixture(scope="session")
def runs_per_document(request) -> int:
    return int(request.config.getoption("--runs"))


@pytest.fixture(scope="session")
def evidence_tag(request) -> str:
    raw = request.config.getoption("--evidence-tag")
    return f"_{raw}" if raw else ""


# --- Hooks for the heavy ML stack -------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def _quiet_logging():
    """Stop loguru from drowning the test output with INFO logs.

    The production code logs at INFO by default; the eval harness wants a
    clean output stream so reviewers can read the assertions and metrics.
    """
    try:
        from loguru import logger
        logger.remove()
        logger.add(sys.stderr, level=os.environ.get("RQSM_TEST_LOG_LEVEL", "WARNING"))
    except Exception:  # pragma: no cover - logging is best-effort
        pass
    yield
