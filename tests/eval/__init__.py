"""
RQSM-Engine evaluation harnesses.

This package contains the runnable test scripts that produce the evidence
referenced in the capstone report:

- test_determinism.py             Section 5.2.2 / 7.1.3 / 7.5.1
- test_performance.py             Section 5.2.4 / 7.1.6 / Table 7.1
- test_intent_classification.py   Section 5.2.3 / Table 5.1
- test_state_machine_stability.py Section 7.1.5
- test_unit_coverage.py           Section 5.2.1 (NFR-20)

Run a single suite with pytest, e.g.

    pytest tests/eval/test_determinism.py -v -s

Or run everything and produce a consolidated report under tests/eval/evidence/

    python -m tests.eval.run_all_evals

All harnesses execute the real production pipeline. Nothing is mocked or
fabricated. Results are written to tests/eval/evidence/ as JSON + Markdown
so they can be inspected after the fact.
"""
