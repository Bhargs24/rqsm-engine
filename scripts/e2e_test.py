"""End-to-end test driver for the RQSM conversational engine (study-group mode).

Flow exercised:
    1. Upload a multi-section study document
    2. Start the conversation  → expect a multi-role topic opener
                                  (primary Explainer + 2 chime-ins)
    3. User message #1 on unit 1  → expect primary reply + chime-in
    4. User message #2 on unit 1  → expect primary reply + chime-in
    5. User message #3 on unit 1  → expect primary reply + chime-in + auto-nudge
       (the "shall we move on?" line from the primary role)
    6. Advance to unit 2 → new multi-role opener
    7. User interrupt + interruption question (stays single-role)
    8. Resume (from_start=False) → single "back to it" line
    9. Advance to unit 3 → opener
    10. Final state snapshot

Every LLM turn is timed; full messages[] lists are captured for reporting.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


BASE_URL = "http://127.0.0.1:8000"
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
DOC_PATH = REPO_ROOT / "demo_document.txt"
REPORT_DIR = REPO_ROOT.parent / "docs" / "reports" / "e2e"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
JSON_PATH = REPORT_DIR / f"e2e_run_{STAMP}.json"
MD_PATH = REPORT_DIR / f"e2e_report_{STAMP}.md"


class Turn(Dict[str, Any]):
    """Just a typed alias for readability — still a plain dict at runtime."""


turns: List[Turn] = []
prev_end: Optional[float] = None


def record_turn(
    step: str,
    action: str,
    *,
    role: Optional[str] = None,
    user_input: Optional[str] = None,
    response: Optional[str] = None,
    messages: Optional[List[Dict[str, Any]]] = None,
    auto_nudge: bool = False,
    latency_ms: Optional[int] = None,
    gap_ms: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    turns.append(
        {
            "step": step,
            "action": action,
            "role": role,
            "user_input": user_input,
            "response": response,
            "messages": messages or [],
            "auto_nudge": auto_nudge,
            "latency_ms": latency_ms,
            "gap_since_prev_ms": gap_ms,
            "extra": extra or {},
            "wall_clock": datetime.now().isoformat(timespec="seconds"),
        }
    )


def describe_messages(messages: List[Dict[str, Any]]) -> str:
    """Pretty one-line summary of a messages[] payload for console output."""
    if not messages:
        return "(no messages)"
    chunks = []
    for m in messages:
        text = (m.get("text") or "").replace("\n", " ")
        if len(text) > 90:
            text = text[:87] + "..."
        tag = " [NUDGE]" if m.get("is_nudge") else ""
        chunks.append(f"  • {m.get('role', '?')}{tag}: {text}")
    return "\n".join(chunks)


def call(method: str, path: str, **kwargs) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    started = time.perf_counter()
    resp = requests.request(method, url, timeout=120, **kwargs)
    latency_ms = int((time.perf_counter() - started) * 1000)
    if not resp.ok:
        raise RuntimeError(f"{method} {path} -> {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    data["__latency_ms"] = latency_ms
    data["__ended_at"] = time.perf_counter()
    return data


def consume_gap(ended_at: float) -> int:
    """Compute gap from previous turn's end to now, then advance prev_end."""
    global prev_end
    if prev_end is None:
        gap = 0
    else:
        gap = int((ended_at - prev_end) * 1000)
    prev_end = ended_at
    return gap


def banner(msg: str) -> None:
    print(f"\n{'=' * 78}\n{msg}\n{'=' * 78}", flush=True)


def main() -> int:
    banner("RQSM Engine — End-to-End Test")
    print(f"Document    : {DOC_PATH}")
    print(f"Endpoint    : {BASE_URL}")
    print(f"Report base : {REPORT_DIR}")

    health = call("GET", "/health")
    cfg = call("GET", "/config")
    print(f"Health      : {health.get('status')}")
    print(f"Provider    : {cfg.get('llm_provider')}  "
          f"temperature={cfg.get('llm_temperature')}  "
          f"max_tokens={cfg.get('llm_max_tokens')}")

    # ── STEP 1: Upload ────────────────────────────────────────────────────
    banner("STEP 1 — Upload document")
    with DOC_PATH.open("rb") as fh:
        files = {"file": (DOC_PATH.name, fh, "text/plain")}
        started = time.perf_counter()
        resp = requests.post(f"{BASE_URL}/sessions/document", files=files, timeout=180)
        latency_ms = int((time.perf_counter() - started) * 1000)
    resp.raise_for_status()
    upload = resp.json()
    ended = time.perf_counter()
    gap = consume_gap(ended)
    session_id = upload["session_id"]
    total_units = upload["total_units"]
    print(f"session_id   = {session_id}")
    print(f"total_units  = {total_units}")
    print(f"roles_assgn  = {upload['roles_assigned']}")
    print(f"upload_ms    = {latency_ms}")
    record_turn(
        "1",
        "upload_document",
        latency_ms=latency_ms,
        gap_ms=gap,
        extra={
            "filename": upload["filename"],
            "total_units": total_units,
            "insights": upload.get("insights", {}),
        },
    )

    # ── STEP 2: Start conversation — expect multi-role opener ─────────────
    banner("STEP 2 — Start conversation (multi-role opener, Explainer primary)")
    start = call("POST", f"/sessions/{session_id}/start")
    gap = consume_gap(start["__ended_at"])
    opener_msgs = start.get("messages", [])
    print(f"opener_count = {len(opener_msgs)}  (expected 3)")
    print(describe_messages(opener_msgs))
    print(f"latency_ms   = {start['__latency_ms']}")
    record_turn(
        "2",
        "start_conversation",
        role=start["role"],
        response=start["response"],
        messages=opener_msgs,
        latency_ms=start["__latency_ms"],
        gap_ms=gap,
        extra={
            "unit_index": start["unit_index"],
            "total_units": start["total_units"],
        },
    )

    # ── STEP 3: User message #1 on unit 1 ─────────────────────────────────
    banner("STEP 3 — User message #1 on unit 1 (expect primary + chime-in)")
    user_msg_1 = "Can you give me a quick analogy for what supervised learning is?"
    print(f"user_msg     = {user_msg_1}")
    msg1 = call(
        "POST",
        f"/sessions/{session_id}/message",
        json={"message": user_msg_1},
    )
    gap = consume_gap(msg1["__ended_at"])
    msgs1 = msg1.get("messages", [])
    print(f"reply_count  = {len(msgs1)}  (expected 2)  auto_nudge={msg1.get('auto_nudge')}")
    print(describe_messages(msgs1))
    print(f"latency_ms   = {msg1['__latency_ms']}")
    record_turn(
        "3",
        "user_message",
        role=msg1["role"],
        user_input=user_msg_1,
        response=msg1["response"],
        messages=msgs1,
        auto_nudge=msg1.get("auto_nudge", False),
        latency_ms=msg1["__latency_ms"],
        gap_ms=gap,
    )

    # ── STEP 4: User message #2 on unit 1 ─────────────────────────────────
    banner("STEP 4 — User message #2 on unit 1 (test cross-talk / continuity)")
    user_msg_2 = "Interesting — but what if the training labels are wrong sometimes?"
    print(f"user_msg     = {user_msg_2}")
    msg2 = call("POST", f"/sessions/{session_id}/message", json={"message": user_msg_2})
    gap = consume_gap(msg2["__ended_at"])
    msgs2 = msg2.get("messages", [])
    print(f"reply_count  = {len(msgs2)}  auto_nudge={msg2.get('auto_nudge')}")
    print(describe_messages(msgs2))
    print(f"latency_ms   = {msg2['__latency_ms']}")
    record_turn(
        "4",
        "user_message",
        role=msg2["role"],
        user_input=user_msg_2,
        response=msg2["response"],
        messages=msgs2,
        auto_nudge=msg2.get("auto_nudge", False),
        latency_ms=msg2["__latency_ms"],
        gap_ms=gap,
    )

    # ── STEP 5: User message #3 on unit 1 (should trigger auto-nudge) ─────
    banner("STEP 5 — User message #3 on unit 1 (expect auto-nudge to appear)")
    user_msg_3 = "Got it. One more: how is that different from unsupervised learning?"
    print(f"user_msg     = {user_msg_3}")
    msg3 = call("POST", f"/sessions/{session_id}/message", json={"message": user_msg_3})
    gap = consume_gap(msg3["__ended_at"])
    msgs3 = msg3.get("messages", [])
    nudge = msg3.get("auto_nudge", False)
    print(f"reply_count  = {len(msgs3)}  auto_nudge={nudge} (expected True)")
    print(describe_messages(msgs3))
    print(f"latency_ms   = {msg3['__latency_ms']}")
    record_turn(
        "5",
        "user_message_triggering_nudge",
        role=msg3["role"],
        user_input=user_msg_3,
        response=msg3["response"],
        messages=msgs3,
        auto_nudge=nudge,
        latency_ms=msg3["__latency_ms"],
        gap_ms=gap,
    )

    # ── STEP 6: Advance to unit 2 (fresh opener) ──────────────────────────
    banner("STEP 6 — Advance to unit 2 (fresh multi-role opener)")
    nxt1 = call("POST", f"/sessions/{session_id}/next")
    gap = consume_gap(nxt1["__ended_at"])
    nxt1_msgs = nxt1.get("messages", [])
    print(f"opener_count = {len(nxt1_msgs)}  (expected 3)")
    print(describe_messages(nxt1_msgs))
    print(f"latency_ms   = {nxt1['__latency_ms']}")
    record_turn(
        "6",
        "advance_to_next_unit",
        role=nxt1.get("role"),
        response=nxt1.get("response"),
        messages=nxt1_msgs,
        latency_ms=nxt1["__latency_ms"],
        gap_ms=gap,
        extra={"unit_index": nxt1["unit_index"], "completed": nxt1["completed"]},
    )

    # ── STEP 7: User interrupts ───────────────────────────────────────────
    banner("STEP 7 — User clicks interrupt")
    interrupt = call("POST", f"/sessions/{session_id}/interrupt")
    gap = consume_gap(interrupt["__ended_at"])
    print(f"interrupt ok = {interrupt.get('success', True)}")
    print(f"latency_ms   = {interrupt['__latency_ms']}")
    record_turn(
        "7",
        "interrupt",
        latency_ms=interrupt["__latency_ms"],
        gap_ms=gap,
        extra={k: v for k, v in interrupt.items() if not k.startswith("__")},
    )

    # ── STEP 8: Answer the interruption question ──────────────────────────
    banner("STEP 8 — User asks interruption question (single-role answer)")
    interrupt_q = "Wait — what's the difference between overfitting and underfitting?"
    print(f"user_msg     = {interrupt_q}")
    ans = call(
        "POST",
        f"/sessions/{session_id}/interrupt/message",
        json={"message": interrupt_q},
    )
    gap = consume_gap(ans["__ended_at"])
    ans_msgs = ans.get("messages", [])
    print(f"bot_role     = {ans['role']}  (may be routed to a different role)")
    print(f"msg_count    = {len(ans_msgs)}  (expected 1 — interruptions stay single-role)")
    print(describe_messages(ans_msgs))
    print(f"latency_ms   = {ans['__latency_ms']}")
    record_turn(
        "8",
        "interruption_answer",
        role=ans["role"],
        user_input=interrupt_q,
        response=ans["response"],
        messages=ans_msgs,
        latency_ms=ans["__latency_ms"],
        gap_ms=gap,
        extra={"interrupted_unit": ans.get("interrupted_unit")},
    )

    # ── STEP 9: Resume ────────────────────────────────────────────────────
    banner("STEP 9 — Resume from where we left off (brief 'back to it' line)")
    resume = call(
        "POST",
        f"/sessions/{session_id}/resume",
        json={"from_start": False},
    )
    gap = consume_gap(resume["__ended_at"])
    resume_msgs = resume.get("messages", [])
    print(f"msg_count    = {len(resume_msgs)}  (expected 1 — resume is not a new opener)")
    print(describe_messages(resume_msgs))
    print(f"latency_ms   = {resume['__latency_ms']}")
    record_turn(
        "9",
        "resume",
        role=resume.get("role"),
        response=resume.get("response"),
        messages=resume_msgs,
        latency_ms=resume["__latency_ms"],
        gap_ms=gap,
        extra={"unit_index": resume.get("unit_index")},
    )

    # ── STEP 10: Advance to unit 3 ────────────────────────────────────────
    banner("STEP 10 — Advance to unit 3 (final group opener)")
    nxt2 = call("POST", f"/sessions/{session_id}/next")
    gap = consume_gap(nxt2["__ended_at"])
    nxt2_msgs = nxt2.get("messages", [])
    print(f"opener_count = {len(nxt2_msgs)}")
    print(describe_messages(nxt2_msgs))
    print(f"latency_ms   = {nxt2['__latency_ms']}")
    record_turn(
        "10",
        "advance_to_next_unit",
        role=nxt2.get("role"),
        response=nxt2.get("response"),
        messages=nxt2_msgs,
        latency_ms=nxt2["__latency_ms"],
        gap_ms=gap,
        extra={"unit_index": nxt2["unit_index"], "completed": nxt2["completed"]},
    )

    # ── STEP 11: Final state ──────────────────────────────────────────────
    banner("STEP 11 — Final session state snapshot")
    final = call("GET", f"/sessions/{session_id}")
    gap = consume_gap(final["__ended_at"])
    print(f"final_role   = {final.get('current_role')}")
    print(f"unit         = {final.get('current_unit_index')} / {final.get('total_units')}")
    record_turn(
        "11",
        "final_state",
        role=final.get("current_role"),
        latency_ms=final["__latency_ms"],
        gap_ms=gap,
        extra={k: v for k, v in final.items() if not k.startswith("__")},
    )

    # ── Persist raw JSON ──────────────────────────────────────────────────
    JSON_PATH.write_text(
        json.dumps(
            {
                "run_started": STAMP,
                "session_id": session_id,
                "document": str(DOC_PATH),
                "config": cfg,
                "upload": {k: v for k, v in upload.items() if k != "__latency_ms"},
                "turns": turns,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nRaw JSON written to: {JSON_PATH}")
    print(f"Markdown target   : {MD_PATH}")
    print(f"Session id        : {session_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
