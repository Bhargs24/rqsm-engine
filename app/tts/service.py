"""
Google Cloud Text-to-Speech service.

Each pedagogical role is assigned a distinct Neural2 voice so students can
distinguish speakers by sound as well as by the role tag.  Debate personas
(arbitrary names) are assigned voices deterministically by hashing the role
name against a pool of accent-varied voices.
"""
from __future__ import annotations

import hashlib
from typing import Dict, Optional

from loguru import logger

# ── Per-role voice assignments ─────────────────────────────────────────────────
# Using Neural2 voices for highest naturalness.
# Voices: https://cloud.google.com/text-to-speech/docs/voices

PEDAGOGICAL_VOICE_MAP: Dict[str, dict] = {
    "Explainer": {
        "name": "en-US-Neural2-J",   # warm, clear US male — best for teaching
        "language_code": "en-US",
        "ssml_gender": "MALE",
    },
    "Challenger": {
        "name": "en-US-Neural2-A",   # direct, assertive US female
        "language_code": "en-US",
        "ssml_gender": "FEMALE",
    },
    "Summarizer": {
        "name": "en-GB-Neural2-A",   # calm, measured British female
        "language_code": "en-GB",
        "ssml_gender": "FEMALE",
    },
    "Example-Generator": {
        "name": "en-US-Neural2-D",   # friendly, energetic US male
        "language_code": "en-US",
        "ssml_gender": "MALE",
    },
    "Misconception-Spotter": {
        "name": "en-US-Neural2-F",   # cautionary, precise US female
        "language_code": "en-US",
        "ssml_gender": "FEMALE",
    },
}

# Debate persona voices — accent-varied pool so opposing voices sound distinct
_DEBATE_VOICE_POOL = [
    {"name": "en-GB-Neural2-B", "language_code": "en-GB", "ssml_gender": "MALE"},   # British
    {"name": "en-IN-Neural2-B", "language_code": "en-IN", "ssml_gender": "MALE"},   # Indian English
    {"name": "en-AU-Neural2-B", "language_code": "en-AU", "ssml_gender": "MALE"},   # Australian
    {"name": "en-US-Neural2-I", "language_code": "en-US", "ssml_gender": "MALE"},   # US alt
]

def _voice_for_role(role_name: str, persona_index: int | None = None) -> dict:
    """Return the voice config for a given role name.

    For debate personas (not in the pedagogical map) the optional *persona_index*
    (0 or 1) is used directly as the pool offset so the two debaters are
    guaranteed to sound different regardless of how their names happen to hash.
    When *persona_index* is omitted the name is hashed as a fallback.
    """
    if role_name in PEDAGOGICAL_VOICE_MAP:
        return PEDAGOGICAL_VOICE_MAP[role_name]
    if persona_index is not None:
        idx = persona_index % len(_DEBATE_VOICE_POOL)
    else:
        idx = int(hashlib.md5(role_name.encode()).hexdigest(), 16) % len(_DEBATE_VOICE_POOL)
    return _DEBATE_VOICE_POOL[idx]


# ── TTS Service ────────────────────────────────────────────────────────────────

class TTSService:
    """Thin wrapper around google-cloud-texttospeech with role-based voice routing."""

    # Hard limit to avoid excessively long TTS requests (characters)
    MAX_CHARS = 4800

    def __init__(self):
        self._client = None
        # Simple in-process LRU-style cache: {cache_key: mp3_bytes}
        # Keeps frequently repeated phrases (e.g. unit openers) free.
        self._cache: Dict[str, bytes] = {}
        self._cache_max = 512  # max cached entries

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from google.cloud import texttospeech  # noqa: F401
        except ImportError:
            raise RuntimeError(
                "google-cloud-texttospeech is not installed. "
                "Run: pip install google-cloud-texttospeech"
            )
        try:
            self._client = texttospeech.TextToSpeechClient()
            logger.info("Google TTS client initialised")
        except Exception as exc:
            raise RuntimeError(f"Failed to create Google TTS client: {exc}") from exc
        return self._client

    def synthesize(self, text: str, role: str, persona_index: int | None = None) -> bytes:
        """
        Return MP3 bytes for *text* spoken in the voice assigned to *role*.

        *persona_index* (0 or 1) is used for debate personas to guarantee that
        the two voices are always distinct.  Pass ``None`` for pedagogical roles.
        Results are cached per (role, text) pair.
        """
        if not text or not text.strip():
            raise ValueError("text must be non-empty")

        # Truncate silently to protect against runaway tokens
        text = text.strip()[: self.MAX_CHARS]

        cache_key = f"{role}\x00{text}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        from google.cloud import texttospeech

        client    = self._get_client()
        voice_cfg = _voice_for_role(role, persona_index)

        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_cfg["language_code"],
            name=voice_cfg["name"],
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=0.97,   # very slightly slower than default — better comprehension
            pitch=0.0,
        )

        logger.debug(f"TTS synthesize: role={role!r}, voice={voice_cfg['name']}, chars={len(text)}")
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
        mp3 = response.audio_content

        # Evict oldest entry if cache is full
        if len(self._cache) >= self._cache_max:
            oldest = next(iter(self._cache))
            del self._cache[oldest]

        self._cache[cache_key] = mp3
        return mp3


# ── Module-level singleton ─────────────────────────────────────────────────────

_instance: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    global _instance
    if _instance is None:
        _instance = TTSService()
    return _instance
