"""
Unit Tests for Conversation State Machine
Tests the ACTUAL implemented API (not old deprecated methods)
"""
import pytest
from datetime import datetime
from app.state_machine.conversation_state import (
    ConversationState,
    EventType,
    StateTransition,
    ConversationContext,
    ConversationStateMachine
)


class TestConversationState:
    """Test ConversationState enum"""
    
    def test_all_states_defined(self):
        """Test all states are defined"""
        expected_states = ['IDLE', 'READY', 'ENGAGED', 'INTERRUPTED', 'PAUSED', 'COMPLETED']
        
        for state_name in expected_states:
            assert hasattr(ConversationState, state_name), f"Missing state: {state_name}"
    
    def test_state_values(self):
        """Test state enum values"""
        assert ConversationState.IDLE.value == "idle"
        assert ConversationState.READY.value == "ready"
        assert ConversationState.ENGAGED.value == "engaged"
        assert ConversationState.INTERRUPTED.value == "interrupted"
        assert ConversationState.PAUSED.value == "paused"
        assert ConversationState.COMPLETED.value == "completed"


class TestEventType:
    """Test EventType enum"""
    
    def test_all_events_defined(self):
        """Test all events are defined"""
        expected_events = [
            'INITIALIZE', 'DOCUMENT_LOADED', 'ROLES_ASSIGNED', 'START_DIALOGUE',
            'USER_MESSAGE', 'BOT_RESPONSE', 'NEXT_UNIT',
            'USER_INTERRUPT', 'RESUME',
            'PAUSE', 'UNPAUSE', 'COMPLETE', 'RESET'
        ]
        
        for event_name in expected_events:
            assert hasattr(EventType, event_name), f"Missing event: {event_name}"
    
    def test_event_values(self):
        """Test event enum values"""
        assert EventType.INITIALIZE.value == "initialize"
        assert EventType.USER_INTERRUPT.value == "user_interrupt"
        assert EventType.RESUME.value == "resume"


class TestStateTransition:
    """Test StateTransition dataclass"""
    
    def test_create_transition(self):
        """Test transition creation"""
        transition = StateTransition(
            from_state=ConversationState.ENGAGED,
            to_state=ConversationState.INTERRUPTED,
            event=EventType.USER_INTERRUPT
        )
        
        assert transition.from_state == ConversationState.ENGAGED
        assert transition.to_state == ConversationState.INTERRUPTED
        assert transition.event == EventType.USER_INTERRUPT
        assert isinstance(transition.timestamp, datetime)


class TestConversationContext:
    """Test ConversationContext dataclass"""
    
    def test_create_context(self):
        """Test context creation"""
        ctx = ConversationContext(session_id="test_123")
        
        assert ctx.current_state == ConversationState.IDLE
        assert ctx.current_unit_index == 0
        assert ctx.total_units == 0
        assert ctx.session_id == "test_123"
        assert ctx.bot_is_generating == False
        assert ctx.awaiting_user_input == False
    
    def test_context_serialization(self):
        """Test to_dict and from_dict"""
        ctx = ConversationContext(
            session_id="test_456",
            current_unit_index=3,
            total_units=10
        )
        ctx.current_state = ConversationState.ENGAGED
        ctx.bot_is_generating = True
        
        # Serialize
        data = ctx.to_dict()
        assert data['session_id'] == "test_456"
        assert data['current_unit_index'] == 3
        assert data['total_units'] == 10
        assert data['current_state'] == "engaged"
        assert data['bot_is_generating'] == True
        
        # Deserialize
        ctx2 = ConversationContext.from_dict(data)
        assert ctx2.session_id == "test_456"
        assert ctx2.current_unit_index == 3
        assert ctx2.current_state == ConversationState.ENGAGED
        assert ctx2.bot_is_generating == True


class TestConversationStateMachine:
    """Test ConversationStateMachine"""
    
    def test_initialization(self):
        """Test state machine initialization"""
        sm = ConversationStateMachine(session_id="test")
        
        assert sm.context.current_state == ConversationState.IDLE
        assert sm.context.session_id == "test"
    
    def test_valid_transitions(self):
        """Test valid state transitions"""
        sm = ConversationStateMachine()
        
        # Setup flow
        sm.transition(EventType.INITIALIZE)
        assert sm.context.current_state == ConversationState.IDLE
        
        sm.transition(EventType.DOCUMENT_LOADED)
        assert sm.context.current_state == ConversationState.READY
        
        sm.transition(EventType.ROLES_ASSIGNED)
        assert sm.context.current_state == ConversationState.READY
        
        sm.transition(EventType.START_DIALOGUE)
        assert sm.context.current_state == ConversationState.ENGAGED
    
    def test_invalid_transition(self):
        """Test invalid transition raises error"""
        sm = ConversationStateMachine()
        sm.transition(EventType.INITIALIZE)
        
        with pytest.raises(ValueError):
            sm.transition(EventType.USER_INTERRUPT)  # Can't interrupt from IDLE
    
    def test_interruption_flow(self):
        """Test interruption flow"""
        sm = ConversationStateMachine()
        
        # Setup to ENGAGED
        sm.transition(EventType.INITIALIZE)
        sm.transition(EventType.DOCUMENT_LOADED)
        sm.context.total_units = 3
        sm.transition(EventType.ROLES_ASSIGNED)
        sm.transition(EventType.START_DIALOGUE)
        
        # User interrupts
        result = sm.user_clicks_interrupt()
        assert result['success'] == True
        assert sm.context.current_state == ConversationState.INTERRUPTED
        assert sm.context.interruption_count == 1
        
        # Process interruption message
        result = sm.process_interruption_message("what does this mean?")
        assert result['should_generate_response'] == True
        
        # Resume
        result = sm.resume_conversation()
        assert result['success'] == True
        assert sm.context.current_state == ConversationState.ENGAGED
    
    def test_advance_unit(self):
        """Test unit advancement"""
        sm = ConversationStateMachine()
        
        # Setup
        sm.transition(EventType.INITIALIZE)
        sm.transition(EventType.DOCUMENT_LOADED)
        sm.context.total_units = 3
        sm.transition(EventType.ROLES_ASSIGNED)
        sm.transition(EventType.START_DIALOGUE)
        
        assert sm.context.current_unit_index == 0
        
        # Advance
        result = sm.advance_unit()
        assert result['success'] == True
        assert result['completed'] == False
        assert sm.context.current_unit_index == 1
        
        result = sm.advance_unit()
        assert sm.context.current_unit_index == 2
        
        # Last unit
        result = sm.advance_unit()
        assert result['completed'] == True
        assert sm.context.current_state == ConversationState.COMPLETED
    
    def test_bot_response_lifecycle(self):
        """Test bot response start/finish"""
        sm = ConversationStateMachine()
        
        sm.transition(EventType.INITIALIZE)
        sm.transition(EventType.DOCUMENT_LOADED)
        sm.transition(EventType.ROLES_ASSIGNED)
        sm.transition(EventType.START_DIALOGUE)
        
        # Start generating
        sm.start_bot_response()
        assert sm.context.bot_is_generating == True
        assert sm.context.awaiting_user_input == False
        
        # Finish
        sm.finish_bot_response()
        assert sm.context.bot_is_generating == False
        assert sm.context.awaiting_user_input == True
        assert sm.context.message_count == 1
    
    def test_state_summary(self):
        """Test get_state_summary"""
        sm = ConversationStateMachine()
        
        sm.transition(EventType.INITIALIZE)
        sm.transition(EventType.DOCUMENT_LOADED)
        sm.context.total_units = 5
        sm.transition(EventType.ROLES_ASSIGNED)
        sm.transition(EventType.START_DIALOGUE)
        
        summary = sm.get_state_summary()
        
        assert summary['current_state'] == 'engaged'
        assert summary['progress']['total_units'] == 5
        assert summary['progress']['current_unit'] == 0
        assert summary['bot_status']['is_generating'] == False
        assert summary['can_interrupt'] == True
        assert summary['is_complete'] == False
    
    def test_persistence(self):
        """Test save and load state"""
        sm = ConversationStateMachine(session_id="persist_test")
        
        # Setup state
        sm.transition(EventType.INITIALIZE)
        sm.transition(EventType.DOCUMENT_LOADED)
        sm.context.total_units = 10
        sm.transition(EventType.ROLES_ASSIGNED)
        sm.transition(EventType.START_DIALOGUE)
        sm.advance_unit()
        sm.advance_unit()
        
        # Save
        state_data = sm.save_state()
        assert state_data['session_id'] == "persist_test"
        assert state_data['current_unit_index'] == 2
        
        # Load into new instance
        sm2 = ConversationStateMachine()
        sm2.load_state(state_data)
        
        assert sm2.context.session_id == "persist_test"
        assert sm2.context.current_unit_index == 2
        assert sm2.context.total_units == 10
        assert sm2.context.current_state == ConversationState.ENGAGED
    
    def test_multiple_interruptions(self):
        """Test multiple interruptions"""
        sm = ConversationStateMachine()
        
        # Setup
        sm.transition(EventType.INITIALIZE)
        sm.transition(EventType.DOCUMENT_LOADED)
        sm.context.total_units = 5
        sm.transition(EventType.ROLES_ASSIGNED)
        sm.transition(EventType.START_DIALOGUE)
        
        # First interruption
        sm.user_clicks_interrupt()
        assert sm.context.interruption_count == 1
        sm.resume_conversation()
        
        # Second interruption
        sm.user_clicks_interrupt()
        assert sm.context.interruption_count == 2
        sm.resume_conversation()
        
        assert sm.context.current_state == ConversationState.ENGAGED
    
    def test_bot_response_during_interruption_no_double_count(self):
        """
        Regression test for Bug #1: Bot responding DURING interruption 
        should not double-count interruption or change interrupted_at_index.
        """
        sm = ConversationStateMachine()
        
        # Setup
        sm.transition(EventType.INITIALIZE)
        sm.transition(EventType.DOCUMENT_LOADED)
        sm.context.total_units = 5
        sm.transition(EventType.ROLES_ASSIGNED)
        sm.transition(EventType.START_DIALOGUE)
        
        # User interrupts at unit 0
        result = sm.user_clicks_interrupt()
        assert sm.context.current_state == ConversationState.INTERRUPTED
        assert sm.context.interrupted_at_index == 0
        assert sm.context.interruption_count == 1
        
        # Save original values
        original_interrupted_at = sm.context.interrupted_at_index
        original_count = sm.context.interruption_count
        
        # User asks interruption question
        sm.process_interruption_message("I don't understand X")
        
        # Bot responds WHILE STILL INTERRUPTED
        sm.start_bot_response()
        assert sm.context.current_state == ConversationState.INTERRUPTED
        assert sm.context.bot_is_generating == True
        # Bug #1 fix: These should NOT change
        assert sm.context.interrupted_at_index == original_interrupted_at
        assert sm.context.interruption_count == original_count
        
        sm.finish_bot_response()
        assert sm.context.bot_is_generating == False
        # Still should not have changed
        assert sm.context.interrupted_at_index == original_interrupted_at
        assert sm.context.interruption_count == original_count
        
        # User asks another question (multi-turn during interruption)
        sm.process_interruption_message("What about Y?")
        sm.start_bot_response()
        sm.finish_bot_response()
        
        # STILL should not have changed
        assert sm.context.interrupted_at_index == original_interrupted_at
        assert sm.context.interruption_count == original_count
        
        # Finally resume
        sm.resume_conversation()
        assert sm.context.current_state == ConversationState.ENGAGED
        
        # Verify we returned to correct unit
        assert sm.context.current_unit_index == original_interrupted_at
    
    def test_pause_unpause(self):
        """Test pause and unpause"""
        sm = ConversationStateMachine()
        
        # Setup
        sm.transition(EventType.INITIALIZE)
        sm.transition(EventType.DOCUMENT_LOADED)
        sm.transition(EventType.ROLES_ASSIGNED)
        sm.transition(EventType.START_DIALOGUE)
        
        # Pause
        sm.transition(EventType.PAUSE)
        assert sm.context.current_state == ConversationState.PAUSED
        
        # Unpause
        sm.transition(EventType.UNPAUSE)
        assert sm.context.current_state == ConversationState.ENGAGED
    
    def test_reset(self):
        """Test reset functionality"""
        sm = ConversationStateMachine()
        
        # Setup state
        sm.transition(EventType.INITIALIZE)
        sm.transition(EventType.DOCUMENT_LOADED)
        sm.transition(EventType.ROLES_ASSIGNED)
        sm.transition(EventType.START_DIALOGUE)
        
        # Reset
        sm.reset()
        assert sm.context.current_state == ConversationState.IDLE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
