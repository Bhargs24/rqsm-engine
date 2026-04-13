"""In-memory runtime for single-document conversational sessions."""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import UploadFile
from loguru import logger

from app.document.processor import DocumentProcessor
from app.document.segmenter import SemanticUnit
from app.llm.client import LLMClient
from app.roles.role_assignment import RoleAssignment, RoleAssigner
from app.roles.role_templates import RoleTemplate, role_library
from app.state_machine.conversation_state import ConversationState, ConversationStateMachine, EventType


@dataclass
class ActiveConversation:
    """Runtime object for one active in-memory session."""

    session_id: str
    filename: str
    semantic_units: List[SemanticUnit]
    assignments_by_position: List[RoleAssignment]
    state_machine: ConversationStateMachine


class ConversationRuntime:
    """In-memory orchestrator for upload -> roles -> conversation flow."""

    def __init__(self):
        self._sessions: Dict[str, ActiveConversation] = {}
        self._processor: Optional[DocumentProcessor] = None
        self._assigner: Optional[RoleAssigner] = None
        self._llm_client: Optional[LLMClient] = None
        self._llm_available = True
        logger.info("ConversationRuntime initialized")

    def create_session_from_uploaded_file(self, upload: UploadFile) -> ActiveConversation:
        """Create session from uploaded document and prepare role queue."""
        extension = Path(upload.filename or "").suffix.lower()
        if extension not in {".txt", ".pdf"}:
            raise ValueError("Unsupported file type. Use .txt or .pdf")

        session_id = str(uuid4())
        temp_path = Path("data") / f"upload_{session_id}{extension}"
        temp_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            contents = upload.file.read()
            temp_path.write_bytes(contents)

            processor = self._get_processor()
            assigner = self._get_assigner()

            semantic_units = processor.process_document(str(temp_path))
            assignments = assigner.assign_roles(semantic_units, balance_roles=True)
            sorted_assignments = sorted(assignments, key=lambda a: a.semantic_unit.position)

            sm = ConversationStateMachine(session_id=session_id)
            sm.transition(EventType.INITIALIZE)
            sm.transition(EventType.DOCUMENT_LOADED, {"filename": upload.filename})
            sm.context.total_units = len(sorted_assignments)
            sm.transition(EventType.ROLES_ASSIGNED)
            if sorted_assignments:
                sm.context.current_role = sorted_assignments[0].assigned_role.value

            conversation = ActiveConversation(
                session_id=session_id,
                filename=upload.filename or "uploaded_document",
                semantic_units=semantic_units,
                assignments_by_position=sorted_assignments,
                state_machine=sm,
            )
            self._sessions[session_id] = conversation
            logger.info(
                f"Created session {session_id} for {conversation.filename} "
                f"with {len(sorted_assignments)} units"
            )
            return conversation
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def get_session(self, session_id: str) -> ActiveConversation:
        """Return existing in-memory session or raise KeyError."""
        if session_id not in self._sessions:
            raise KeyError(f"Session not found: {session_id}")
        return self._sessions[session_id]

    def start_conversation(self, session_id: str) -> Dict:
        """Start conversation and generate first role response."""
        session = self.get_session(session_id)
        sm = session.state_machine

        if sm.context.current_state == ConversationState.READY:
            sm.transition(EventType.START_DIALOGUE)
        elif sm.context.current_state != ConversationState.ENGAGED:
            raise ValueError(f"Cannot start conversation from state {sm.context.current_state.value}")

        assignment = self._current_assignment(session)
        response = self._generate_response(assignment.role_template, assignment.semantic_unit.text)
        sm.context.current_role = assignment.assigned_role.value
        sm.transition(EventType.BOT_RESPONSE, {"type": "start"})
        sm.finish_bot_response()

        return {
            "session_id": session_id,
            "role": assignment.assigned_role.value,
            "unit_index": sm.context.current_unit_index,
            "total_units": sm.context.total_units,
            "response": response,
            "state": sm.get_state_summary(),
        }

    def send_user_message(self, session_id: str, message: str) -> Dict:
        """Handle a normal user message while engaged."""
        session = self.get_session(session_id)
        sm = session.state_machine

        result = sm.process_user_message(message)
        if "error" in result:
            raise ValueError(result["error"])

        assignment = self._current_assignment(session)
        sm.start_bot_response()
        response = self._generate_response(
            assignment.role_template,
            assignment.semantic_unit.text,
            user_input=message,
        )
        sm.context.current_role = assignment.assigned_role.value
        sm.transition(EventType.BOT_RESPONSE, {"type": "user_message"})
        sm.finish_bot_response()

        return {
            "session_id": session_id,
            "role": assignment.assigned_role.value,
            "unit_index": sm.context.current_unit_index,
            "response": response,
            "state": sm.get_state_summary(),
        }

    def interrupt(self, session_id: str) -> Dict:
        """Handle interrupt button click."""
        session = self.get_session(session_id)
        result = session.state_machine.user_clicks_interrupt()
        result["state"] = session.state_machine.get_state_summary()
        return {"session_id": session_id, **result}

    def answer_interruption(self, session_id: str, message: str) -> Dict:
        """Generate answer for an interruption question."""
        session = self.get_session(session_id)
        sm = session.state_machine

        result = sm.process_interruption_message(message)
        if "error" in result:
            raise ValueError(result["error"])

        current_assignment = self._current_assignment(session)
        override_template = role_library.find_best_role_for_keywords(message)
        template = override_template or current_assignment.role_template

        sm.start_bot_response()
        response = self._generate_response(
            template,
            current_assignment.semantic_unit.text,
            user_input=message,
        )
        sm.context.current_role = template.name
        sm.transition(EventType.BOT_RESPONSE, {"type": "interruption"})
        sm.finish_bot_response()

        return {
            "session_id": session_id,
            "role": template.name,
            "interrupted_unit": result["interrupted_unit"],
            "response": response,
            "can_resume": True,
            "state": sm.get_state_summary(),
        }

    def resume(self, session_id: str, from_start: bool = False) -> Dict:
        """Resume after interruption, with optional restart of current unit."""
        session = self.get_session(session_id)
        sm = session.state_machine

        if from_start and sm.context.interrupted_at_index is not None:
            sm.context.current_unit_index = sm.context.interrupted_at_index

        result = sm.resume_conversation()
        if not result.get("success", False):
            result["state"] = sm.get_state_summary()
            result["session_id"] = session_id
            return result

        assignment = self._current_assignment(session)
        sm.start_bot_response()
        response = self._generate_response(assignment.role_template, assignment.semantic_unit.text)
        sm.context.current_role = assignment.assigned_role.value
        sm.transition(EventType.BOT_RESPONSE, {"type": "resume"})
        sm.finish_bot_response()

        result["message"] = (
            "Restarted current topic from the beginning."
            if from_start
            else "Resumed from where we left off."
        )
        result["unit_index"] = sm.context.current_unit_index
        result["role"] = assignment.assigned_role.value
        result["response"] = response
        result["state"] = sm.get_state_summary()
        result["session_id"] = session_id
        return result

    def advance_to_next_unit(self, session_id: str) -> Dict:
        """Advance to next unit and generate a response for the new unit."""
        session = self.get_session(session_id)
        sm = session.state_machine
        result = sm.advance_unit()

        payload = {
            "session_id": session_id,
            "success": result.get("success", False),
            "completed": result.get("completed", False),
            "unit_index": sm.context.current_unit_index,
            "state": sm.get_state_summary(),
            "response": None,
            "role": None,
        }

        if not payload["success"] or payload["completed"]:
            return payload

        assignment = self._current_assignment(session)
        sm.start_bot_response()
        response = self._generate_response(assignment.role_template, assignment.semantic_unit.text)
        sm.context.current_role = assignment.assigned_role.value
        sm.transition(EventType.BOT_RESPONSE, {"type": "next_unit"})
        sm.finish_bot_response()

        payload["response"] = response
        payload["role"] = assignment.assigned_role.value
        payload["state"] = sm.get_state_summary()
        return payload

    def get_session_state(self, session_id: str) -> Dict:
        """Return session metadata and frontend-ready state."""
        session = self.get_session(session_id)
        sm = session.state_machine
        current_role = sm.context.current_role

        return {
            "session_id": session_id,
            "filename": session.filename,
            "total_units": sm.context.total_units,
            "current_unit_index": sm.context.current_unit_index,
            "current_role": current_role,
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

    def _generate_response(
        self,
        template: RoleTemplate,
        context: str,
        user_input: Optional[str] = None,
    ) -> str:
        """Generate response with LLM provider, or deterministic fallback when unavailable."""
        short_context = context[:1800]
        prompt = template.build_prompt(short_context, user_input=user_input)

        client = self._get_llm_client()
        if client is None:
            return self._fallback_response(template, short_context, user_input=user_input)

        try:
            return client.generate(
                prompt,
                temperature=template.temperature,
                max_tokens=template.max_tokens,
            ).strip()
        except Exception as exc:
            logger.warning(f"LLM generation failed, using fallback response: {exc}")
            self._llm_available = False
            return self._fallback_response(template, short_context, user_input=user_input)

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
        """Deterministic fallback response used when no provider is available."""
        preview = context.split("\n\n")[0][:320]
        if user_input:
            return (
                f"[{template.name}] I am running in fallback mode (no active LLM provider). "
                f"You asked: {user_input}\n\n"
                f"From this section: {preview}\n\n"
                f"Key guidance: focus on the main concept, then ask for the next unit when ready."
            )
        return (
            f"[{template.name}] We are now on a new section. "
            f"Here is the focus:\n\n{preview}\n\n"
            f"Ask a question or request clarification, and I will continue in {template.name} mode."
        )
