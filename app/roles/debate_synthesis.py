"""LLM-generated speakers for perspective-debate sessions (two viewpoints)."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from loguru import logger

from app.roles.role_templates import RoleTemplate, RoleType


# ── JSON extraction ────────────────────────────────────────────────────────────

def _extract_json_array(text: str) -> Optional[List[Any]]:
    """Try every reasonable strategy to pull a JSON array out of raw LLM text."""
    if not text:
        return None
    t = text.strip()

    # 1. Fenced code block: ```json [ ... ] ```
    fence = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", t, re.DOTALL | re.IGNORECASE)
    if fence:
        t = fence.group(1)
    else:
        # 2. Bare array anywhere in the string (greedy from first [ to last ])
        bracket = re.search(r"(\[[\s\S]*\])", t)
        if bracket:
            t = bracket.group(1)
        else:
            # 3. Some models output the two objects without wrapping them in an array.
            # Find all {...} top-level objects and wrap them.
            objects = re.findall(r"\{[\s\S]*?\}", t)
            if len(objects) >= 2:
                t = "[" + ", ".join(objects[:2]) + "]"

    try:
        data = json.loads(t)
        return data if isinstance(data, list) else None
    except json.JSONDecodeError:
        # Last-ditch: remove common non-JSON cruft (trailing commas, comments)
        cleaned = re.sub(r",\s*([}\]])", r"\1", t)
        try:
            data = json.loads(cleaned)
            return data if isinstance(data, list) else None
        except json.JSONDecodeError:
            return None


# ── Fallback personas (no LLM needed) ─────────────────────────────────────────

def _make_debate_template(
    *,
    name: str,
    viewpoint_label: str,
    system_prompt: str,
    instruction: str,
    priority_keywords: List[str],
    avoid_keywords: List[str],
    debate_index: int,
) -> RoleTemplate:
    """Construct a RoleTemplate with is_debate=True and full metadata."""
    rt = RoleType.EXPLAINER if debate_index == 0 else RoleType.CHALLENGER
    return RoleTemplate(
        name=name,
        role_type=rt,
        system_prompt=system_prompt,
        instruction=instruction,
        priority_keywords=priority_keywords,
        avoid_keywords=avoid_keywords,
        temperature=0.65,
        max_tokens=480,
        is_debate=True,
        metadata={
            "debate_index": debate_index,
            "synthetic": True,
            "viewpoint_label": viewpoint_label,
        },
    )


def _fallback_personas(topic_hint: str) -> List[RoleTemplate]:
    hint = (topic_hint or "").strip()
    hint_clause = f" The document concerns: {hint}." if hint else ""
    return [
        _make_debate_template(
            name="Viewpoint A",
            viewpoint_label="Perspective A — one cultural, ideological, or stakeholder angle",
            system_prompt=(
                f"You are «Viewpoint A», one of two debaters discussing an uploaded document. "
                f"You represent one particular cultural, ideological, or stakeholder perspective "
                f"that the text invites.{hint_clause} "
                "Stay in character throughout. Ground every claim in the provided study material. "
                "Do not invent facts."
            ),
            instruction=(
                "Present and defend your assigned angle on the material. "
                "Pull evidence from the text; acknowledge tensions where the source is ambiguous; "
                "do not adopt the opposing stance."
            ),
            priority_keywords=["my view", "from our side", "our perspective", "we believe", "this shows"],
            avoid_keywords=["on the other hand", "both sides agree"],
            debate_index=0,
        ),
        _make_debate_template(
            name="Viewpoint B",
            viewpoint_label="Perspective B — the contrasting angle",
            system_prompt=(
                f"You are «Viewpoint B», one of two debaters discussing an uploaded document. "
                f"You represent a contrasting cultural, ideological, or stakeholder perspective "
                f"to your debate partner.{hint_clause} "
                "Stay in character throughout. Ground every claim in the provided study material. "
                "Do not invent facts."
            ),
            instruction=(
                "Offer the counterpoint to the other debater. "
                "Pull evidence and emphasis from the text; show where your interpretation "
                "diverges from theirs without being dismissive."
            ),
            priority_keywords=["counter", "however", "on the other hand", "critics argue", "alternative reading"],
            avoid_keywords=["we all agree", "both sides"],
            debate_index=1,
        ),
    ]


# ── Build from LLM output ──────────────────────────────────────────────────────

def build_debate_personas_from_llm(
    raw_llm_text: str,
    hint: str,
) -> List[RoleTemplate]:
    """Parse model output into two RoleTemplate debate speakers."""
    arr = _extract_json_array(raw_llm_text)
    if not arr or len(arr) < 2:
        logger.warning(
            "Debate persona JSON missing or incomplete — falling back to generic personas. "
            f"(raw preview: {raw_llm_text[:200]!r})"
        )
        return _fallback_personas(hint)

    out: List[RoleTemplate] = []
    for i, item in enumerate(arr[:2]):
        if not isinstance(item, dict):
            logger.warning(f"Debate persona item {i} is not a dict: {type(item)}")
            continue

        name = str(item.get("name") or f"Perspective {i + 1}").strip() or f"Perspective {i + 1}"
        viewpoint = str(
            item.get("viewpoint_label") or item.get("viewpoint") or item.get("stance") or ""
        ).strip()
        system_prompt = str(item.get("system_prompt") or "").strip()
        instruction = str(item.get("instruction") or "").strip()

        # Embed viewpoint into system_prompt so it's always visible to the LLM
        if viewpoint and viewpoint not in system_prompt:
            system_prompt = f"You represent: {viewpoint}\n\n{system_prompt}".strip()
        if not system_prompt:
            system_prompt = (
                f"You are «{name}», one of two debaters. "
                f"{('You represent: ' + viewpoint + '.') if viewpoint else ''} "
                "Ground every claim in the study material."
            ).strip()
        if not instruction:
            instruction = (
                "Debate in character: defend your position using the document, "
                "engage the other voice, and keep the student in the loop."
            )

        pk = item.get("priority_keywords")
        ak = item.get("avoid_keywords")
        priority_keywords = [str(x) for x in pk] if isinstance(pk, list) else []
        avoid_keywords = [str(x) for x in ak] if isinstance(ak, list) else []

        out.append(
            _make_debate_template(
                name=name[:80],
                viewpoint_label=viewpoint[:500] or f"Perspective {i + 1}",
                system_prompt=system_prompt[:4000],
                instruction=instruction[:4000],
                priority_keywords=priority_keywords[:40],
                avoid_keywords=avoid_keywords[:40],
                debate_index=i,
            )
        )

    if len(out) < 2:
        logger.warning(
            f"Only {len(out)} valid persona(s) parsed from LLM output; using fallback"
        )
        return _fallback_personas(hint)
    return out


# ── Persona synthesis prompt ───────────────────────────────────────────────────

def render_debate_persona_prompt(
    document_excerpt: str,
    user_hint: str,
) -> str:
    """Build the one-shot prompt that asks the model for exactly two JSON persona objects."""
    hint = (user_hint or "").strip()

    # Example is fully inlined so even small models can pattern-match against it.
    example = (
        '[\n'
        '  {\n'
        '    "name": "British Colonial Official",\n'
        '    "viewpoint_label": "Pro-Empire administrator: justifies colonialism through order, trade, and civilising mission",\n'
        '    "system_prompt": "You represent the British colonial establishment. You believe the Empire brought infrastructure, rule of law, and trade networks that the subcontinent lacked. Ground all claims in the provided document.",\n'
        '    "instruction": "Defend British administrative choices and policies described in the text. Acknowledge costs but frame them as necessary or exaggerated by critics. Stay in character throughout.",\n'
        '    "priority_keywords": ["order", "administration", "trade", "stability", "progress"],\n'
        '    "avoid_keywords": ["oppression", "exploitation", "resistance"]\n'
        '  },\n'
        '  {\n'
        '    "name": "Indian Independence Advocate",\n'
        '    "viewpoint_label": "Anti-colonial nationalist: highlights exploitation, sovereignty, and the freedom struggle",\n'
        '    "system_prompt": "You represent the Indian independence movement. You view British rule as exploitative, culturally destructive, and a denial of self-determination. Ground all claims in the provided document.",\n'
        '    "instruction": "Highlight evidence of exploitation, cultural erasure, and resistance in the text. Challenge the other debater\'s framing. Stay in character throughout.",\n'
        '    "priority_keywords": ["exploitation", "resistance", "sovereignty", "freedom", "oppression"],\n'
        '    "avoid_keywords": ["stability", "civilising", "order"]\n'
        '  }\n'
        ']'
    )

    return (
        "TASK: Design exactly TWO debate personas for a student studying an uploaded document.\n"
        "The two speakers must hold GENUINELY CONTRASTING viewpoints "
        "(different cultures, ideologies, time periods, or stakeholder positions).\n"
        "\n"
        "OUTPUT FORMAT: Return ONLY a raw JSON array — no preamble, no explanation, "
        "no markdown fences, no text before or after the array. "
        "Start your entire response with [ and end it with ].\n"
        "\n"
        "SCHEMA — each object in the array:\n"
        '  "name"           : short human-readable title (≤ 8 words)\n'
        '  "viewpoint_label": one sentence describing what position this voice holds\n'
        '  "system_prompt"  : who this speaker is, their stance, and the constraint to '
        "ground claims in the document (2-4 sentences)\n"
        '  "instruction"    : how they should argue across debate turns (1-3 sentences)\n'
        '  "priority_keywords": 3-8 short tokens that signal a user message matches '
        "this persona's side\n"
        '  "avoid_keywords" : 2-6 tokens this persona would NOT naturally use\n'
        "\n"
        "RULES:\n"
        "- Both personas must be able to engage the SAME document excerpt below.\n"
        "- Do NOT pick sides morally; do NOT use slurs; maintain academic tone.\n"
        "- Names should be concise and self-explanatory.\n"
        f"- User hint (use this to shape the personas, may be empty): {hint!r}\n"
        "- If the hint is empty, infer the most interesting tension from the excerpt.\n"
        "\n"
        "EXAMPLE OUTPUT (British India topic — adapt to your topic):\n"
        f"{example}\n"
        "\n"
        "Now generate personas for the document below.\n"
        "Document excerpt:\n"
        '"""\n'
        f"{document_excerpt[:8000]}\n"
        '"""\n'
        "\n"
        "JSON array:"
    )
