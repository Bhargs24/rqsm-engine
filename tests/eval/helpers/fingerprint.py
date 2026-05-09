"""
Canonical fingerprinting of pipeline outputs for the determinism harness.

The thesis (Section 5.2.2) defines reproducibility as: same input + same
configuration -> byte-identical semantic units, role queues, initial RQSM
state, and audit log.

The job of this module is to take those four runtime artefacts and produce
a *canonical, stable* string and SHA-256 fingerprint so two runs can be
compared without being misled by:

  - Python set / dict ordering changes
  - Different float formatting between runs
  - Whitespace artifacts in deserialised payloads

If two fingerprints match, the runs were behaviourally identical.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Iterable, List, Tuple


# How many decimal places we keep when serialising floats. The thesis
# checks "byte-identical" replays; in practice we want stability against
# tiny floating point jitter that can come from BLAS/MKL non-determinism
# even though the model itself is deterministic. Eight decimals is more
# than enough resolution for this system without being so loose that it
# would mask a real bug.
FLOAT_PRECISION = 8


def _normalise(value: Any) -> Any:
    """Recursively convert an object to a JSON-canonicalisable form.

    - dataclasses become dicts
    - enums and arbitrary objects become their .value or repr
    - floats are rounded to FLOAT_PRECISION
    - sets become sorted lists
    """
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return round(value, FLOAT_PRECISION)
    if isinstance(value, (list, tuple)):
        return [_normalise(v) for v in value]
    if isinstance(value, set):
        return sorted(_normalise(v) for v in value)
    if isinstance(value, dict):
        return {str(k): _normalise(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if is_dataclass(value):
        return _normalise(asdict(value))
    if hasattr(value, "value") and hasattr(value, "name"):
        return value.value
    return repr(value)


def _semantic_units_payload(units: Iterable[Any]) -> List[Dict[str, Any]]:
    """Extract only the fields that should be reproducible across runs.

    We deliberately exclude metadata fields like ``source_path`` because
    the absolute path differs between machines but is not part of the
    determinism claim.
    """
    payload = []
    for u in units:
        payload.append({
            "id": u.id,
            "title": u.title,
            "text": u.text,
            "document_section": u.document_section,
            "position": u.position,
            "similarity_score": round(float(u.similarity_score), FLOAT_PRECISION),
            "word_count": u.word_count,
        })
    return payload


def _assignment_payload(assignment: Any) -> Dict[str, Any]:
    """Pull the deterministic part of one role assignment."""
    return {
        "unit_id": assignment.semantic_unit.id,
        "unit_position": assignment.semantic_unit.position,
        "primary_role": assignment.assigned_role.value,
        "chime_in_roles": [r.value for r in (assignment.chime_in_roles or [])],
        "score": {
            "total": round(float(assignment.score.total_score), FLOAT_PRECISION),
            "structural": round(float(assignment.score.structural_score), FLOAT_PRECISION),
            "lexical": round(float(assignment.score.lexical_score), FLOAT_PRECISION),
            "topic": round(float(assignment.score.topic_score), FLOAT_PRECISION),
        },
        "confidence": round(float(assignment.confidence), FLOAT_PRECISION),
    }


def _state_machine_payload(state_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Strip wallclock fields out of the state-machine snapshot.

    We compare the *initial* RQSM context, which is set up the same way for
    every run. Wallclock timestamps and progress percentages that depend on
    the machine clock are excluded.
    """
    drop_keys = {"started_at", "last_activity"}
    cleaned = {k: v for k, v in state_summary.items() if k not in drop_keys}
    return _normalise(cleaned)


def fingerprint_run(
    semantic_units: Iterable[Any],
    assignments: Iterable[Any],
    state_summary: Dict[str, Any],
    audit_events: Iterable[Dict[str, Any]] = (),
) -> Tuple[str, Dict[str, Any]]:
    """Produce a (sha256_hex, canonical_payload) tuple for a pipeline run."""
    payload = {
        "semantic_units": _semantic_units_payload(semantic_units),
        "assignments": [_assignment_payload(a) for a in assignments],
        "state_machine": _state_machine_payload(state_summary),
        "audit_events": _normalise(list(audit_events)),
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return digest, payload


def diff_payloads(a: Dict[str, Any], b: Dict[str, Any]) -> List[str]:
    """Return a list of human readable differences between two payloads.

    Used by the determinism harness when a mismatch is detected, so the
    failure message points the developer at exactly which field drifted.
    """
    diffs: List[str] = []

    def walk(prefix: str, x: Any, y: Any) -> None:
        if x == y:
            return
        if isinstance(x, dict) and isinstance(y, dict):
            keys = sorted(set(x.keys()) | set(y.keys()))
            for k in keys:
                walk(f"{prefix}.{k}" if prefix else k, x.get(k, "<MISSING>"), y.get(k, "<MISSING>"))
            return
        if isinstance(x, list) and isinstance(y, list):
            for i in range(max(len(x), len(y))):
                walk(f"{prefix}[{i}]", x[i] if i < len(x) else "<MISSING>", y[i] if i < len(y) else "<MISSING>")
            return
        diffs.append(f"{prefix}: {x!r} != {y!r}")

    walk("", a, b)
    return diffs
