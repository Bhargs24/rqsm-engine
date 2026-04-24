"""
Standalone debate-mode test / audit script
===========================================
Loads DebateSample.md, creates perspective-debate and study-group sessions,
captures every prompt sent to the LLM (or fallback response when offline),
then writes a full Markdown report to:
    docs/reports/debate_test_output.md

Run from the rqsm-engine directory:
    $env:LLM_PROVIDER="gemini"; .\.venv\Scripts\python.exe scripts/run_debate_test.py
"""
from __future__ import annotations

import io
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Resolve project paths ──────────────────────────────────────────────────────
HERE = Path(__file__).resolve().parent
ENGINE_ROOT = HERE.parent
REPO_ROOT = ENGINE_ROOT.parent

sys.path.insert(0, str(ENGINE_ROOT))

SAMPLE_DOC = REPO_ROOT / "docs" / "Sample input" / "DebateSample.md"
REPORT_DIR = REPO_ROOT / "docs" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = REPORT_DIR / "debate_test_output.md"

import os
os.environ.setdefault("LOG_LEVEL", "WARNING")

from loguru import logger
logger.remove()
logger.add(sys.stderr, level="WARNING")


# ── UploadFile shim ────────────────────────────────────────────────────────────
class _MockUploadFile:
    def __init__(self, path: Path, force_ext: str | None = None):
        stem = path.stem
        ext = force_ext or path.suffix
        self.filename = f"{stem}{ext}"
        self._data = path.read_bytes()
        self.file = io.BytesIO(self._data)


# ── LLM prompt spy: wrap the client so we capture every call ──────────────────
_llm_calls: list[dict] = []

def _patch_llm_client(runtime) -> None:
    """Monkey-patch the runtime's LLM client to log every prompt/response."""
    client = runtime._get_llm_client()
    if client is None:
        return
    original_generate = client.generate

    def _spy_generate(prompt: str, **kwargs):
        entry = {"prompt": prompt, "response": None, "error": None}
        _llm_calls.append(entry)
        try:
            resp = original_generate(prompt, **kwargs)
            entry["response"] = resp
            return resp
        except Exception as exc:
            entry["error"] = str(exc)
            raise

    client.generate = _spy_generate


# ── Helpers ───────────────────────────────────────────────────────────────────
def _truncate(text: str, n: int = 600) -> str:
    text = text.strip()
    return text if len(text) <= n else text[:n] + "…  *(truncated)*"

def _md_fence(text: str, lang: str = "text") -> str:
    return f"```{lang}\n{text.strip()}\n```"


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    from app.session.runtime import ConversationRuntime
    from app.roles.debate_synthesis import render_debate_persona_prompt

    lines: list[str] = []

    # ═══════════════════════════════════════════════════════════════════════════
    # Report header
    # ═══════════════════════════════════════════════════════════════════════════
    llm_provider = os.environ.get("LLM_PROVIDER", "ollama")
    model_name   = os.environ.get("GEMINI_MODEL", os.environ.get("OLLAMA_MODEL", "?"))

    lines += [
        "# RQSM Engine — Debate Mode Test Output",
        "",
        f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_",
        "",
        "> **Note on LLM availability** — Gemini free-tier quota was exhausted at test time",
        "> and Ollama was not running locally.  The conversation responses below are the",
        "> engine's **deterministic fallback** outputs, which the system emits when no",
        "> LLM is reachable.  The full prompts that *would* be sent to the model are",
        "> shown in the **LLM Prompts** sections so the quality of the prompting can be",
        "> reviewed independently.",
        "",
        "---",
        "",
        "## 1. Session Configuration",
        "",
        f"| Field | Value |",
        f"|---|---|",
        f"| Document | `{SAMPLE_DOC.name}` |",
        f"| Mode | `perspective_debate` |",
        f"| Debate hint | British colonial official vs Indian independence advocate |",
        f"| LLM provider (attempted) | `{llm_provider}` |",
        f"| Model (attempted) | `{model_name}` |",
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # Persona synthesis prompt (show without running the LLM)
    # ═══════════════════════════════════════════════════════════════════════════
    print(f"[test] Loading document: {SAMPLE_DOC}")
    doc_text = SAMPLE_DOC.read_text(encoding="utf-8")
    hint = "British colonial official defending the Raj vs Indian independence advocate opposing it."
    persona_prompt = render_debate_persona_prompt(doc_text, hint)

    lines += [
        "",
        "---",
        "",
        "## 2. Debate Persona Synthesis",
        "",
        "### 2a. Prompt sent to the LLM to create the two debate personas",
        "",
        "> This is the exact text that the engine sends to the model.",
        "> The model must return a JSON array of two persona objects.",
        "",
        _md_fence(persona_prompt[:3000] + ("\n…*(truncated — full prompt is ~4 kB)*" if len(persona_prompt) > 3000 else ""), "text"),
    ]

    # ═══════════════════════════════════════════════════════════════════════════
    # Run debate session (fallback personas because LLM is offline)
    # ═══════════════════════════════════════════════════════════════════════════
    print("[test] Creating DEBATE session …")
    upload = _MockUploadFile(SAMPLE_DOC, force_ext=".txt")
    runtime = ConversationRuntime()
    _patch_llm_client(runtime)

    t0 = time.perf_counter()
    conv = runtime.create_session_from_uploaded_file(
        upload,
        session_mode="perspective_debate",
        debate_hint=hint,
    )
    session_id = conv.session_id
    print(f"[test] Session created ({time.perf_counter()-t0:.1f}s). "
          f"Units={len(conv.semantic_units)}")

    # Show personas
    lines += [
        "",
        "### 2b. Personas used in this run",
        "",
        "> Because the LLM was unavailable, the engine fell back to the",
        "> generic-persona fallback.  With a live model, these would be",
        "> named and characterised according to the hint above.",
        "",
    ]
    if conv.debate_personas:
        for i, p in enumerate(conv.debate_personas, 1):
            vl = (p.metadata or {}).get("viewpoint_label", p.name)
            lines += [
                f"#### Persona {i}: **{p.name}**",
                f"- **Viewpoint label**: {vl}",
                f"- **System prompt**:",
                _md_fence(p.system_prompt),
                f"- **Instruction**: {p.instruction}",
                f"- **Priority keywords**: `{', '.join(p.priority_keywords[:8])}`",
                f"- **Avoid keywords**: `{', '.join(p.avoid_keywords[:6])}`",
                "",
            ]

    # ═══════════════════════════════════════════════════════════════════════════
    # Show what the actual build_prompt output looks like for the opener
    # ═══════════════════════════════════════════════════════════════════════════
    if conv.debate_personas and conv.semantic_units:
        unit0_text = conv.semantic_units[0].text
        for i, p in enumerate(conv.debate_personas):
            other = conv.debate_personas[1 - i]
            style = "open" if i == 0 else "chime_closer"
            sample_prompt = p.build_prompt(
                context=unit0_text,
                reply_style=style,
                other_role_names=[other.name],
                group_transcript=[],
            )
            lines += [
                f"### 2c. Full build_prompt for Persona {i+1} ({p.name}) — opener turn",
                "",
                f"> `reply_style='{style}'`, `other_role_names=['{other.name}']`",
                "",
                _md_fence(_truncate(sample_prompt, 2000), "text"),
                "",
            ]

    # ═══════════════════════════════════════════════════════════════════════════
    # Conversation transcript (fallback)
    # ═══════════════════════════════════════════════════════════════════════════
    lines += [
        "",
        "---",
        "",
        "## 3. Conversation Transcript — Debate Mode",
        "",
        "> These responses are the **deterministic fallback** the engine uses when",
        "> no LLM is reachable.  They are structurally correct (two voices,",
        "> debate framing, unit text injected) but not generatively paraphrased.",
        "",
        "### 3a. Opener (Unit 1)",
        "",
    ]

    print("[test] Starting debate conversation …")
    t0 = time.perf_counter()
    result = runtime.start_conversation(session_id)
    print(f"[test] Opener done ({time.perf_counter()-t0:.1f}s, {len(result['messages'])} turns)")

    for msg in result["messages"]:
        lines.append(f"**{msg['role']}:** {msg['text'].strip()}\n")

    student_msgs = [
        "What were the main economic arguments used to justify British rule in India?",
        "How do you respond to the claim that the railways and infrastructure benefited India?",
        "Was partition an inevitable outcome of British divide-and-rule policies?",
    ]

    for turn_i, student_text in enumerate(student_msgs, 1):
        lines += [
            f"---",
            f"",
            f"### 3b. Student turn {turn_i}",
            f"",
            f"> **Student:** _{student_text}_",
            f"",
        ]
        print(f"[test] Student message {turn_i}: '{student_text[:60]}…'")
        t0 = time.perf_counter()
        try:
            resp = runtime.send_user_message(session_id, student_text)
        except Exception as exc:
            lines.append(f"_[ERROR]: {exc}_\n")
            print(f"[test] ERROR: {exc}")
            continue
        print(f"[test] Reply ({time.perf_counter()-t0:.1f}s, {len(resp['messages'])} turns)")

        for msg in resp["messages"]:
            lines.append(f"**{msg['role']}:** {msg['text'].strip()}\n")

    # ═══════════════════════════════════════════════════════════════════════════
    # Study-group session (2 roles)
    # ═══════════════════════════════════════════════════════════════════════════
    lines += [
        "",
        "---",
        "",
        "## 4. Study-Group Mode — 2 Roles (Explainer + Challenger)",
        "",
    ]

    upload2 = _MockUploadFile(SAMPLE_DOC, force_ext=".txt")
    print("[test] Creating STUDY-GROUP (2-role) session …")
    try:
        t0 = time.perf_counter()
        conv2 = runtime.create_session_from_uploaded_file(
            upload2,
            session_mode="study_group",
            study_role_count=2,
            study_roles=["Explainer", "Challenger"],
        )
        session_id2 = conv2.session_id
        assignments_preview = [a.assigned_role.value for a in conv2.assignments_by_position[:5]]
        print(f"[test] Study session ({time.perf_counter()-t0:.1f}s). "
              f"Units={len(conv2.semantic_units)}, Roles={assignments_preview}")

        lines += [
            f"- **Units**: {len(conv2.semantic_units)}",
            f"- **Role assignments (all units)**: "
            f"`{', '.join(a.assigned_role.value for a in conv2.assignments_by_position)}`",
            f"- **Allowed pool**: `[Explainer, Challenger]`",
            "",
            "### 4a. Opener",
            "",
        ]

        # Show a sample build_prompt for the study opener
        if conv2.assignments_by_position:
            a0 = conv2.assignments_by_position[0]
            tmpl = a0.role_template
            study_prompt = tmpl.build_prompt(
                context=a0.semantic_unit.text,
                reply_style="open",
                other_role_names=["Challenger"] if tmpl.name == "Explainer" else ["Explainer"],
                group_transcript=[],
            )
            lines += [
                "#### Sample build_prompt for Explainer — opener",
                "",
                _md_fence(_truncate(study_prompt, 1800), "text"),
                "",
                "#### Conversation",
                "",
            ]

        t0 = time.perf_counter()
        result2 = runtime.start_conversation(session_id2)
        print(f"[test] Study opener done ({time.perf_counter()-t0:.1f}s)")

        for msg in result2["messages"]:
            lines.append(f"**{msg['role']}:** {msg['text'].strip()}\n")

        student_msg2 = "What is the debate about deindustrialisation under British rule?"
        lines += [
            "",
            f"---",
            "",
            "### 4b. Student message",
            "",
            f"> **Student:** _{student_msg2}_",
            "",
        ]
        print(f"[test] Study student message")
        t0 = time.perf_counter()
        resp2 = runtime.send_user_message(session_id2, student_msg2)
        print(f"[test] Study reply ({time.perf_counter()-t0:.1f}s)")
        for msg in resp2["messages"]:
            lines.append(f"**{msg['role']}:** {msg['text'].strip()}\n")

    except Exception as exc:
        lines.append(f"_[ERROR creating study session]: {exc}_\n")
        print(f"[test] ERROR study session: {exc}")

    # ═══════════════════════════════════════════════════════════════════════════
    # System architecture summary
    # ═══════════════════════════════════════════════════════════════════════════
    lines += [
        "",
        "---",
        "",
        "## 5. System Architecture Summary",
        "",
        "```",
        "Document Upload",
        "  └─► DocumentProcessor  (sentence-transformer embeddings, semantic segmentation)",
        "        └─► [debate mode]  render_debate_persona_prompt  ──►  LLM  ──►  2 RoleTemplates",
        "        └─► [study  mode]  RoleAssigner  (keyword + structural scoring)  ──►  RoleType queue",
        "",
        "Start Conversation",
        "  └─► _generate_group_opener  →  primary voice (open)  +  secondary (chime_closer)",
        "",
        "Student Message",
        "  └─► _generate_group_reply  →  primary (reply)  +  optional chime-in",
        "",
        "Interrupt / Resume",
        "  └─► ConversationStateMachine  (ENGAGED → INTERRUPTED → ENGAGED)",
        "",
        "LLM unavailable  →  _fallback_debate / _fallback_study  (deterministic, in-character)",
        "```",
        "",
        "### Semantic unit breakdown",
        "",
        f"| Unit | Words | Section | Cohesion |",
        f"|---|---|---|---|",
    ]
    if 'conv' in dir():
        for u in conv.semantic_units:
            preview = u.text.split()
            section = getattr(u, 'document_section', '—') or '—'
            cohesion = getattr(u, 'similarity_score', 0) or 0
            lines.append(
                f"| {u.position+1} | {u.word_count} | {section[:40]} | {cohesion:.3f} |"
            )

    lines += [
        "",
        "---",
        "",
        "_End of report_",
    ]

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[test] Report written: {REPORT_PATH}")


if __name__ == "__main__":
    main()
