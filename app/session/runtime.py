"""In-memory runtime for single-document conversational sessions."""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4
import re
import time

from fastapi import UploadFile
from loguru import logger

from app.document.processor import DocumentProcessor
from app.document.segmenter import SemanticUnit
from app.llm.client import LLMClient
from app.roles.debate_synthesis import build_debate_personas_from_llm, render_debate_persona_prompt
from app.roles.role_assignment import RoleAssignment, RoleAssigner, RoleScore
from app.roles.role_templates import RoleType, RoleTemplate, find_best_among_templates, role_library
from app.config import settings
from app.state_machine.conversation_state import ConversationState, ConversationStateMachine, EventType


@dataclass
class ActiveConversation:
    """Runtime object for one active in-memory session."""

    session_id: str
    filename: str
    semantic_units: List[SemanticUnit]
    assignments_by_position: List[RoleAssignment]
    state_machine: ConversationStateMachine
    conversation_history: List[Dict] = None
    document_summary: Dict = None
    # Per-unit user-message counter. Drives the auto-nudge to move on after
    # ~3 user turns on the same topic (see AUTO_NUDGE_AFTER_USER_TURNS).
    user_turns_by_unit: Dict[int, int] = None
    # ``study_group`` = fixed pedagogical pool; ``perspective_debate`` = two LLM-authored viewpoints.
    session_mode: str = "study_group"
    # Selected RoleType order for study-group mode (``None`` = all five roles).
    study_pool: Optional[List[RoleType]] = None
    # Two `RoleTemplate` instances; only set for ``perspective_debate``.
    debate_personas: Optional[List[RoleTemplate]] = None

    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.document_summary is None:
            self.document_summary = {}
        if self.user_turns_by_unit is None:
            self.user_turns_by_unit = {}


# --- Session mode + role pool parsing -------------------------------------------------

SESSION_MODE_STUDY = "study_group"
SESSION_MODE_DEBATE = "perspective_debate"

_ROLE_VALUE_MAP: Dict[str, RoleType] = {rt.value: rt for rt in RoleType}


def _parse_study_role_pool(study_role_count: int, role_names: List[str]) -> List[RoleType]:
    if study_role_count not in (2, 5):
        raise ValueError("study_role_count must be 2 or 5")
    if not role_names or len(role_names) != study_role_count:
        raise ValueError(f"Select exactly {study_role_count} roles for this session")
    out: List[RoleType] = []
    for raw in role_names:
        key = (raw or "").strip()
        role = _ROLE_VALUE_MAP.get(key)
        if role is None:
            raise ValueError(
                f"Unknown role: {raw!r}. Use one of: {', '.join(_ROLE_VALUE_MAP)}"
            )
        out.append(role)
    if len(set(out)) != len(out):
        raise ValueError("Each role can only be selected once")
    return out


class ConversationRuntime:
    """In-memory orchestrator for upload -> roles -> conversation flow."""

    # Study-group tunables.
    OPENER_SPEAKERS = 3           # primary + up to 2 chime-ins in a topic opener
    REPLY_CHIME_IN = True         # after primary replies to student, one chime-in speaks
    AUTO_NUDGE_AFTER_USER_TURNS = 3  # soft wrap-up after N user turns on same unit

    def __init__(self):
        self._sessions: Dict[str, ActiveConversation] = {}
        self._processor: Optional[DocumentProcessor] = None
        self._assigner: Optional[RoleAssigner] = None
        self._llm_client: Optional[LLMClient] = None
        self._llm_available = True
        self._llm_fail_count = 0
        self._llm_max_retries = 3
        logger.info("ConversationRuntime initialized")

    def create_session_from_uploaded_file(
        self,
        upload: UploadFile,
        *,
        session_mode: str = SESSION_MODE_STUDY,
        study_role_count: int = 5,
        study_roles: Optional[List[str]] = None,
        debate_hint: str = "",
    ) -> ActiveConversation:
        """Create session from uploaded document and prepare role queue."""
        logger.info("")
        logger.info("=" * 80)
        logger.info("📤 DOCUMENT UPLOAD RECEIVED")
        logger.info(f"   Filename: {upload.filename}")
        logger.info(f"   Size: {len(upload.file.read())} bytes")
        upload.file.seek(0)  # Reset file pointer
        mode = (session_mode or SESSION_MODE_STUDY).strip().lower()
        if mode in ("debate", "perspective", "perspective_debate", "pd"):
            mode = SESSION_MODE_DEBATE
        elif mode in ("study", "study_group", "sg"):
            mode = SESSION_MODE_STUDY
        if mode not in (SESSION_MODE_STUDY, SESSION_MODE_DEBATE):
            raise ValueError("session_mode must be study_group or perspective_debate")
        logger.info(f"   session_mode: {mode}")
        logger.info("=" * 80)
        
        extension = Path(upload.filename or "").suffix.lower()
        if extension not in {".txt", ".pdf"}:
            raise ValueError("Unsupported file type. Use .txt or .pdf")

        session_id = str(uuid4())
        logger.info(f"📋 Generated Session ID: {session_id}")
        temp_path = Path("data") / f"upload_{session_id}{extension}"
        temp_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            logger.info("📖 Reading and processing document...")
            contents = upload.file.read()
            temp_path.write_bytes(contents)
            logger.info(f"   Saved to: {temp_path}")

            processor = self._get_processor()
            assigner = self._get_assigner()

            logger.info("🔍 Segmenting into semantic units...")
            semantic_units = processor.process_document(str(temp_path))
            logger.info(f"✅ Created {len(semantic_units)} semantic units")
            
            for idx, unit in enumerate(semantic_units, start=1):
                preview = " ".join(unit.text.split())[:80]
                logger.info(
                    f"   Unit {idx}: pos={unit.position}, section='{unit.document_section}', "
                    f"words={unit.word_count}, cohesion={unit.similarity_score:.3f}, "
                    f"text='{preview}...'"
                )
            
            document_summary = processor.get_document_summary(semantic_units)
            logger.info("📊 DOCUMENT SUMMARY")
            logger.info(f"   Total Units: {document_summary.get('total_units', 0)}")
            logger.info(f"   Total Words: {document_summary.get('total_words', 0)}")
            logger.info(f"   Avg Words/Unit: {document_summary.get('avg_words_per_unit', 0):.1f}")
            logger.info(f"   Avg Cohesion: {document_summary.get('avg_cohesion', 0):.3f}")

            study_pool: Optional[List[RoleType]] = None
            debate_personas: Optional[List[RoleTemplate]] = None
            sorted_assignments: List[RoleAssignment] = []

            if mode == SESSION_MODE_DEBATE:
                logger.info("🎭 PERSPECTIVE-DEBATE MODE: synthesizing two viewpoint personas...")
                joined_excerpt = "\n\n".join(u.text for u in semantic_units[:12])
                hint = (debate_hint or "").strip()
                personas: List[RoleTemplate] = self._synthesize_debate_personas(
                    document_excerpt=joined_excerpt, user_hint=hint
                )
                debate_personas = personas
                dummy_score = RoleScore(
                    role_type=RoleType.EXPLAINER,
                    total_score=0.5,
                    structural_score=0.5,
                    lexical_score=0.5,
                    topic_score=0.5,
                )
                primary_template = personas[0]
                sorted_assignments = [
                    RoleAssignment(
                        semantic_unit=u,
                        assigned_role=RoleType.EXPLAINER,
                        role_template=primary_template,
                        score=dummy_score,
                        confidence=0.5,
                        chime_in_roles=[RoleType.CHALLENGER],
                    )
                    for u in sorted(semantic_units, key=lambda x: x.position)
                ]
                logger.info(
                    f"✅ Debate personas: {personas[0].name!r} vs {personas[1].name!r} "
                    f"({len(sorted_assignments)} units)"
                )
            else:
                names = study_roles
                if not names:
                    if study_role_count == 5:
                        names = [rt.value for rt in RoleType]
                    else:
                        raise ValueError(
                            "For a 2-role study session, pass study_roles with exactly two role names"
                        )
                study_pool = _parse_study_role_pool(study_role_count, names)
                logger.info(
                    f"🎭 ASSIGNING PEDAGOGICAL ROLES (pool {study_role_count}: "
                    f"{[r.value for r in study_pool]})..."
                )
                assignments = assigner.assign_roles(
                    semantic_units, balance_roles=True, allowed_roles=study_pool
                )
                sorted_assignments = sorted(assignments, key=lambda a: a.semantic_unit.position)
                logger.info(f"✅ Assigned roles to {len(sorted_assignments)} units")
                for idx, assignment in enumerate(sorted_assignments, start=1):
                    preview = " ".join(assignment.semantic_unit.text.split())[:80]
                    logger.info(
                        f"   Unit {idx}: role={assignment.assigned_role.value}, "
                        f"confidence={assignment.confidence:.3f}, "
                        f"scores=[struct:{assignment.score.structural_score:.2f}, "
                        f"lex:{assignment.score.lexical_score:.2f}, "
                        f"topic:{assignment.score.topic_score:.2f}]"
                    )

            sm = ConversationStateMachine(session_id=session_id)
            sm.transition(EventType.INITIALIZE)
            sm.transition(EventType.DOCUMENT_LOADED, {"filename": upload.filename})
            sm.context.total_units = len(sorted_assignments)
            sm.transition(EventType.ROLES_ASSIGNED)
            if sorted_assignments:
                if mode == SESSION_MODE_DEBATE and debate_personas:
                    sm.context.current_role = debate_personas[0].name
                else:
                    sm.context.current_role = sorted_assignments[0].assigned_role.value
            self._log_state(sm, "session_initialized")

            conversation = ActiveConversation(
                session_id=session_id,
                filename=upload.filename or "uploaded_document",
                semantic_units=semantic_units,
                assignments_by_position=sorted_assignments,
                state_machine=sm,
                document_summary=document_summary,
                session_mode=mode,
                study_pool=study_pool,
                debate_personas=debate_personas,
            )
            self._sessions[session_id] = conversation
            logger.info(
                f"Created session {session_id} for {conversation.filename} "
                f"with {len(sorted_assignments)} units (mode={mode})"
            )
            return conversation
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def _synthesize_debate_personas(
        self, document_excerpt: str, user_hint: str
    ) -> List[RoleTemplate]:
        """Ask the LLM for two debate personas; fall back deterministically on failure."""
        client = self._get_llm_client()
        if client is None:
            return build_debate_personas_from_llm("", user_hint)
        try:
            prompt = render_debate_persona_prompt(document_excerpt, user_hint)
            raw = client.generate(
                prompt,
                temperature=0.35,
                max_tokens=min(2000, max(settings.llm_max_tokens, 1200)),
            )
            return build_debate_personas_from_llm(raw, user_hint)
        except Exception as exc:
            logger.warning(f"Debate persona synthesis failed ({exc}); using fallbacks")
            return build_debate_personas_from_llm("", user_hint)

    def get_session(self, session_id: str) -> ActiveConversation:
        """Return existing in-memory session or raise KeyError."""
        if session_id not in self._sessions:
            raise KeyError(f"Session not found: {session_id}")
        return self._sessions[session_id]

    def start_conversation(self, session_id: str) -> Dict:
        """Start the conversation with a multi-role topic opener."""
        session = self.get_session(session_id)
        sm = session.state_machine
        logger.info("")
        logger.info("=" * 80)
        logger.info("🎯 STARTING CONVERSATION (group opener)")
        logger.info(f"   Session: {session_id}")
        logger.info(f"   Document: {session.filename}")
        logger.info(f"   Total Units: {sm.context.total_units}")
        logger.info("=" * 80)
        self._log_state(sm, "before_start_conversation")

        if sm.context.current_state == ConversationState.READY:
            sm.transition(EventType.START_DIALOGUE)
        elif sm.context.current_state != ConversationState.ENGAGED:
            raise ValueError(f"Cannot start conversation from state {sm.context.current_state.value}")

        assignment = self._current_assignment(session)
        if self._is_debate(session) and session.debate_personas:
            speaker_line = ", ".join(p.name for p in session.debate_personas)
        else:
            spk = assignment.speaker_order()[: self.OPENER_SPEAKERS]
            speaker_line = ", ".join(r.value for r in spk)
        logger.info(
            f"🎤 OPENER on Unit 1 of {sm.context.total_units} (speakers: {speaker_line})"
        )

        start_gen = time.perf_counter()
        messages = self._generate_group_opener(session, assignment)
        gen_time = int((time.perf_counter() - start_gen) * 1000)
        logger.info(
            f"✅ OPENER GENERATED ({len(messages)} messages, {gen_time}ms total)"
        )

        last_role = messages[-1]["role"] if messages else (
            session.debate_personas[0].name
            if self._is_debate(session) and session.debate_personas
            else assignment.assigned_role.value
        )
        sm.context.current_role = last_role
        sm.transition(EventType.BOT_RESPONSE, {"type": "start"})
        sm.finish_bot_response()
        self._log_state(sm, "after_start_conversation")
        logger.info("=" * 80)

        return {
            "session_id": session_id,
            "role": last_role,
            "unit_index": sm.context.current_unit_index,
            "total_units": sm.context.total_units,
            "response": messages[-1]["text"] if messages else "",
            "messages": messages,
            "auto_nudge": False,
            "state": sm.get_state_summary(),
        }

    def send_user_message(self, session_id: str, message: str) -> Dict:
        """Handle a user message: primary role replies, then a second role chimes in."""
        session = self.get_session(session_id)
        sm = session.state_machine
        logger.info("")
        logger.info("=" * 80)
        logger.info(f"📥 USER MESSAGE RECEIVED")
        logger.info(f"   Session: {session_id}")
        logger.info(f"   Input: '{message[:100]}...' ({len(message)} chars)")
        logger.info("=" * 80)
        self._log_state(sm, "before_user_message")

        result = sm.process_user_message(message)
        if "error" in result:
            raise ValueError(result["error"])

        assignment = self._current_assignment(session)
        unit_idx = assignment.semantic_unit.position
        session.user_turns_by_unit[unit_idx] = session.user_turns_by_unit.get(unit_idx, 0) + 1
        turns_on_unit = session.user_turns_by_unit[unit_idx]
        logger.info(
            f"📊 Unit {unit_idx} / {sm.context.total_units - 1}, "
            f"user_turns_on_this_unit={turns_on_unit}, "
            f"primary={assignment.assigned_role.value}, "
            f"chime_in_candidates={[r.value for r in assignment.chime_in_roles]}"
        )

        sm.start_bot_response()
        start_gen = time.perf_counter()
        messages = self._generate_group_reply(session, assignment, message)
        gen_time = int((time.perf_counter() - start_gen) * 1000)
        logger.info(
            f"✅ GROUP REPLY GENERATED ({len(messages)} messages, {gen_time}ms total)"
        )

        # Optional soft wrap-up nudge after N user turns on the same unit.
        nudge = self._maybe_wrap_up(session, assignment)
        if nudge is not None:
            messages.append(nudge)

        last_role = messages[-1]["role"] if messages else (
            session.debate_personas[0].name
            if self._is_debate(session) and session.debate_personas
            else assignment.assigned_role.value
        )
        sm.context.current_role = last_role
        sm.transition(EventType.BOT_RESPONSE, {"type": "user_message"})
        sm.finish_bot_response()
        self._log_state(sm, "after_user_message")
        logger.info("=" * 80)

        return {
            "session_id": session_id,
            "role": last_role,
            "unit_index": sm.context.current_unit_index,
            "response": messages[-1]["text"] if messages else "",
            "messages": messages,
            "auto_nudge": nudge is not None,
            "state": sm.get_state_summary(),
        }

    def interrupt(self, session_id: str) -> Dict:
        """Handle interrupt button click."""
        session = self.get_session(session_id)
        logger.info(f"interrupt invoked for session {session_id}")
        self._log_state(session.state_machine, "before_interrupt")
        result = session.state_machine.user_clicks_interrupt()
        result["state"] = session.state_machine.get_state_summary()
        self._log_state(session.state_machine, "after_interrupt")
        return {"session_id": session_id, **result}

    def answer_interruption(self, session_id: str, message: str) -> Dict:
        """Generate answer for an interruption question."""
        session = self.get_session(session_id)
        sm = session.state_machine
        logger.info(
            f"answer_interruption invoked for session {session_id}, chars={len(message)}, "
            f"preview='{message[:120]}'"
        )
        self._log_state(sm, "before_interruption_answer")

        result = sm.process_interruption_message(message)
        if "error" in result:
            raise ValueError(result["error"])

        current_assignment = self._current_assignment(session)
        override_template = None
        if self._is_debate(session) and session.debate_personas:
            override_template = find_best_among_templates(
                session.debate_personas, message, fallback=session.debate_personas[0]
            )
        else:
            override_template = role_library.find_best_role_for_keywords(message)
            pooled = session.study_pool
            if (
                override_template is not None
                and pooled is not None
                and override_template.role_type not in pooled
            ):
                override_template = None
        template = override_template or current_assignment.role_template
        template_name = template.name
        logger.info(
            f"Interruption response role selected: {template_name} "
            f"(override={'yes' if override_template else 'no'})"
        )

        sm.start_bot_response()
        response = self._generate_response(
            template,
            current_assignment.semantic_unit.text,
            user_input=message,
            session=session,
        )
        sm.context.current_role = template.name
        sm.transition(EventType.BOT_RESPONSE, {"type": "interruption"})
        sm.finish_bot_response()
        role_name = template.name
        self._record_exchange(session, message, role_name, response)
        self._log_state(sm, "after_interruption_answer")

        return {
            "session_id": session_id,
            "role": role_name,
            "interrupted_unit": result["interrupted_unit"],
            "response": response,
            "messages": [{"role": role_name, "text": response}],
            "can_resume": True,
            "state": sm.get_state_summary(),
        }

    def resume(self, session_id: str, from_start: bool = False) -> Dict:
        """Resume after interruption.

        * from_start=True  → restart the current topic with a fresh group opener.
        * from_start=False → primary role gives a brief "back to it" re-entry
                             (single message — resuming shouldn't feel like the
                             group started over).
        """
        session = self.get_session(session_id)
        sm = session.state_machine
        logger.info(f"resume invoked for session {session_id}, from_start={from_start}")
        self._log_state(sm, "before_resume")

        if from_start and sm.context.interrupted_at_index is not None:
            sm.context.current_unit_index = sm.context.interrupted_at_index
            # Reset the nudge counter for this unit since we're restarting it.
            session.user_turns_by_unit.pop(sm.context.interrupted_at_index, None)
            logger.info(
                f"Resume from start; reset unit index to {sm.context.interrupted_at_index}"
            )

        result = sm.resume_conversation()
        if not result.get("success", False):
            result["state"] = sm.get_state_summary()
            result["session_id"] = session_id
            self._log_state(sm, "resume_failed")
            return result

        assignment = self._current_assignment(session)
        sm.start_bot_response()

        if from_start:
            messages = self._generate_group_opener(session, assignment)
        else:
            response = self._generate_response(
                assignment.role_template, assignment.semantic_unit.text, session=session
            )
            self._record_exchange(session, None, assignment.assigned_role.value, response)
            messages = [{"role": assignment.role_template.name, "text": response}]

        last_role = messages[-1]["role"] if messages else assignment.assigned_role.value
        sm.context.current_role = last_role
        sm.transition(EventType.BOT_RESPONSE, {"type": "resume"})
        sm.finish_bot_response()
        self._log_state(sm, "after_resume")

        return {
            "session_id": session_id,
            "success": True,
            "message": (
                "Restarted current topic from the beginning."
                if from_start
                else "Resumed from where we left off."
            ),
            "resuming_from_unit": sm.context.current_unit_index,
            "unit_index": sm.context.current_unit_index,
            "role": last_role,
            "response": messages[-1]["text"] if messages else "",
            "messages": messages,
            "state": sm.get_state_summary(),
        }

    def advance_to_next_unit(self, session_id: str) -> Dict:
        """Advance to next unit and launch a fresh multi-role opener for it."""
        session = self.get_session(session_id)
        sm = session.state_machine
        logger.info(f"advance_to_next_unit invoked for session {session_id}")
        self._log_state(sm, "before_advance")
        result = sm.advance_unit()

        payload = {
            "session_id": session_id,
            "success": result.get("success", False),
            "completed": result.get("completed", False),
            "unit_index": sm.context.current_unit_index,
            "total_units": sm.context.total_units,
            "state": sm.get_state_summary(),
            "response": None,
            "role": None,
            "messages": [],
            "auto_nudge": False,
        }

        if not payload["success"] or payload["completed"]:
            if payload["completed"]:
                logger.info(f"Session {session_id} completed all units")
            self._log_state(sm, "after_advance_no_response")
            return payload

        assignment = self._current_assignment(session)
        # Fresh topic — reset any stale nudge counter for this unit.
        session.user_turns_by_unit.pop(assignment.semantic_unit.position, None)
        if self._is_debate(session) and session.debate_personas:
            spk = [p.name for p in session.debate_personas]
        else:
            spk = [r.value for r in assignment.speaker_order()[: self.OPENER_SPEAKERS]]
        logger.info(
            f"Advanced to unit={assignment.semantic_unit.id} "
            f"(index={sm.context.current_unit_index}) with speakers={spk}"
        )
        sm.start_bot_response()
        messages = self._generate_group_opener(session, assignment)
        last_role = messages[-1]["role"] if messages else (
            session.debate_personas[0].name
            if self._is_debate(session) and session.debate_personas
            else assignment.assigned_role.value
        )
        sm.context.current_role = last_role
        sm.transition(EventType.BOT_RESPONSE, {"type": "next_unit"})
        sm.finish_bot_response()
        self._log_state(sm, "after_advance")

        payload["response"] = messages[-1]["text"] if messages else ""
        payload["role"] = last_role
        payload["messages"] = messages
        payload["state"] = sm.get_state_summary()
        return payload

    def get_session_state(self, session_id: str) -> Dict:
        """Return session metadata and frontend-ready state."""
        session = self.get_session(session_id)
        sm = session.state_machine
        current_role = sm.context.current_role
        self._log_state(sm, "get_session_state")

        study_sel = [r.value for r in session.study_pool] if session.study_pool else None
        debate = (
            [{"name": p.name} for p in session.debate_personas]
            if session.debate_personas
            else None
        )
        return {
            "session_id": session_id,
            "filename": session.filename,
            "total_units": sm.context.total_units,
            "current_unit_index": sm.context.current_unit_index,
            "current_role": current_role,
            "session_mode": session.session_mode,
            "selected_roles": study_sel,
            "debate_personas": debate,
            "state": sm.get_state_summary(),
        }

    def _get_processor(self) -> DocumentProcessor:
        """Lazily initialize document processor (loads embedding model)."""
        if self._processor is None:
            self._processor = DocumentProcessor()
        return self._processor

    def _get_assigner(self) -> RoleAssigner:
        """Lazily initialize role assigner."""
        if self._assigner is None:
            self._assigner = RoleAssigner()
        return self._assigner

    def _current_assignment(self, session: ActiveConversation) -> RoleAssignment:
        """Get assignment for current index, clamped to valid range."""
        if not session.assignments_by_position:
            raise ValueError("No semantic units available for conversation")

        index = min(
            session.state_machine.context.current_unit_index,
            len(session.assignments_by_position) - 1,
        )
        return session.assignments_by_position[index]

    def _build_history_context(self, session: ActiveConversation, max_turns: int = 5) -> str:
        """Build recent conversation history string for LLM context."""
        if not session.conversation_history:
            return ""
        recent = session.conversation_history[-max_turns:]
        lines = []
        for entry in recent:
            if entry["role"] == "user":
                lines.append(f"Student: {entry['text']}")
            else:
                lines.append(f"{entry['role']}: {entry['text'][:300]}")
        return "\n".join(lines)

    def _record_exchange(
        self, session: ActiveConversation, user_msg: Optional[str], bot_role: str, bot_msg: str
    ):
        """Append an exchange to session conversation history."""
        if user_msg:
            session.conversation_history.append({"role": "user", "text": user_msg})
        session.conversation_history.append({"role": bot_role, "text": bot_msg})
        logger.info(
            f"Recorded exchange: history_length={len(session.conversation_history)}, "
            f"last_bot_role={bot_role}, last_bot_chars={len(bot_msg)}"
        )

    def _log_state(self, sm: ConversationStateMachine, stage: str):
        """Log compact, consistent state snapshots for terminal observability."""
        summary = sm.get_state_summary()
        progress = summary.get("progress", {})
        logger.info(
            f"State[{stage}]: state={summary.get('current_state')}, role={summary.get('current_role')}, "
            f"unit={progress.get('current_unit')}/{progress.get('total_units')}, "
            f"bot_generating={summary.get('bot_status', {}).get('is_generating')}, "
            f"awaiting_input={summary.get('bot_status', {}).get('awaiting_input')}, "
            f"interruptions={summary.get('interruptions')}, messages={summary.get('messages')}"
        )

    # Cap on response length. We want actual teaching turns (multiple
    # sentences of explanation, not one-liners), so this is sized for a real
    # mini-lesson paragraph rather than a chat one-liner.
    MAX_RESPONSE_CHARS = 1400

    # ──────────────────────────────────────────────────────────────────────
    # Group conversation generators
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _is_debate(session: ActiveConversation) -> bool:
        return session.session_mode == SESSION_MODE_DEBATE and bool(session.debate_personas)

    def _generate_group_opener(
        self,
        session: ActiveConversation,
        assignment: RoleAssignment,
    ) -> List[Dict[str, str]]:
        """Produce a topic-opening multi-role exchange.

        Returns a list of at most OPENER_SPEAKERS messages, each shaped as
        ``{"role": <RoleType.value>, "text": <str>}``. The first speaker is
        the unit's primary role; the rest are the pre-computed chime-ins.
        """
        if self._is_debate(session) and session.debate_personas:
            return self._generate_debate_group_opener(session, assignment)

        speakers = assignment.speaker_order()[: self.OPENER_SPEAKERS]
        other_names_full = [role_library.get_role(r).name for r in speakers]
        messages: List[Dict[str, str]] = []
        last_idx = len(speakers) - 1

        for idx, role_type in enumerate(speakers):
            template = role_library.get_role(role_type)
            other_names = [n for n in other_names_full if n != template.name]
            # The LAST voice in the opener hands the mic to the student with a
            # direct question — otherwise the group just trails off and the
            # student is left guessing whose turn it is.
            if idx == 0:
                style = "open"
            elif idx == last_idx:
                style = "chime_closer"
            else:
                style = "chime"
            text = self._generate_response_with_style(
                template,
                assignment.semantic_unit.text,
                session=session,
                reply_style=style,
                group_transcript=list(messages),
                other_role_names=other_names,
            )
            messages.append({"role": template.name, "text": text})
            self._record_exchange(session, None, template.name, text)

        return messages

    def _generate_debate_group_opener(
        self,
        session: ActiveConversation,
        assignment: RoleAssignment,
    ) -> List[Dict[str, str]]:
        """Two-voice topic opener for perspective-debate mode."""
        personas = session.debate_personas or []
        if len(personas) < 2:
            return []
        other_names_full = [p.name for p in personas]
        messages: List[Dict[str, str]] = []
        last_idx = len(personas) - 1
        for idx, template in enumerate(personas):
            other_names = [n for n in other_names_full if n != template.name]
            if idx == 0:
                style = "open"
            elif idx == last_idx:
                style = "chime_closer"
            else:
                style = "chime"
            text = self._generate_response_with_style(
                template,
                assignment.semantic_unit.text,
                session=session,
                reply_style=style,
                group_transcript=list(messages),
                other_role_names=other_names,
            )
            messages.append({"role": template.name, "text": text})
            self._record_exchange(session, None, template.name, text)
        return messages

    def _generate_debate_group_reply(
        self,
        session: ActiveConversation,
        assignment: RoleAssignment,
        user_message: str,
    ) -> List[Dict[str, str]]:
        """Two-voice reply: best keyword match, then the other debater chimes in."""
        personas = session.debate_personas or []
        if len(personas) < 2:
            return []
        primary_template = find_best_among_templates(
            personas, user_message, fallback=personas[0]
        )
        chime_template = next(
            (p for p in personas if p.name != primary_template.name), personas[1]
        )
        other_names_for_primary = [p.name for p in personas if p.name != primary_template.name]
        messages: List[Dict[str, str]] = []
        primary_text = self._generate_response_with_style(
            primary_template,
            assignment.semantic_unit.text,
            user_input=user_message,
            session=session,
            reply_style="reply",
            other_role_names=other_names_for_primary,
        )
        messages.append({"role": primary_template.name, "text": primary_text})
        self._record_exchange(session, user_message, primary_template.name, primary_text)
        if self.REPLY_CHIME_IN:
            other_names_for_chime = [p.name for p in personas if p.name != chime_template.name]
            chime_text = self._generate_response_with_style(
                chime_template,
                assignment.semantic_unit.text,
                user_input=user_message,
                session=session,
                reply_style="reply_chime",
                group_transcript=list(messages),
                other_role_names=other_names_for_chime,
            )
            messages.append({"role": chime_template.name, "text": chime_text})
            self._record_exchange(session, None, chime_template.name, chime_text)
        return messages

    def _generate_group_reply(
        self,
        session: ActiveConversation,
        assignment: RoleAssignment,
        user_message: str,
    ) -> List[Dict[str, str]]:
        """Produce a primary reply + (optional) chime-in to the student."""
        if self._is_debate(session) and session.debate_personas:
            return self._generate_debate_group_reply(session, assignment, user_message)

        speakers = assignment.speaker_order()
        if not speakers:
            return []

        # Pick primary replier: keyword-route first, fall back to unit owner.
        routed = role_library.find_best_role_for_keywords(user_message)
        pooled = session.study_pool
        if (
            routed is not None
            and pooled is not None
            and routed.role_type not in pooled
        ):
            routed = None
        primary_role = (
            routed.role_type
            if routed is not None and routed.role_type in speakers
            else assignment.assigned_role
        )
        primary_template = role_library.get_role(primary_role)

        # Chime-in: first speaker in the unit's order that isn't the primary.
        chime_role = next((r for r in speakers if r != primary_role), None)

        other_names_for_primary = [
            role_library.get_role(r).name for r in speakers if r != primary_role
        ]
        logger.info(
            f"Group reply: primary={primary_template.name}, "
            f"chime_in={(role_library.get_role(chime_role).name if chime_role else 'none')}, "
            f"routed={'yes' if routed is not None else 'no'}"
        )

        messages: List[Dict[str, str]] = []

        primary_text = self._generate_response_with_style(
            primary_template,
            assignment.semantic_unit.text,
            user_input=user_message,
            session=session,
            reply_style="reply",
            other_role_names=other_names_for_primary,
        )
        messages.append({"role": primary_template.name, "text": primary_text})
        self._record_exchange(session, user_message, primary_template.name, primary_text)

        if self.REPLY_CHIME_IN and chime_role is not None:
            chime_template = role_library.get_role(chime_role)
            other_names_for_chime = [
                role_library.get_role(r).name for r in speakers if r != chime_role
            ]
            chime_text = self._generate_response_with_style(
                chime_template,
                assignment.semantic_unit.text,
                user_input=user_message,
                session=session,
                reply_style="reply_chime",
                group_transcript=list(messages),
                other_role_names=other_names_for_chime,
            )
            messages.append({"role": chime_template.name, "text": chime_text})
            # record WITHOUT user_input (already recorded once on primary)
            self._record_exchange(session, None, chime_template.name, chime_text)

        return messages

    def _maybe_wrap_up(
        self,
        session: ActiveConversation,
        assignment: RoleAssignment,
    ) -> Optional[Dict[str, str]]:
        """Return a soft wrap-up line if this unit has hit the nudge threshold.

        The wrap-up voice is the unit's primary role (keeps attribution stable).
        """
        unit_idx = assignment.semantic_unit.position
        turns = session.user_turns_by_unit.get(unit_idx, 0)
        if turns < self.AUTO_NUDGE_AFTER_USER_TURNS:
            return None
        # Only nudge ONCE per unit — bump the counter past threshold.
        session.user_turns_by_unit[unit_idx] = turns + 1000
        if self._is_debate(session) and session.debate_personas:
            template = session.debate_personas[0]
        else:
            template = role_library.get_role(assignment.assigned_role)
        text = self._generate_response_with_style(
            template,
            assignment.semantic_unit.text,
            session=session,
            reply_style="wrap",
        )
        self._record_exchange(session, None, template.name, text)
        return {"role": template.name, "text": text, "is_nudge": True}

    def _generate_response_with_style(
        self,
        template: RoleTemplate,
        context: str,
        user_input: Optional[str] = None,
        session: Optional[ActiveConversation] = None,
        *,
        reply_style: str = "auto",
        group_transcript: Optional[List[Dict[str, str]]] = None,
        other_role_names: Optional[List[str]] = None,
    ) -> str:
        """Generate one role's turn.

        Uses the reply-style aware prompt so the same code path supports topic
        openers, chime-ins, primary replies, reply chime-ins, and wrap-up nudges.
        """
        short_context = context[:1200]
        last_period = short_context.rfind(".")
        if last_period > 700:
            short_context = short_context[: last_period + 1]

        history = self._build_history_context(session) if session else ""
        prompt = template.build_prompt(
            short_context,
            user_input=user_input,
            history=history,
            reply_style=reply_style,
            group_transcript=group_transcript,
            other_role_names=other_role_names,
        )

        client = self._get_llm_client()
        if client is None:
            logger.warning(f"LLM unavailable; using fallback response for role {template.name}")
            return self._postprocess_response(
                self._fallback_response(template, short_context, user_input=user_input),
                template=template,
                other_role_names=other_role_names,
            )

        try:
            start_time = time.perf_counter()
            logger.info(
                f"Generating {template.name} response "
                f"(style={reply_style}, prompt_chars={len(prompt)}, "
                f"ctx_chars={len(short_context)}, has_user_input={bool(user_input)}, "
                f"group_turns={len(group_transcript) if group_transcript else 0}, "
                f"history_turns={len(session.conversation_history) if session else 0})"
            )
            raw = client.generate(
                prompt,
                temperature=template.temperature,
                max_tokens=template.max_tokens,
            ).strip()
            result = self._postprocess_response(
                raw, template=template, other_role_names=other_role_names
            )

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(
                f"Generated {template.name} response "
                f"(raw_chars={len(raw)}, final_chars={len(result)}, latency_ms={elapsed_ms})"
            )
            self._llm_fail_count = 0  # reset on success
            return result
        except Exception as exc:
            self._llm_fail_count += 1
            logger.warning(
                f"LLM generation failed ({self._llm_fail_count}/{self._llm_max_retries}): {exc}"
            )
            if self._llm_fail_count >= self._llm_max_retries:
                self._llm_available = False
                logger.error("LLM disabled after repeated failures. Restart server to retry.")
            return self._postprocess_response(
                self._fallback_response(template, short_context, user_input=user_input),
                template=template,
                other_role_names=other_role_names,
            )

    def _generate_response(
        self,
        template: RoleTemplate,
        context: str,
        user_input: Optional[str] = None,
        session: Optional[ActiveConversation] = None,
    ) -> str:
        """Single-turn generator used by interruption and resume paths.

        For debate sessions we pass the other persona name as other_role_names so
        the hallucination-cut regex catches it.
        """
        other_role_names: Optional[List[str]] = None
        if session is not None and self._is_debate(session) and session.debate_personas:
            other_role_names = [
                p.name for p in session.debate_personas if p.name != template.name
            ]
        return self._generate_response_with_style(
            template,
            context,
            user_input=user_input,
            session=session,
            reply_style="auto",
            other_role_names=other_role_names,
        )

    # Roles the LLM might hallucinate a turn for after its own. We cut the
    # response at the first such marker to kill the "writes both sides of the
    # dialogue" problem that small models exhibit.
    # Debate persona names are added dynamically per-session in _postprocess_response.
    _HALLUCINATED_SPEAKERS = (
        "Student",
        "User",
        "You",
        "Teacher",
        "Tutor",
        "Explainer",
        "Challenger",
        "Summarizer",
        "Example-Generator",
        "Misconception-Spotter",
    )

    def _postprocess_response(
        self,
        text: str,
        *,
        template: Optional[RoleTemplate] = None,
        other_role_names: Optional[List[str]] = None,
    ) -> str:
        """Strip markdown artifacts, cut hallucinated next-speaker lines,
        enforce a conversational length budget.

        The LLM frequently ignores "no markdown" instructions and emits headings,
        bullet lists, and bold markers. Small models also tend to "complete the
        script" by writing another speaker's turn after their own
        (``\\n\\nStudent: …``). We scrub both.
        """
        if not text:
            return text

        cleaned = text.strip()

        # 1. Strip a leading "RoleName:" prefix the model sometimes emits even
        #    though the prompt already ends with that marker.
        leading_name = template.name if template is not None else None
        if leading_name:
            cleaned = re.sub(
                rf"^\s*{re.escape(leading_name)}\s*:\s*",
                "",
                cleaned,
                count=1,
                flags=re.IGNORECASE,
            )

        # 2. Cut at the first hallucinated next-speaker marker. This is the most
        #    impactful fix for the "writes both sides" bug we saw on llama3.2:1b.
        speaker_names = set(self._HALLUCINATED_SPEAKERS)
        if other_role_names:
            speaker_names.update(other_role_names)
        if leading_name:
            speaker_names.discard(leading_name)  # our own name is fine leading
        pattern = r"\n\s*(?:" + "|".join(re.escape(n) for n in speaker_names) + r")\s*:"
        match = re.search(pattern, cleaned)
        if match:
            cleaned = cleaned[: match.start()].rstrip()

        # 3. Markdown scrubbing (unchanged behaviour).
        cleaned = re.sub(r"```.*?```", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
        cleaned = re.sub(r"^\s{0,3}#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", cleaned)
        cleaned = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", cleaned)
        cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
        cleaned = re.sub(r"^\s*[-*•]\s+", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = cleaned.strip()

        # 4. Hard length clamp on a sentence boundary.
        if len(cleaned) > self.MAX_RESPONSE_CHARS:
            window = cleaned[: self.MAX_RESPONSE_CHARS]
            cut = max(window.rfind("."), window.rfind("!"), window.rfind("?"))
            if cut >= int(self.MAX_RESPONSE_CHARS * 0.5):
                cleaned = window[: cut + 1].rstrip()
            else:
                space = window.rfind(" ")
                cleaned = (window[:space] if space > 0 else window).rstrip() + "…"
            logger.info(f"Response clamped to {len(cleaned)} chars for conversational flow")

        return cleaned

    def _get_llm_client(self) -> Optional[LLMClient]:
        """Lazily initialize LLM client to keep startup resilient."""
        if not self._llm_available:
            return None
        if self._llm_client is not None:
            return self._llm_client

        try:
            self._llm_client = LLMClient()
            return self._llm_client
        except Exception as exc:
            logger.warning(f"LLM client unavailable. Falling back to deterministic mode: {exc}")
            self._llm_available = False
            return None

    def _fallback_response(
        self,
        template: RoleTemplate,
        context: str,
        user_input: Optional[str] = None,
    ) -> str:
        """Deterministic fallback used when the LLM is unavailable."""
        paragraphs = [p.strip() for p in context.split("\n\n") if len(p.strip()) > 40]
        if not paragraphs:
            paragraphs = [s.strip() for s in context.split("\n") if len(s.strip()) > 30]
        key_sentences = []
        for p in paragraphs[:5]:
            dot = p.find(".")
            if dot > 15:
                key_sentences.append(p[: dot + 1])

        # Debate personas: route to the debate fallback
        if template.is_debate:
            return self._fallback_debate(template, context, paragraphs, key_sentences, user_input)

        role = template.name
        if role == "Explainer":
            return self._fallback_explainer(context, paragraphs, key_sentences, user_input)
        elif role == "Challenger":
            return self._fallback_challenger(context, paragraphs, key_sentences, user_input)
        elif role == "Summarizer":
            return self._fallback_summarizer(context, paragraphs, key_sentences, user_input)
        elif role == "Example-Generator":
            return self._fallback_example_gen(context, paragraphs, key_sentences, user_input)
        elif role == "Misconception-Spotter":
            return self._fallback_misconception(context, paragraphs, key_sentences, user_input)
        preview = paragraphs[0][:400] if paragraphs else context[:400]
        return f"Let's explore this section: {preview} Feel free to ask about any part of this."

    # ── Role-specific fallback generators ──────────────────────────────────────

    def _fallback_debate(self, template: RoleTemplate, context, paragraphs, key_sentences, user_input) -> str:
        """Persona-aware fallback for debate mode (used when LLM is offline)."""
        meta = template.metadata or {}
        viewpoint = meta.get("viewpoint_label") or template.name
        debate_index = meta.get("debate_index", 0)
        topic = key_sentences[0] if key_sentences else (paragraphs[0][:200] if paragraphs else context[:200])

        if user_input:
            if debate_index == 0:
                resp = (
                    f"From my standpoint as {template.name} — {viewpoint} — "
                    f"your question touches on something important. {topic} "
                    "The material supports this reading when you consider the context and actors described. "
                    "What aspect of my interpretation do you find most or least convincing?"
                )
            else:
                resp = (
                    f"I'd push back on that from my position as {template.name}. {topic} "
                    "The same passage can be read very differently depending on whose interests you centre. "
                    "Does the text give you enough evidence to favour one interpretation over the other?"
                )
        else:
            if debate_index == 0:
                resp = (
                    f"As {template.name} — representing {viewpoint} — I read this section as follows. "
                    f"{topic} "
                    "The evidence here, taken at face value, strongly supports the position I represent. "
                    "I welcome the other perspective, but I think the text is clear on this point."
                )
            else:
                resp = (
                    f"From where I stand as {template.name} — {viewpoint} — this section "
                    "tells a very different story. "
                    f"{topic} "
                    "The framing my counterpart offers ignores critical tensions in the material. "
                    "Which reading do you think the evidence better supports?"
                )
        return resp

    def _fallback_explainer(self, context, paragraphs, key_sentences, user_input):
        intro = key_sentences[0] if key_sentences else paragraphs[0][:200] if paragraphs else context[:200]
        body_parts = []
        for i, sent in enumerate(key_sentences[1:4], 1):
            body_parts.append(f"  {i}. {sent}")
        body = "\n".join(body_parts) if body_parts else ""

        if user_input:
            resp = f"Great question! Let me break this down for you.\n\n{intro}\n\n"
            if body:
                resp += f"Here are the key concepts to understand:\n{body}\n\n"
            remaining = [p for p in paragraphs if user_input.lower().split()[0] in p.lower()] if user_input else []
            if remaining:
                resp += f"Specifically regarding your question: {remaining[0][:300]}\n\n"
            resp += "Would you like me to elaborate on any of these points, or shall we move to the next topic?"
        else:
            resp = f"Let me walk you through this section step by step.\n\n{intro}\n\n"
            if body:
                resp += f"The key ideas we'll cover here are:\n{body}\n\n"
            resp += "What aspect would you like me to explain in more detail?"
        return resp

    def _fallback_challenger(self, context, paragraphs, key_sentences, user_input):
        topic = key_sentences[0] if key_sentences else context[:150]
        questions = []
        if "not" in context.lower() or "however" in context.lower():
            questions.append("What are the limitations of this approach, and when might it fail?")
        if "used" in context.lower() or "application" in context.lower():
            questions.append("Can you think of scenarios where an alternative method would be more appropriate?")
        questions.append("What assumptions does this concept rely on, and are they always valid?")
        questions.append("How would you explain this to someone who disagrees with this approach?")

        if user_input:
            resp = f"Interesting perspective! Let me push your thinking further.\n\n"
            resp += f"You mentioned: \"{user_input}\"\n\n"
            resp += f"Consider this — {topic}\n\n"
            resp += f"Now, here's what I want you to think about:\n"
            for q in questions[:2]:
                resp += f"  • {q}\n"
            resp += "\nTake a moment to reason through these questions. What's your take?"
        else:
            resp = f"Let's think critically about this material.\n\n{topic}\n\n"
            resp += "Before we accept this at face value, consider:\n"
            for q in questions[:3]:
                resp += f"  • {q}\n"
            resp += "\nI'd love to hear your critical analysis. What stands out to you?"
        return resp

    def _fallback_summarizer(self, context, paragraphs, key_sentences, user_input):
        if user_input:
            resp = "Let me distill the key takeaways for you.\n\n"
        else:
            resp = "Here's a structured summary of this section.\n\n"

        resp += "📌 **Key Points:**\n"
        for i, sent in enumerate(key_sentences[:5], 1):
            resp += f"  {i}. {sent}\n"
        if not key_sentences:
            for i, p in enumerate(paragraphs[:3], 1):
                resp += f"  {i}. {p[:120]}...\n"

        # Extract any terms that look like definitions (sentences with "is" or "are")
        defs = [s for s in key_sentences if " is " in s or " are " in s]
        if defs:
            resp += "\n📖 **Core Definitions:**\n"
            for d in defs[:2]:
                resp += f"  → {d}\n"

        resp += "\nWould you like to dive deeper into any of these points, or move on to the next section?"
        return resp

    def _fallback_example_gen(self, context, paragraphs, key_sentences, user_input):
        topic_sentence = key_sentences[0] if key_sentences else context[:200]

        if user_input:
            resp = f"Let me give you some concrete examples to illustrate this.\n\n"
            resp += f"Based on the concept: {topic_sentence}\n\n"
        else:
            resp = f"Let's make this concrete with some real-world examples.\n\n"
            resp += f"The core idea: {topic_sentence}\n\n"

        resp += "🔹 **Example 1 (Everyday Analogy):**\n"
        resp += f"Think of this like a recipe — each component described here plays a specific role, "
        resp += f"just as each ingredient contributes to the final dish. The key concept here works similarly: "
        resp += f"individual parts combine to produce the overall behavior described in the material.\n\n"

        resp += "🔹 **Example 2 (Practical Application):**\n"
        if len(paragraphs) > 1:
            resp += f"In practice, {paragraphs[1][:200]}\n\n"
        else:
            resp += f"In a real-world setting, this concept is applied when systems need to {topic_sentence.lower()[:100]}.\n\n"

        resp += "Can you think of another example from your own experience? That's often the best way to solidify understanding!"
        return resp

    def _fallback_misconception(self, context, paragraphs, key_sentences, user_input):
        topic = key_sentences[0] if key_sentences else context[:200]

        if user_input:
            resp = f"Let me address potential misunderstandings related to your question.\n\n"
        else:
            resp = f"Let's clear up some common misconceptions about this topic.\n\n"

        resp += f"Based on: {topic}\n\n"

        resp += "⚠️ **Common Misconception #1:**\n"
        resp += "Many learners assume this concept is simpler than it actually is. "
        resp += "The key nuance is that the relationships described here are not always straightforward — "
        resp += "context and conditions matter significantly.\n\n"

        resp += "⚠️ **Common Misconception #2:**\n"
        if len(key_sentences) > 1:
            resp += f"Another frequent error is confusing this with related but distinct ideas. "
            resp += f"Note carefully: {key_sentences[1]}\n\n"
        else:
            resp += "Students sometimes overgeneralize from a single example. "
            resp += "Remember that what works in one context may not apply universally.\n\n"

        resp += "✅ **The Correct Understanding:**\n"
        resp += f"{topic}\n\n"
        resp += "Does this help clarify things? Feel free to ask about any point that still seems confusing."
        return resp
