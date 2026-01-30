"""
Quick validation test for cleaned state machine
"""
from app.state_machine.conversation_state import ConversationStateMachine, EventType, ConversationState


def test_basic_flow():
    """Test basic conversation flow"""
    sm = ConversationStateMachine(session_id="test")
    
    # Setup
    sm.transition(EventType.INITIALIZE)
    assert sm.context.current_state == ConversationState.IDLE
    
    sm.transition(EventType.DOCUMENT_LOADED)
    sm.context.total_units = 3
    assert sm.context.current_state == ConversationState.READY
    
    sm.transition(EventType.ROLES_ASSIGNED)
    sm.transition(EventType.START_DIALOGUE)
    assert sm.context.current_state == ConversationState.ENGAGED
    
    print("[OK] Basic setup works")


def test_interruption_flow():
    """Test interruption handling"""
    sm = ConversationStateMachine(session_id="test")
    
    # Setup to ENGAGED
    sm.transition(EventType.INITIALIZE)
    sm.transition(EventType.DOCUMENT_LOADED)
    sm.context.total_units = 3
    sm.transition(EventType.ROLES_ASSIGNED)
    sm.transition(EventType.START_DIALOGUE)
    
    # Bot starts responding
    sm.start_bot_response()
    assert sm.context.bot_is_generating == True
    
    # User clicks interrupt
    result = sm.user_clicks_interrupt()
    assert result['success'] == True
    assert sm.context.current_state == ConversationState.INTERRUPTED
    assert sm.context.bot_is_generating == False
    
    # Bot answers interruption
    sm.start_bot_response()
    sm.transition(EventType.BOT_RESPONSE)
    sm.finish_bot_response()
    
    # Resume
    result = sm.resume_conversation()
    assert result['success'] == True
    assert sm.context.current_state == ConversationState.ENGAGED
    
    print("[OK] Interruption flow works")


def test_advance_unit():
    """Test unit advancement"""
    sm = ConversationStateMachine(session_id="test")
    
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
    
    # Last unit - should complete
    result = sm.advance_unit()
    assert result['completed'] == True
    assert sm.context.current_state == ConversationState.COMPLETED
    
    print("[OK] Unit advancement works")


def test_persistence():
    """Test state save/load"""
    sm = ConversationStateMachine(session_id="test_123")
    
    # Setup some state
    sm.transition(EventType.INITIALIZE)
    sm.transition(EventType.DOCUMENT_LOADED)
    sm.context.total_units = 5
    sm.transition(EventType.ROLES_ASSIGNED)
    sm.transition(EventType.START_DIALOGUE)
    
    # Advance a few units
    sm.advance_unit()
    sm.advance_unit()
    sm.advance_unit()
    
    # Save
    state_data = sm.save_state()
    assert state_data['session_id'] == "test_123"
    assert state_data['current_unit_index'] == 3
    assert state_data['total_units'] == 5
    
    # Load into new instance
    sm2 = ConversationStateMachine()
    sm2.load_state(state_data)
    
    assert sm2.context.session_id == "test_123"
    assert sm2.context.current_unit_index == 3
    assert sm2.context.total_units == 5
    assert sm2.context.current_state == ConversationState.ENGAGED
    
    print("[OK] Persistence works")


def test_ui_indicators():
    """Test frontend UI state indicators"""
    sm = ConversationStateMachine(session_id="test")
    
    # Setup
    sm.transition(EventType.INITIALIZE)
    sm.transition(EventType.DOCUMENT_LOADED)
    sm.context.total_units = 3
    sm.transition(EventType.ROLES_ASSIGNED)
    sm.transition(EventType.START_DIALOGUE)
    
    # Bot starts generating
    sm.start_bot_response()
    summary = sm.get_state_summary()
    assert summary['bot_status']['is_generating'] == True
    assert summary['bot_status']['awaiting_input'] == False
    
    # Bot finishes
    sm.finish_bot_response()
    summary = sm.get_state_summary()
    assert summary['bot_status']['is_generating'] == False
    assert summary['bot_status']['awaiting_input'] == True
    
    print("[OK] UI indicators work")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("RUNNING QUICK VALIDATION TESTS")
    print("="*60 + "\n")
    
    test_basic_flow()
    test_interruption_flow()
    test_advance_unit()
    test_persistence()
    test_ui_indicators()
    
    print("\n" + "="*60)
    print("[SUCCESS] ALL TESTS PASSED - System is working correctly")
    print("="*60 + "\n")
