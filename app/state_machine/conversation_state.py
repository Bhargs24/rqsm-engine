"""
Conversation State Machine
Clean, frontend-friendly interruption system
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger


class ConversationState(Enum):
    """Conversation states"""
    IDLE = "idle"
    READY = "ready"
    ENGAGED = "engaged"
    INTERRUPTED = "interrupted"
    PAUSED = "paused"
    COMPLETED = "completed"


class EventType(Enum):
    """State machine events"""
    # Setup
    INITIALIZE = "initialize"
    DOCUMENT_LOADED = "document_loaded"
    ROLES_ASSIGNED = "roles_assigned"
    START_DIALOGUE = "start_dialogue"
    
    # Flow
    USER_MESSAGE = "user_message"
    BOT_RESPONSE = "bot_response"
    NEXT_UNIT = "next_unit"
    
    # Interruption
    USER_INTERRUPT = "user_interrupt"
    RESUME = "resume"
    
    # Control
    PAUSE = "pause"
    UNPAUSE = "unpause"
    COMPLETE = "complete"
    RESET = "reset"


@dataclass
class StateTransition:
    """Record of a state transition"""
    from_state: ConversationState
    to_state: ConversationState
    event: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """All conversation state data"""
    # State
    current_state: ConversationState = ConversationState.IDLE
    
    # Progress
    current_unit_index: int = 0
    total_units: int = 0
    current_role: Optional[str] = None
    
    # UI Indicators
    bot_is_generating: bool = False      # Show typing indicator
    awaiting_user_input: bool = False    # Enable input box
    
    # Interruption tracking
    interrupted_at_index: Optional[int] = None
    interruption_count: int = 0
    
    # History
    state_history: List[StateTransition] = field(default_factory=list)
    message_count: int = 0
    
    # Metadata
    session_id: Optional[str] = None
    started_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict"""
        return {
            'current_state': self.current_state.value,
            'current_unit_index': self.current_unit_index,
            'total_units': self.total_units,
            'current_role': self.current_role,
            'bot_is_generating': self.bot_is_generating,
            'awaiting_user_input': self.awaiting_user_input,
            'interrupted_at_index': self.interrupted_at_index,
            'interruption_count': self.interruption_count,
            'message_count': self.message_count,
            'session_id': self.session_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationContext':
        """Deserialize from dict"""
        ctx = cls(
            current_state=ConversationState(data['current_state']),
            current_unit_index=data['current_unit_index'],
            total_units=data['total_units'],
            current_role=data.get('current_role'),
            bot_is_generating=data.get('bot_is_generating', False),
            awaiting_user_input=data.get('awaiting_user_input', False),
            interrupted_at_index=data.get('interrupted_at_index'),
            interruption_count=data.get('interruption_count', 0),
            message_count=data.get('message_count', 0),
            session_id=data.get('session_id'),
        )
        
        if data.get('started_at'):
            ctx.started_at = datetime.fromisoformat(data['started_at'])
        if data.get('last_activity'):
            ctx.last_activity = datetime.fromisoformat(data['last_activity'])
        
        return ctx


class ConversationStateMachine:
    """
    State machine for interruption-resilient conversations.
    Simple, deterministic transitions for frontend integration.
    """
    
    # Valid transitions: {(from_state, event): to_state}
    TRANSITIONS = {
        # Setup flow
        (ConversationState.IDLE, EventType.INITIALIZE): ConversationState.IDLE,
        (ConversationState.IDLE, EventType.DOCUMENT_LOADED): ConversationState.READY,
        (ConversationState.READY, EventType.ROLES_ASSIGNED): ConversationState.READY,
        (ConversationState.READY, EventType.START_DIALOGUE): ConversationState.ENGAGED,
        
        # Normal conversation
        (ConversationState.ENGAGED, EventType.USER_MESSAGE): ConversationState.ENGAGED,
        (ConversationState.ENGAGED, EventType.BOT_RESPONSE): ConversationState.ENGAGED,
        (ConversationState.ENGAGED, EventType.NEXT_UNIT): ConversationState.ENGAGED,
        
        # Interruption: ENGAGED → INTERRUPTED → ENGAGED (after handling)
        (ConversationState.ENGAGED, EventType.USER_INTERRUPT): ConversationState.INTERRUPTED,
        (ConversationState.INTERRUPTED, EventType.BOT_RESPONSE): ConversationState.INTERRUPTED,  # Bot answers interruption
        (ConversationState.INTERRUPTED, EventType.RESUME): ConversationState.ENGAGED,  # Continue
        
        # Pause
        (ConversationState.ENGAGED, EventType.PAUSE): ConversationState.PAUSED,
        (ConversationState.PAUSED, EventType.UNPAUSE): ConversationState.ENGAGED,
        
        # Completion
        (ConversationState.ENGAGED, EventType.COMPLETE): ConversationState.COMPLETED,
        
        # Reset
        (ConversationState.READY, EventType.RESET): ConversationState.IDLE,
        (ConversationState.ENGAGED, EventType.RESET): ConversationState.IDLE,
        (ConversationState.INTERRUPTED, EventType.RESET): ConversationState.IDLE,
        (ConversationState.PAUSED, EventType.RESET): ConversationState.IDLE,
        (ConversationState.COMPLETED, EventType.RESET): ConversationState.IDLE,
    }
    
    def __init__(self, session_id: Optional[str] = None):
        """Initialize state machine"""
        self.context = ConversationContext(session_id=session_id)
        logger.info(f"State machine initialized (session: {session_id})")
    
    def can_transition(self, event: EventType) -> bool:
        """Check if event is valid from current state"""
        return (self.context.current_state, event) in self.TRANSITIONS
    
    def transition(self, event: EventType, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Execute state transition.
        
        Args:
            event: Event triggering transition
            metadata: Optional context
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If transition invalid
        """
        if not self.can_transition(event):
            valid_events = [e.value for (s, e) in self.TRANSITIONS.keys() 
                          if s == self.context.current_state]
            raise ValueError(
                f"Invalid transition: {self.context.current_state.value} + {event.value}. "
                f"Valid events: {valid_events}"
            )
        
        old_state = self.context.current_state
        new_state = self.TRANSITIONS[(old_state, event)]
        
        # Record transition
        transition = StateTransition(
            from_state=old_state,
            to_state=new_state,
            event=event,
            metadata=metadata or {}
        )
        self.context.state_history.append(transition)
        
        # Update state
        self.context.current_state = new_state
        self.context.last_activity = datetime.now()
        
        # Handle state-specific logic
        self._handle_state_entry(new_state, event, metadata)
        
        logger.debug(f"Transition: {old_state.value} → {new_state.value} ({event.value})")
        return True
    
    def _handle_state_entry(
        self,
        state: ConversationState,
        event: EventType,
        metadata: Optional[Dict[str, Any]]
    ):
        """Execute logic when entering a state"""
        if state == ConversationState.ENGAGED and event == EventType.START_DIALOGUE:
            self.context.started_at = datetime.now()
            self.context.current_unit_index = 0
        
        elif state == ConversationState.INTERRUPTED:
            # Only record interruption on USER_INTERRUPT event, not on every entry
            # (bot can respond during INTERRUPTED state via BOT_RESPONSE event)
            if event == EventType.USER_INTERRUPT:
                self.context.interrupted_at_index = self.context.current_unit_index
                self.context.interruption_count += 1
                logger.info(f"Interrupt #{self.context.interruption_count} at unit {self.context.current_unit_index}")
        
        elif state == ConversationState.ENGAGED and event == EventType.RESUME:
            logger.info(f"Resumed at unit {self.context.current_unit_index}")
        
        elif state == ConversationState.COMPLETED:
            logger.info("Conversation completed")
    
    # =========================================================================
    # FRONTEND API - Methods called by UI
    # =========================================================================
    
    def start_bot_response(self):
        """
        Bot starts generating response.
        Frontend: Show "Bot is typing..." indicator
        """
        self.context.bot_is_generating = True
        self.context.awaiting_user_input = False
        logger.debug("Bot started generating")
    
    def finish_bot_response(self):
        """
        Bot finishes generating response.
        Frontend: Hide typing, enable input
        """
        self.context.bot_is_generating = False
        self.context.awaiting_user_input = True
        self.context.message_count += 1
        logger.debug("Bot finished, awaiting user")
    
    def user_clicks_interrupt(self) -> Dict[str, Any]:
        """
        User clicks [INTERRUPT] button.
        
        Flow:
        1. User clicks button
        2. Bot stops (if generating)
        3. Show input: "What's your question?"
        4. User types and submits → call process_interruption_message()
        
        Returns:
            {
                'success': bool,
                'interrupted_at_unit': int,
                'message': str
            }
        """
        if self.context.current_state != ConversationState.ENGAGED:
            return {
                'success': False,
                'message': f'Cannot interrupt - state is {self.context.current_state.value}'
            }
        
        interrupted_unit = self.context.current_unit_index
        
        # Stop bot immediately
        self.context.bot_is_generating = False
        self.context.awaiting_user_input = True
        
        # Transition to INTERRUPTED
        self.transition(EventType.USER_INTERRUPT, {
            'interrupted_at_unit': interrupted_unit
        })
        
        logger.info(f"User interrupted at unit {interrupted_unit}")
        
        return {
            'success': True,
            'interrupted_at_unit': interrupted_unit,
            'message': "What's your question?"
        }
    
    def process_interruption_message(self, message: str) -> Dict[str, Any]:
        """
        User submitted their interruption question.
        
        Args:
            message: User's question
            
        Returns:
            {
                'interrupted_unit': int,
                'user_message': str,
                'should_generate_response': bool
            }
        """
        if self.context.current_state != ConversationState.INTERRUPTED:
            return {
                'error': f'Not in interrupted state (current: {self.context.current_state.value})'
            }
        
        logger.info(f"Processing interruption: '{message}'")
        
        return {
            'interrupted_unit': self.context.interrupted_at_index,
            'user_message': message,
            'should_generate_response': True
        }
    
    def resume_conversation(self) -> Dict[str, Any]:
        """
        Resume conversation after handling interruption.
        
        Called after bot answers user's interruption question.
        Just continues from current unit naturally.
        
        Returns:
            {
                'success': bool,
                'resuming_from_unit': int
            }
        """
        if self.context.current_state != ConversationState.INTERRUPTED:
            return {
                'success': False,
                'message': f'Not interrupted (current: {self.context.current_state.value})'
            }
        
        # Transition back to ENGAGED
        self.transition(EventType.RESUME, {
            'resumed_from_unit': self.context.current_unit_index
        })
        
        logger.info(f"Resuming from unit {self.context.current_unit_index}")
        
        return {
            'success': True,
            'resuming_from_unit': self.context.current_unit_index
        }
    
    def process_user_message(self, message: str) -> Dict[str, Any]:
        """
        Process regular user message (not interruption).
        
        Args:
            message: User's message
            
        Returns:
            {
                'current_unit': int
            }
        """
        if self.context.current_state != ConversationState.ENGAGED:
            return {
                'error': f'Cannot process message in state {self.context.current_state.value}'
            }
        
        self.transition(EventType.USER_MESSAGE, {'message': message})
        logger.debug(f"User message received")
        
        return {
            'current_unit': self.context.current_unit_index
        }
    
    def advance_unit(self) -> Dict[str, Any]:
        """
        Move to next topic/unit.
        
        Returns:
            {
                'success': bool,
                'new_unit': int,
                'completed': bool
            }
        """
        if self.context.current_state != ConversationState.ENGAGED:
            return {
                'success': False,
                'message': f'Cannot advance in state {self.context.current_state.value}'
            }
        
        if self.context.current_unit_index >= self.context.total_units - 1:
            # Reached end
            self.transition(EventType.COMPLETE)
            return {
                'success': True,
                'new_unit': self.context.current_unit_index,
                'completed': True
            }
        
        old_unit = self.context.current_unit_index
        self.context.current_unit_index += 1
        self.transition(EventType.NEXT_UNIT, {
            'from_unit': old_unit,
            'to_unit': self.context.current_unit_index
        })
        
        logger.info(f"Advanced: unit {old_unit} → {self.context.current_unit_index}")
        
        return {
            'success': True,
            'new_unit': self.context.current_unit_index,
            'completed': False
        }
    
    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get current state for UI rendering.
        
        Returns:
            Complete state info for frontend
        """
        return {
            'current_state': self.context.current_state.value,
            'bot_status': {
                'is_generating': self.context.bot_is_generating,
                'awaiting_input': self.context.awaiting_user_input,
            },
            'progress': {
                'current_unit': self.context.current_unit_index,
                'total_units': self.context.total_units,
                'percentage': (self.context.current_unit_index / self.context.total_units * 100) 
                             if self.context.total_units > 0 else 0
            },
            'interruptions': self.context.interruption_count,
            'messages': self.context.message_count,
            'can_interrupt': self.context.current_state == ConversationState.ENGAGED,
            'can_resume': self.context.current_state == ConversationState.INTERRUPTED,
            'is_complete': self.context.current_state == ConversationState.COMPLETED,
        }
    
    # =========================================================================
    # PERSISTENCE
    # =========================================================================
    
    def save_state(self) -> Dict[str, Any]:
        """Save state for persistence"""
        return self.context.to_dict()
    
    def load_state(self, state_data: Dict[str, Any]):
        """Load state from persistence"""
        self.context = ConversationContext.from_dict(state_data)
        logger.info(f"State loaded for session {self.context.session_id}")
    
    def reset(self):
        """Reset to initial state"""
        if self.context.current_state != ConversationState.IDLE:
            self.transition(EventType.RESET)
        logger.info("State machine reset")
