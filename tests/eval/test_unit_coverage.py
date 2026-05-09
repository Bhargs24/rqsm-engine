"""
Unit-test coverage harness.

Backs Section 5.2.1 of the report ("Coverage is above 80%, matching
NFR-20"). The check itself is just a thin wrapper around ``pytest --cov``
that runs the existing ``tests/unit/`` suite over the ``app/`` package
and parses the resulting coverage report.

This is structured as a regular pytest test so the same `python -m pytest
tests/eval` invocation that runs the rest of the harness picks it up.

Output
------
A coverage report is written to ``tests/eval/evidence/coverage.xml``
plus a small JSON summary to ``tests/eval/evidence/coverage_report.json``.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest


COVERAGE_FLOOR = 0.80


def _parse_coverage_total(stdout: str) -> float:
    """Pull the TOTAL line out of `pytest --cov` text output and return [0, 1]."""
    for line in stdout.splitlines():
        if line.strip().startswith("TOTAL"):
            tokens = line.split()
            for tok in tokens:
                if tok.endswith("%"):
                    try:
                        return float(tok.rstrip("%")) / 100.0
                    except ValueError:
                        continue
    return -1.0


def test_unit_test_coverage_meets_floor(evidence_dir: Path, evidence_tag: str):
    """Run pytest --cov over the unit tests and assert >= 80% coverage.

    This test is *skipped* (not failed) when pytest-cov is not installed,
    so a developer can still run the rest of the eval harness. The
    skip reason is recorded in the evidence file for transparency.
    """
    pkg_root = Path(__file__).resolve().parent.parent.parent  # rqsm-engine/
    unit_dir = pkg_root / "tests" / "unit"
    cov_target = pkg_root / "app"

    out_xml = evidence_dir / f"coverage{evidence_tag}.xml"
    out_json = evidence_dir / f"coverage_report{evidence_tag}.json"

    if not unit_dir.exists():
        pytest.skip(f"No tests/unit/ directory found at {unit_dir}")

    # Probe pytest-cov availability up front so we can skip cleanly.
    try:
        import pytest_cov  # noqa: F401
    except ImportError:
        report = {
            "harness": "test_unit_coverage",
            "claim_reference": "Section 5.2.1, NFR-20",
            "status": "SKIPPED",
            "reason": "pytest-cov not installed; install with `pip install pytest-cov`.",
        }
        out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        pytest.skip("pytest-cov is not installed")

    cmd = [
        sys.executable, "-m", "pytest",
        str(unit_dir),
        f"--cov={cov_target}",
        "--cov-report", f"xml:{out_xml}",
        "--cov-report", "term",
        "-q",
    ]
    print(f"[coverage] running: {' '.join(cmd)}")
    completed = subprocess.run(
        cmd,
        cwd=pkg_root,
        capture_output=True,
        text=True,
    )

    coverage = _parse_coverage_total(completed.stdout) if completed.stdout else -1.0

    report = {
        "harness": "test_unit_coverage",
        "claim_reference": "Section 5.2.1, NFR-20",
        "command": cmd,
        "exit_code": completed.returncode,
        "coverage": round(coverage, 4) if coverage >= 0 else None,
        "coverage_percent": round(coverage * 100, 2) if coverage >= 0 else None,
        "floor_percent": COVERAGE_FLOOR * 100,
        "stdout_tail": completed.stdout.splitlines()[-40:] if completed.stdout else [],
        "stderr_tail": completed.stderr.splitlines()[-40:] if completed.stderr else [],
        "status": "PASS" if coverage >= COVERAGE_FLOOR else "FAIL",
    }
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[coverage] coverage={coverage * 100:.2f}% (floor {COVERAGE_FLOOR * 100:.0f}%)")
    print(f"[coverage] evidence written to {out_json}")

    assert coverage >= 0, (
        "Could not parse coverage from pytest output. Inspect "
        f"{out_json} for stdout/stderr tails."
    )
    assert coverage >= COVERAGE_FLOOR, (
        f"Coverage {coverage * 100:.2f}% is below the {COVERAGE_FLOOR * 100:.0f}% floor."
    )
