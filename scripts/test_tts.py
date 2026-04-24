"""
TTS integration test
====================
Tests every pedagogical role + two debate persona voices directly against the
Google Cloud TTS API (no HTTP server needed).  Saves one MP3 per role to
docs/reports/tts_samples/ and writes a results report to
docs/reports/tts_test_results.md

Run from the rqsm-engine directory:
    $env:GOOGLE_APPLICATION_CREDENTIALS="google_tts_key.json"
    .venv/Scripts/python.exe scripts/test_tts.py
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ── path setup ─────────────────────────────────────────────────────────────────
HERE        = Path(__file__).resolve().parent
ENGINE_ROOT = HERE.parent
REPO_ROOT   = ENGINE_ROOT.parent

sys.path.insert(0, str(ENGINE_ROOT))

SAMPLES_DIR  = REPO_ROOT / "docs" / "reports" / "tts_samples"
REPORT_PATH  = REPO_ROOT / "docs" / "reports" / "tts_test_results.md"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

# Point credentials at the key file if not already set
creds_env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
if not creds_env or not Path(creds_env).exists():
    key_path = ENGINE_ROOT / "google_tts_key.json"
    if key_path.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(key_path)
        print(f"[tts-test] Using credentials: {key_path}")
    else:
        print(f"[tts-test] ERROR: google_tts_key.json not found at {key_path}")
        sys.exit(1)

import os as _os
_os.environ.setdefault("LOG_LEVEL", "WARNING")

from loguru import logger
logger.remove()
logger.add(sys.stderr, level="WARNING")

from app.tts.service import PEDAGOGICAL_VOICE_MAP, _DEBATE_VOICE_POOL, _voice_for_role, TTSService


# ── Test cases ─────────────────────────────────────────────────────────────────

STUDY_CASES = [
    (
        "Explainer",
        "The period of British rule in India is one of the most contested chapters "
        "in modern history. Let me walk you through the key arguments on both sides."
    ),
    (
        "Challenger",
        "Before we accept the pro-Empire narrative at face value, consider this: "
        "every so-called benefit came at enormous human and economic cost. "
        "Can modernisation justify subjugation?"
    ),
    (
        "Summarizer",
        "To recap what we have covered so far: the debate centres on whether "
        "infrastructure and legal reforms outweigh the documented harms of "
        "economic extraction, deindustrialisation, and political oppression."
    ),
    (
        "Example-Generator",
        "Here is a concrete example. The Bengal famine of 1943 killed roughly "
        "two to three million people, yet grain exports from India continued "
        "throughout—a vivid illustration of colonial priorities in practice."
    ),
    (
        "Misconception-Spotter",
        "A common misconception here is that Indians universally welcomed "
        "British legal reforms. In reality, many reformers explicitly framed "
        "their demands in terms of self-determination, not gratitude."
    ),
]

DEBATE_CASES = [
    (
        "British Colonial Official",
        0,
        "The Empire brought railways, a unified postal system, and codified law "
        "to a subcontinent that had previously been fragmented into dozens of "
        "competing kingdoms. These are lasting institutional contributions."
    ),
    (
        "Indian Independence Advocate",
        1,
        "Those railways were built to extract resources, not to serve the "
        "Indian people. The so-called rule of law excluded Indians from its "
        "highest offices and was enforced through repression when challenged."
    ),
]

ALL_CASES = [(r, None, t) for r, t in STUDY_CASES] + DEBATE_CASES


def run_test(svc: TTSService, role: str, text: str, persona_index=None) -> dict:
    """Synthesize one sample and return a result dict."""
    voice_cfg = _voice_for_role(role, persona_index)
    result = {
        "role": role,
        "voice_name": voice_cfg["name"],
        "language_code": voice_cfg["language_code"],
        "persona_index": persona_index,
        "text_chars": len(text),
        "text_preview": text[:80],
        "mp3_bytes": None,
        "duration_ms": None,
        "mp3_path": None,
        "error": None,
        "status": "PENDING",
    }
    t0 = time.perf_counter()
    try:
        mp3 = svc.synthesize(text, role, persona_index)
        elapsed = int((time.perf_counter() - t0) * 1000)
        result["mp3_bytes"]   = len(mp3)
        result["duration_ms"] = elapsed
        result["status"]      = "PASS"

        # Save MP3 file
        safe_name = role.replace(" ", "_").replace("-", "_").lower()
        out_path = SAMPLES_DIR / f"{safe_name}.mp3"
        out_path.write_bytes(mp3)
        result["mp3_path"] = str(out_path.relative_to(REPO_ROOT))
        print(
            f"  [PASS] {role:28s}  voice={voice_cfg['name']:22s}  "
            f"{len(mp3):>7,} bytes  {elapsed:>5}ms  -> {out_path.name}"
        )
    except Exception as exc:
        elapsed = int((time.perf_counter() - t0) * 1000)
        result["error"]       = str(exc)
        result["duration_ms"] = elapsed
        result["status"]      = "FAIL"
        print(f"  [FAIL] {role:28s}  {exc}")
    return result


def main():
    print("\n" + "=" * 70)
    print("RQSM Engine — TTS Integration Test")
    print(f"Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Key file  : {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")
    print("=" * 70)

    svc = TTSService()
    results = []

    # ── Test cache hit (second call for same text should be instant) ──────────
    print("\n[1/3] Pedagogical roles (5 voices)")
    for role, text in STUDY_CASES:
        results.append(run_test(svc, role, text))

    print("\n[2/3] Debate persona voices (with persona_index for distinct voice guarantee)")
    for role, idx, text in DEBATE_CASES:
        results.append(run_test(svc, role, text, persona_index=idx))

    print("\n[3/3] Cache test (repeat Explainer - should be < 5ms)")
    t0 = time.perf_counter()
    mp3 = svc.synthesize(STUDY_CASES[0][1], "Explainer")
    cache_ms = int((time.perf_counter() - t0) * 1000)
    cache_pass = cache_ms < 50
    print(
        f"  [{'PASS' if cache_pass else 'FAIL'}] Cache hit: {cache_ms}ms "
        f"({len(mp3):,} bytes from cache)"
    )

    # ── Write report ──────────────────────────────────────────────────────────
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    total  = len(results)

    lines = [
        "# RQSM Engine — TTS Integration Test Results",
        "",
        f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_",
        "",
        f"**{passed}/{total} tests passed**  |  "
        f"{'All voices operational' if failed == 0 else f'{failed} failures'}",
        "",
        "---",
        "",
        "## Voice Assignments",
        "",
        "### Pedagogical roles",
        "",
        "| Role | Voice | Accent | Gender |",
        "|---|---|---|---|",
    ]
    for role, cfg in PEDAGOGICAL_VOICE_MAP.items():
        lines.append(f"| {role} | `{cfg['name']}` | {cfg['language_code']} | {cfg['ssml_gender'].title()} |")

    lines += [
        "",
        "### Debate persona pool (hash-based assignment)",
        "",
        "| Pool index | Voice | Accent | Gender |",
        "|---|---|---|---|",
    ]
    for i, cfg in enumerate(_DEBATE_VOICE_POOL):
        lines.append(f"| {i} | `{cfg['name']}` | {cfg['language_code']} | {cfg['ssml_gender'].title()} |")

    lines += [
        "",
        "---",
        "",
        "## Synthesis Results",
        "",
        "| # | Role | Voice (Accent) | Persona idx | Status | Size | Latency | File |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(results, 1):
        status_icon = "✅" if r["status"] == "PASS" else "❌"
        size_str    = f"{r['mp3_bytes']:,} B" if r["mp3_bytes"] else "—"
        lat_str     = f"{r['duration_ms']}ms" if r["duration_ms"] else "—"
        file_str    = f"`{Path(r['mp3_path']).name}`" if r["mp3_path"] else "—"
        idx_str     = str(r["persona_index"]) if r["persona_index"] is not None else "—"
        lines.append(
            f"| {i} | {r['role']} | `{r['voice_name']}` ({r['language_code']}) | "
            f"{idx_str} | {status_icon} {r['status']} | {size_str} | {lat_str} | {file_str} |"
        )
        if r["error"]:
            lines.append(f"|   | *Error* | `{r['error'][:120]}` | | | | |")

    lines += [
        "",
        f"**Cache hit test**: {cache_ms}ms  {'✅ PASS' if cache_pass else '❌ FAIL (expected < 50ms)'}",
        "",
        "---",
        "",
        "## Sample Texts Used",
        "",
    ]
    for i, (role, _idx, text) in enumerate(ALL_CASES, 1):
        lines.append(f"**{i}. {role}:** _{text[:150]}_\n")

    lines += [
        "",
        "## MP3 Samples",
        "",
        f"Audio files saved to `docs/reports/tts_samples/`:",
        "",
    ]
    for r in results:
        if r["mp3_path"]:
            lines.append(f"- `{Path(r['mp3_path']).name}` — {r['role']}")

    lines += ["", "---", "_End of report_"]

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print("\n" + "=" * 70)
    print(f"Results: {passed}/{total} passed  |  cache: {'PASS' if cache_pass else 'FAIL'}")
    print(f"Report:  {REPORT_PATH}")
    print(f"Samples: {SAMPLES_DIR}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
