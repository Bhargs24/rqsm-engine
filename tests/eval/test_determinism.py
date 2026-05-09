"""
Determinism and reproducibility harness.

Backs the claims made in:
  - Section 5.2.2 (methodology)
  - Section 7.1.3 / Figure 7.7 ("100% byte-identical replays out of 10")
  - Section 7.5.1 ("100% match across 40 runs")

What this harness does
----------------------
For each of the three reference documents (textbook, research paper, study
guide), the harness:

    1. Runs the *real* document processing + role assignment pipeline N
       times (default N=40, configurable via ``--runs=K`` on the command
       line).
    2. Computes a canonical SHA-256 fingerprint over the semantic units,
       role assignments and initial RQSM state on every run.
    3. Asserts that all N fingerprints are identical.

If any fingerprint diverges from the first run, the test fails and prints
a structured diff pointing at the first differing field.

Outputs
-------
A JSON evidence file is written to ``tests/eval/evidence/`` summarising:

    - per-document number of runs and the unique fingerprint
    - per-run wallclock duration (mean, p50, p95)
    - the percentage of runs that matched the first run

Why this can run live in front of the reviewer
----------------------------------------------
The pipeline is deterministic by construction (Section 5.1.2). Tie
breaking uses fixed alphabetical ordering on role identifiers, the
embedding model is pinned to ``all-MiniLM-L6-v2``, the scoring function
contains no calls to the random number generator, and the state machine
transition table is static. The 100% replay rate is therefore the *expected*
outcome of an honest run, not a fragile coincidence.
"""
from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Dict, List

import pytest

from app.document.processor import DocumentProcessor
from app.roles.role_assignment import RoleAssigner
from app.state_machine.conversation_state import ConversationStateMachine

from .helpers.fingerprint import diff_payloads, fingerprint_run


def _run_pipeline_once(processor: DocumentProcessor, assigner: RoleAssigner, doc_path: Path):
    """Process a document end-to-end exactly the way the API does."""
    units = processor.process_document(str(doc_path))
    assignments = assigner.assign_roles(units, balance_roles=True)
    sm = ConversationStateMachine(session_id="determinism-harness")
    sm.context.total_units = len(units)
    return units, assignments, sm.get_state_summary()


@pytest.fixture(scope="module")
def pipeline():
    """One processor + assigner shared across all docs in this module.

    Important: we reuse the same DocumentProcessor instance across all runs
    on purpose. Reusing the loaded SentenceTransformer model is *closer*
    to how the production API behaves (the model is loaded once at
    startup, not per request) and it also avoids paying the model load
    cost N times.
    """
    return DocumentProcessor(), RoleAssigner()


def test_determinism_across_runs(
    pipeline,
    eval_documents: Dict[str, Path],
    runs_per_document: int,
    evidence_dir: Path,
    evidence_tag: str,
):
    """Run each document N times and assert all replays match."""
    processor, assigner = pipeline

    per_doc_results: Dict[str, Dict] = {}
    overall_status = "PASS"

    for doc_label, doc_path in eval_documents.items():
        print(f"\n[determinism] {doc_label}: running {runs_per_document} replays of {doc_path.name}")

        digests: List[str] = []
        durations_ms: List[float] = []
        first_payload = None
        first_diff_lines: List[str] = []

        for run_idx in range(runs_per_document):
            t0 = time.perf_counter()
            units, assignments, state_summary = _run_pipeline_once(processor, assigner, doc_path)
            duration_ms = (time.perf_counter() - t0) * 1000.0

            digest, payload = fingerprint_run(units, assignments, state_summary)

            if first_payload is None:
                first_payload = payload
                first_digest = digest

            if digest != first_digest and not first_diff_lines:
                first_diff_lines = diff_payloads(first_payload, payload)

            digests.append(digest)
            durations_ms.append(duration_ms)

        unique_digests = sorted(set(digests))
        match_count = sum(1 for d in digests if d == first_digest)
        match_rate = match_count / runs_per_document

        per_doc_results[doc_label] = {
            "document": str(doc_path.name),
            "runs": runs_per_document,
            "unique_fingerprints": unique_digests,
            "fingerprint_count": len(unique_digests),
            "match_count": match_count,
            "match_rate_percent": round(match_rate * 100.0, 4),
            "duration_ms": {
                "mean": round(statistics.mean(durations_ms), 3),
                "p50": round(statistics.median(durations_ms), 3),
                "p95": round(sorted(durations_ms)[int(0.95 * len(durations_ms)) - 1], 3),
                "min": round(min(durations_ms), 3),
                "max": round(max(durations_ms), 3),
            },
            "first_diff": first_diff_lines[:25],  # cap so the artefact stays readable
        }

        if len(unique_digests) != 1:
            overall_status = "FAIL"

        print(
            f"[determinism] {doc_label}: "
            f"{match_count}/{runs_per_document} matched first run ({match_rate * 100:.2f}%) "
            f"unique={len(unique_digests)} mean={per_doc_results[doc_label]['duration_ms']['mean']}ms"
        )

    # Persist evidence even if the assertion fails -- the reviewer should
    # still be able to inspect the artefact.
    overall_match_rate = (
        100.0 * sum(d["match_count"] for d in per_doc_results.values())
        / (runs_per_document * len(per_doc_results))
    )
    artefact = {
        "harness": "test_determinism",
        "claim_reference": "Section 5.2.2, 7.1.3, Figure 7.7, 7.5.1",
        "runs_per_document": runs_per_document,
        "documents": per_doc_results,
        "overall_match_rate_percent": round(overall_match_rate, 4),
        "status": overall_status,
    }
    out_path = evidence_dir / f"determinism_report{evidence_tag}.json"
    out_path.write_text(json.dumps(artefact, indent=2), encoding="utf-8")
    print(f"[determinism] evidence written to {out_path}")

    # Hard assertion last so the artefact is always written even on failure.
    for doc_label, summary in per_doc_results.items():
        assert summary["fingerprint_count"] == 1, (
            f"Determinism violation on {doc_label}: produced "
            f"{summary['fingerprint_count']} distinct fingerprints across "
            f"{summary['runs']} runs. First diff:\n  "
            + "\n  ".join(summary["first_diff"])
        )


def test_role_assignment_is_pure(pipeline, eval_documents):
    """A second, smaller smoke check: role assignment must be a pure function of its input.

    This is a structural check that complements the end-to-end determinism
    test. It runs the assigner alone (no segmenter, no state machine) so a
    failure here is definitely in the scoring layer rather than in the
    embedding stack.
    """
    processor, assigner = pipeline
    units = processor.process_document(str(eval_documents["textbook"]))

    first = assigner.assign_roles(units, balance_roles=True)
    second = assigner.assign_roles(units, balance_roles=True)

    assert len(first) == len(second)
    for a, b in zip(first, second):
        assert a.assigned_role is b.assigned_role, (
            f"Role assignment for unit {a.semantic_unit.id} drifted: "
            f"{a.assigned_role.value} != {b.assigned_role.value}"
        )
        assert pytest.approx(a.score.total_score, rel=1e-9) == b.score.total_score
        assert [r.value for r in a.chime_in_roles] == [r.value for r in b.chime_in_roles]
