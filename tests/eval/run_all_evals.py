"""
Master eval runner -- invokes every test_*.py under tests/eval/ in order
and produces a single consolidated Markdown summary alongside the JSON
evidence files.

Usage
-----
From the rqsm-engine project root:

    python -m tests.eval.run_all_evals                   # full run, 40 replays
    python -m tests.eval.run_all_evals --runs 5          # fast smoke
    python -m tests.eval.run_all_evals --skip coverage   # skip a section

The runner does not import the harness modules directly. It shells out
to ``pytest`` so each section runs in a clean process and a failure in
one section does not prevent the others from running.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


HERE = Path(__file__).resolve().parent
PKG_ROOT = HERE.parent.parent  # rqsm-engine/
EVIDENCE = HERE / "evidence"
EVIDENCE.mkdir(parents=True, exist_ok=True)


SECTIONS = [
    {
        "name": "determinism",
        "module": "tests/eval/test_determinism.py",
        "evidence_file": "determinism_report.json",
        "claim": "Section 5.2.2, 7.1.3, 7.5.1: 100% byte-identical replays.",
    },
    {
        "name": "performance",
        "module": "tests/eval/test_performance.py",
        "evidence_file": "performance_report.json",
        "claim": "Table 7.1: NFR-1, NFR-2, NFR-3, NFR-4 latency targets.",
    },
    {
        "name": "intent",
        "module": "tests/eval/test_intent_classification.py",
        "evidence_file": "intent_classification_report.json",
        "claim": "Section 5.2.3, Table 5.1: 5-class classifier metrics.",
    },
    {
        "name": "stability",
        "module": "tests/eval/test_state_machine_stability.py",
        "evidence_file": "state_machine_stability_report.json",
        "claim": "Section 4.1.6, 7.1.5: gating + hysteresis bounds.",
    },
    {
        "name": "coverage",
        "module": "tests/eval/test_unit_coverage.py",
        "evidence_file": "coverage_report.json",
        "claim": "Section 5.2.1, NFR-20: unit-test coverage >= 80%.",
    },
]


def _run_section(module: str, runs: int, evidence_tag: str, extra_args: List[str]) -> int:
    cmd = [
        sys.executable, "-m", "pytest", module,
        "-v", "-s",
        f"--runs={runs}",
    ]
    if evidence_tag:
        cmd.extend(["--evidence-tag", evidence_tag])
    cmd.extend(extra_args)
    print("\n" + "=" * 78)
    print(f"  RUNNING: {' '.join(cmd)}")
    print("=" * 78)
    return subprocess.run(cmd, cwd=PKG_ROOT).returncode


def _read_evidence(name: str, tag: str) -> Dict:
    suffix = f"_{tag}" if tag else ""
    path = EVIDENCE / name.replace(".json", f"{suffix}.json")
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"error": f"failed to parse {path}: {exc}"}
    return {"error": f"missing evidence file at {path}"}


def _summarise_determinism(data: Dict) -> str:
    if "error" in data:
        return f"- **status**: missing artefact ({data['error']})"
    docs = data.get("documents", {})
    lines = [
        f"- **status**: {data.get('status', 'UNKNOWN')}",
        f"- **runs per document**: {data.get('runs_per_document', '?')}",
        f"- **overall match rate**: {data.get('overall_match_rate_percent', '?')}%",
        "",
        "| Document | Runs | Unique fingerprints | Match rate | Mean (ms) | p95 (ms) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for label, doc in docs.items():
        lines.append(
            f"| {label} | {doc['runs']} | {doc['fingerprint_count']} | "
            f"{doc['match_rate_percent']}% | {doc['duration_ms']['mean']} | "
            f"{doc['duration_ms']['p95']} |"
        )
    return "\n".join(lines)


def _summarise_performance(data: Dict) -> str:
    if "error" in data:
        return f"- **status**: missing artefact ({data['error']})"
    comps = data.get("components", {})
    status = data.get("component_status", {})
    lines = [
        f"- **status**: {data.get('status', 'UNKNOWN')}",
        "",
        "| Component | NFR | Target (ms) | p95 (ms) | Verdict |",
        "|---|:---:|---:|---:|:---:|",
    ]
    for name, comp in comps.items():
        p95 = comp.get("stats_ms", {}).get("p95")
        lines.append(
            f"| {name} | {comp.get('nfr', '?')} | {comp.get('target_ms')} | "
            f"{p95 if p95 is not None else 'n/a'} | {status.get(name, '?')} |"
        )
    return "\n".join(lines)


def _summarise_intent(data: Dict) -> str:
    if "error" in data:
        return f"- **status**: missing artefact ({data['error']})"
    lines = [
        f"- **status**: {data.get('status', 'UNKNOWN')}",
        f"- **dataset size**: {data.get('dataset_size', '?')}",
        f"- **threshold tau**: {data.get('threshold_tau', '?')}",
        f"- **overall accuracy**: {round((data.get('overall_accuracy', 0) or 0) * 100, 2)}%",
        "",
        "| Intent | Precision | Recall | F1 | Support |",
        "|---|---:|---:|---:|---:|",
    ]
    for cls in data.get("per_class", []):
        lines.append(
            f"| {cls['intent']} | {round(cls['precision'] * 100, 2)}% | "
            f"{round(cls['recall'] * 100, 2)}% | {round(cls['f1'] * 100, 2)}% | {cls['support']} |"
        )
    matrix = data.get("confusion_matrix") or {}
    if matrix:
        lines.append("")
        lines.append("**Confusion matrix (rows = truth, cols = predicted)**")
        lines.append("")
        cols = list(next(iter(matrix.values())).keys())
        lines.append("| | " + " | ".join(cols) + " |")
        lines.append("|---|" + "|".join(["---:"] * len(cols)) + "|")
        for row, cells in matrix.items():
            lines.append("| " + row + " | " + " | ".join(str(cells[c]) for c in cols) + " |")
    return "\n".join(lines)


def _summarise_stability(data: Dict) -> str:
    if "error" in data:
        return f"- **status**: missing artefact ({data['error']})"
    th = data.get("thresholds", {})
    lines = [
        f"- **status**: {data.get('status', 'UNKNOWN')}",
        f"- **gate**: tau={th.get('tau')}, min_interval={th.get('min_interval_s')}s, min_edit_distance={th.get('min_edit_distance')}",
        f"- **accepted**: {data.get('accepted_count')} / **rejected**: {data.get('rejected_count')}",
        "",
        "| # | Confidence | Edit distance | Elapsed (s) | Decision |",
        "|---:|---:|---:|---:|:---|",
    ]
    for i, attempt in enumerate(data.get("attempts", []), 1):
        lines.append(
            f"| {i} | {attempt.get('confidence')} | {attempt.get('edit_distance')} | "
            f"{attempt.get('elapsed_since_last_s')} | {attempt.get('decision')} |"
        )
    return "\n".join(lines)


def _summarise_coverage(data: Dict) -> str:
    if "error" in data:
        return f"- **status**: missing artefact ({data['error']})"
    return (
        f"- **status**: {data.get('status', 'UNKNOWN')}\n"
        f"- **measured**: {data.get('coverage_percent', '?')}% "
        f"(floor {data.get('floor_percent', '?')}%)\n"
        f"- **exit code**: {data.get('exit_code')}\n"
    )


SUMMARISERS = {
    "determinism": _summarise_determinism,
    "performance": _summarise_performance,
    "intent": _summarise_intent,
    "stability": _summarise_stability,
    "coverage": _summarise_coverage,
}


def _render_report(section_outcomes: Dict[str, int], evidence_tag: str, runs: int) -> str:
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    lines = [
        f"# RQSM-Engine Evaluation Evidence",
        "",
        f"_Generated: {timestamp}_",
        f"_Replays per document for the determinism harness: {runs}_",
        "",
        "Every section below corresponds to a numbered claim in the capstone",
        "report and was produced by running the matching harness under",
        "`tests/eval/`. Raw JSON artefacts are written next to this file in",
        "`tests/eval/evidence/`. To reproduce, run the command shown at the",
        "top of each section.",
        "",
    ]
    for section in SECTIONS:
        name = section["name"]
        if name not in section_outcomes:
            continue
        evidence = _read_evidence(section["evidence_file"], evidence_tag)
        summariser = SUMMARISERS[name]
        rc = section_outcomes[name]
        lines.append(f"## {name.title()}")
        lines.append("")
        lines.append(f"_{section['claim']}_")
        lines.append("")
        lines.append(f"_Reproduce: `pytest {section['module']} -v -s`_")
        lines.append("")
        lines.append(f"- **pytest exit code**: {rc} ({'PASS' if rc == 0 else 'FAIL'})")
        lines.append("")
        lines.append(summariser(evidence))
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs", type=int, default=40,
        help="Replays per document for the determinism harness (default: 40).",
    )
    parser.add_argument(
        "--skip", action="append", default=[],
        choices=[s["name"] for s in SECTIONS],
        help="Skip a named section. May be repeated.",
    )
    parser.add_argument(
        "--evidence-tag", default="",
        help="Optional label appended to evidence file names.",
    )
    args, extra = parser.parse_known_args()

    section_outcomes: Dict[str, int] = {}
    for section in SECTIONS:
        if section["name"] in args.skip:
            print(f"\n[run_all_evals] skipping {section['name']} (per --skip)")
            continue
        rc = _run_section(section["module"], args.runs, args.evidence_tag, extra)
        section_outcomes[section["name"]] = rc

    report_md = _render_report(section_outcomes, args.evidence_tag, args.runs)
    suffix = f"_{args.evidence_tag}" if args.evidence_tag else ""
    report_path = EVIDENCE / f"final_report{suffix}.md"
    report_path.write_text(report_md, encoding="utf-8")
    print(f"\n[run_all_evals] consolidated report -> {report_path}")

    failures = [name for name, rc in section_outcomes.items() if rc != 0]
    if failures:
        print(f"[run_all_evals] FAILED sections: {', '.join(failures)}")
        return 1
    print("[run_all_evals] all sections passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
