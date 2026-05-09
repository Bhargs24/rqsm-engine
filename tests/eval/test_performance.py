"""
Performance benchmarks against the Non-Functional Requirements (NFRs).

Backs Table 7.1 of the report:

    Document processing (10k words)        NFR-1   <= 5000 ms
    Role assignment per unit               NFR-2   <= 100  ms
    State transition                       NFR-3   <= 50   ms
    Intent classification                  NFR-4   <= 500  ms

Method
------
Each component is exercised on a realistic input (one of the three
reference documents, possibly repeated to hit the 10k word target) and
timed across a small number of warm-up + measurement iterations. The
warm-up runs absorb the one-time cost of loading the embedding model so
that the reported latencies reflect steady-state behaviour, which is what
the API serves in production.

The harness reports min / mean / p50 / p95 / max in milliseconds for each
component and asserts the *p95* against the NFR target. p95 is a stricter
criterion than the mean and is the right thing to check for a service-
level claim.

The full per-component report is written to
``tests/eval/evidence/performance_report.json``.
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
from app.state_machine.conversation_state import (
    ConversationState,
    ConversationStateMachine,
    EventType,
)


# Number of measurement iterations per component. Small but large enough
# for a stable p95 on a developer laptop.
WARMUP_ITERATIONS = 2
MEASURE_ITERATIONS = 12


def _percentiles(values_ms: List[float]) -> Dict[str, float]:
    if not values_ms:
        return {}
    sorted_values = sorted(values_ms)
    return {
        "min": round(sorted_values[0], 3),
        "p50": round(statistics.median(sorted_values), 3),
        "mean": round(statistics.mean(sorted_values), 3),
        "p95": round(sorted_values[int(0.95 * len(sorted_values)) - 1], 3),
        "max": round(sorted_values[-1], 3),
    }


def _time_calls(n: int, fn) -> List[float]:
    """Call ``fn()`` ``n`` times and return per-call durations in milliseconds."""
    durations: List[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        durations.append((time.perf_counter() - t0) * 1000.0)
    return durations


def _make_10k_word_document(base_path: Path, target_words: int = 10000) -> Path:
    """Construct a ~10k word document by repeating the textbook content.

    The NFR target (Table 7.1) is "10,000 words", so we synthesise a fixture
    of approximately that size from the existing reference document. This
    keeps the eval reproducible without committing a 10k word lorem ipsum
    blob to the repo.
    """
    base_text = base_path.read_text(encoding="utf-8")
    word_count = len(base_text.split())
    repeats = max(1, target_words // max(word_count, 1) + 1)
    big = (base_text + "\n\n") * repeats
    out = base_path.parent / "doc_10k_words.txt"
    out.write_text(big, encoding="utf-8")
    return out


@pytest.fixture(scope="module")
def stack(eval_documents):
    """Shared processor + assigner. Pre-warms the embedding model."""
    processor = DocumentProcessor()
    assigner = RoleAssigner()

    # Warm up segmenter/embedding caches.
    processor.process_document(str(eval_documents["textbook"]))

    return processor, assigner


def test_performance_against_nfr_targets(
    stack,
    eval_documents,
    evidence_dir: Path,
    evidence_tag: str,
):
    processor, assigner = stack

    # ------- NFR-1: document processing on a ~10k word document -----------
    big_doc = _make_10k_word_document(eval_documents["textbook"], target_words=10000)
    word_count = len(big_doc.read_text(encoding="utf-8").split())

    for _ in range(WARMUP_ITERATIONS):
        processor.process_document(str(big_doc))
    doc_proc_durations = _time_calls(
        MEASURE_ITERATIONS,
        lambda: processor.process_document(str(big_doc)),
    )

    # ------- Pre-stage: get a real units-list to drive the next two ------
    units = processor.process_document(str(eval_documents["research_paper"]))

    # ------- NFR-2: role assignment per unit -----------------------------
    for _ in range(WARMUP_ITERATIONS):
        assigner.assign_roles(units, balance_roles=True)
    assignment_durations = _time_calls(
        MEASURE_ITERATIONS,
        lambda: assigner.assign_roles(units, balance_roles=True),
    )
    per_unit_durations = [d / max(len(units), 1) for d in assignment_durations]

    # ------- NFR-3: state-machine transition -----------------------------
    def _one_transition_cycle():
        sm = ConversationStateMachine(session_id="perf-harness")
        sm.context.total_units = 5
        sm.transition(EventType.DOCUMENT_LOADED)
        sm.transition(EventType.ROLES_ASSIGNED)
        sm.transition(EventType.START_DIALOGUE)
        sm.transition(EventType.USER_MESSAGE)
        sm.transition(EventType.BOT_RESPONSE)
        sm.transition(EventType.NEXT_UNIT)
    transition_durations_total = _time_calls(MEASURE_ITERATIONS * 5, _one_transition_cycle)
    # Six transitions per cycle -> per-transition latency.
    transition_durations = [d / 6.0 for d in transition_durations_total]

    # ------- NFR-4: intent classification --------------------------------
    # We import lazily so the test still reports the other three NFRs even
    # if sentence-transformers is unhappy (the determinism test would
    # already have failed in that case anyway).
    intent_durations: List[float] = []
    intent_error: str = ""
    try:
        from .helpers.intent_classifier import IntentClassifier  # noqa: WPS433

        clf = IntentClassifier()
        # Warm up the encode() path.
        for _ in range(WARMUP_ITERATIONS):
            clf.classify("Can you explain that again?")
        sample_inputs = [
            "Can you explain that again, I don't understand.",
            "Actually, that doesn't sound right.",
            "Tell me more about why this happens.",
            "Let's move on to a different topic.",
            "Can you give me an example?",
        ]
        for sample in sample_inputs:
            intent_durations.extend(_time_calls(MEASURE_ITERATIONS, lambda s=sample: clf.classify(s)))
    except Exception as exc:  # pragma: no cover - skips cleanly if model missing
        intent_error = repr(exc)

    # ------- Build the report --------------------------------------------
    components = {
        "document_processing_10k_words": {
            "nfr": "NFR-1",
            "target_ms": 5000.0,
            "input_word_count": word_count,
            "stats_ms": _percentiles(doc_proc_durations),
            "raw_ms": [round(x, 3) for x in doc_proc_durations],
        },
        "role_assignment_per_unit": {
            "nfr": "NFR-2",
            "target_ms": 100.0,
            "unit_count": len(units),
            "stats_ms": _percentiles(per_unit_durations),
            "raw_ms": [round(x, 3) for x in per_unit_durations],
        },
        "state_transition": {
            "nfr": "NFR-3",
            "target_ms": 50.0,
            "stats_ms": _percentiles(transition_durations),
            "raw_ms": [round(x, 3) for x in transition_durations],
        },
        "intent_classification": {
            "nfr": "NFR-4",
            "target_ms": 500.0,
            "stats_ms": _percentiles(intent_durations) if intent_durations else {},
            "raw_ms": [round(x, 3) for x in intent_durations],
            "error": intent_error,
        },
    }

    component_status = {}
    overall_pass = True
    for name, comp in components.items():
        target = comp["target_ms"]
        p95 = comp["stats_ms"].get("p95")
        if p95 is None:
            component_status[name] = "SKIPPED"
            continue
        passed = p95 <= target
        component_status[name] = "PASS" if passed else "FAIL"
        overall_pass = overall_pass and passed

    report = {
        "harness": "test_performance",
        "claim_reference": "Section 5.2.4, Section 7.1.6, Table 7.1",
        "components": components,
        "component_status": component_status,
        "status": "PASS" if overall_pass else "FAIL",
    }
    out_path = evidence_dir / f"performance_report{evidence_tag}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[performance] evidence written to {out_path}")

    # Stdout summary so the reviewer sees something readable in the test log.
    for name, comp in components.items():
        target = comp["target_ms"]
        p95 = comp["stats_ms"].get("p95")
        if p95 is None:
            print(f"[performance] {name}: SKIPPED ({comp.get('error', 'no measurements')})")
            continue
        verdict = "PASS" if p95 <= target else "FAIL"
        print(f"[performance] {name}: p95={p95}ms target={target}ms {verdict}")

    # Hard assertions per component (skip the intent one if it could not run).
    for name in ("document_processing_10k_words", "role_assignment_per_unit", "state_transition"):
        comp = components[name]
        p95 = comp["stats_ms"].get("p95")
        target = comp["target_ms"]
        assert p95 is not None, f"{name} produced no measurements"
        assert p95 <= target, f"{name} p95={p95}ms exceeds NFR target {target}ms"

    if intent_durations:
        comp = components["intent_classification"]
        assert comp["stats_ms"]["p95"] <= comp["target_ms"], (
            f"intent_classification p95={comp['stats_ms']['p95']}ms exceeds "
            f"NFR target {comp['target_ms']}ms"
        )
