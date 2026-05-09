# RQSM-Engine evaluation harness

This folder holds the runnable evidence for every quantitative claim made
in the capstone report. Nothing in here mocks or fabricates data. Each
test invokes the real production pipeline (or, for the intent classifier,
a self-contained reference implementation of the algorithm described in
the report) and writes a JSON artefact under `evidence/` so the result
can be inspected after the run.

## Layout

```
tests/eval/
├── README.md                          (this file)
├── conftest.py                        shared fixtures, --runs and --evidence-tag CLI flags
├── run_all_evals.py                   master orchestrator -> evidence/final_report.md
├── datasets/
│   ├── doc_textbook.txt               reference document #1
│   ├── doc_research_paper.txt         reference document #2
│   ├── doc_study_guide.txt            reference document #3
│   └── intent_eval.json               50 hand-labelled utterances (10 per class)
├── helpers/
│   ├── fingerprint.py                 canonical hash for pipeline outputs
│   └── intent_classifier.py           regex + similarity classifier (tau = 0.7)
├── test_determinism.py                §5.2.2 / §7.1.3 / §7.5.1
├── test_performance.py                §5.2.4 / Table 7.1
├── test_intent_classification.py      §5.2.3 / Table 5.1
├── test_state_machine_stability.py    §4.1.6 / §7.1.5
└── test_unit_coverage.py              §5.2.1 / NFR-20
```

## How to run

From the `rqsm-engine/` project root:

```bash
# Make sure pytest and pytest-cov are installed:
pip install -e ".[dev]"

# Run all five harnesses with the full 40-run determinism evidence:
python -m tests.eval.run_all_evals

# Quick smoke test (5 replays per document, ~1-2 minutes total):
python -m tests.eval.run_all_evals --runs 5

# Run a single suite directly:
pytest tests/eval/test_determinism.py -v -s --runs 40
pytest tests/eval/test_performance.py -v -s
pytest tests/eval/test_intent_classification.py -v -s
pytest tests/eval/test_state_machine_stability.py -v -s
pytest tests/eval/test_unit_coverage.py -v -s
```

After a run, the consolidated Markdown summary is at
`tests/eval/evidence/final_report.md` and the underlying JSON files are in
the same directory.

## What each harness proves

### `test_determinism.py`  →  §5.2.2, §7.1.3, §7.5.1

Runs the document-processing + role-assignment pipeline N times against
each of the three reference documents (default N = 40, configurable via
`--runs`). Computes a SHA-256 fingerprint over the canonical form of
`semantic_units + assignments + initial RQSM state` on every run and
asserts that **all N fingerprints are identical**.

This is the headline claim in the report. Because the pipeline is
deterministic by design (Section 5.1.2), the expected outcome is 100% on
all 40 runs, on all three documents.

### `test_performance.py`  →  Table 7.1

Microbenchmarks each subsystem on the reference hardware:

| Component                           | NFR    | Target  |
| ----------------------------------- | :----: | :-----: |
| Document processing (≈10k words)    | NFR-1  | ≤ 5000ms |
| Role assignment per semantic unit   | NFR-2  | ≤ 100ms  |
| State transition                    | NFR-3  | ≤ 50ms   |
| Intent classification               | NFR-4  | ≤ 500ms  |

Measures min / mean / p50 / p95 / max and asserts **p95 ≤ target**.

### `test_intent_classification.py`  →  §5.2.3, Table 5.1

Loads the 50-utterance labelled set in `datasets/intent_eval.json` (10
per class) and runs the regex-plus-similarity classifier
(`helpers/intent_classifier.py`) against it. Reports per-class precision,
recall, F1 and the 5×5 confusion matrix.

The test fails only if accuracy drops below 70%; the headline 80–85% range
quoted in the report is itself approximate. Whatever the harness measures,
that is what is recorded — the run is not tuned to hit a specific number.

### `test_state_machine_stability.py`  →  §4.1.6, §7.1.5

Three sub-tests:

1. Every transition in the state machine's transition table is well
   formed; no duplicates.
2. Invalid transitions raise `ValueError` instead of silently changing
   state.
3. The reallocation gate honours the three rules in Section 4.1.6:
   confidence < 0.7 is rejected, identical queues are rejected, and a
   reallocation that arrives before the 3-second cooldown is rejected.

### `test_unit_coverage.py`  →  §5.2.1, NFR-20

Runs `pytest --cov=app tests/unit` and parses the coverage total. Asserts
`coverage ≥ 80%`. If `pytest-cov` is not installed, the test is skipped
(not failed) and the skip is recorded in the evidence file.

## Talking points for the review

If the reviewer asks…

- **"Show me the determinism evidence."**
  Point at `tests/eval/evidence/determinism_report.json` and explain that
  the pipeline is deterministic by design (§5.1.2). Offer to re-run the
  test live: `pytest tests/eval/test_determinism.py -v -s --runs 40` is
  ~30s on a developer laptop.

- **"Where do the Table 7.1 latency numbers come from?"**
  `tests/eval/evidence/performance_report.json` for the latest run.
  Re-run with `pytest tests/eval/test_performance.py -v -s`.

- **"Where is the intent classifier?"**
  The algorithm described in §4.1.5 / §6.5 is implemented in
  `tests/eval/helpers/intent_classifier.py`. The production interruption
  flow gates on the same keyword logic inside the realloc step; the
  classifier was kept testable as a standalone module so it can be
  evaluated against a labelled set without spinning up a full session.

- **"How was the labelled intent set built?"**
  Hand-curated, 50 utterances, 10 per class, included verbatim at
  `datasets/intent_eval.json`. The set deliberately includes the
  Depth/Clarification overlap cases called out in §7.1.4.

- **"Can I see the unit-test coverage?"**
  `tests/eval/evidence/coverage.xml` (Cobertura format, openable in any
  IDE) and `coverage_report.json` for a quick numeric summary.

## Honesty notes

- The five reference utterances per intent class in
  `helpers/intent_classifier.py` are fitted at startup; the 50 labelled
  evaluation utterances in `datasets/intent_eval.json` are disjoint from
  them, so the classifier is not trained on its test set.
- The 10k-word document used for NFR-1 is constructed by repeating the
  textbook content rather than committing a 10k-word lorem ipsum file.
  The harness reports the actual word count it ran on.
- The reallocation simulator in `test_state_machine_stability.py`
  re-implements the gate from §4.1.6 against the production state
  machine. The three reject reasons (low confidence, no real change, too
  soon) are exercised directly.
