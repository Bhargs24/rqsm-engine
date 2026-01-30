"""
Demo: Frontend-Friendly Interruption System
Shows clean API for UI integration with explicit interrupt button
"""
from app.state_machine.conversation_state import ConversationStateMachine, EventType


def simulate_bot_thinking(message: str):
    """Simulate bot generating response"""
    print(f"\n🤖 Bot: {message}")


def display_ui_state(sm: ConversationStateMachine):
    """Show what UI elements should be visible"""
    summary = sm.get_state_summary()
    
    print(f"\n{'='*60}")
    print(f"UI STATE")
    print(f"{'='*60}")
    print(f"Conversation: {summary['current_state'].upper()}")
    print(f"Progress: Unit {summary['progress']['current_unit'] + 1}/{summary['progress']['total_units']} "
          f"({summary['progress']['percentage']:.0f}%)")
    
    # UI element visibility
    print(f"\nUI Elements:")
    if summary['bot_status']['is_generating']:
        print(f"  ⏳ Typing indicator: VISIBLE")
        print(f"  📝 Input box: DISABLED")
        print(f"  🛑 [INTERRUPT] button: ENABLED (red, pulsing)")
    elif summary['bot_status']['awaiting_input']:
        print(f"  ⏳ Typing indicator: HIDDEN")
        print(f"  📝 Input box: ENABLED")
        print(f"  🛑 [INTERRUPT] button: ENABLED")
    
    if summary['can_resume']:
        print(f"  ▶️  [RESUME] buttons: VISIBLE")
    
    if summary['is_complete']:
        print(f"  ✅ Completion screen: SHOW")
    
    print(f"\nStats: {summary['messages']} messages, {summary['interruptions']} interruptions")


def main():
    print("="*70)
    print("FRONTEND-FRIENDLY INTERRUPTION SYSTEM")
    print("="*70)
    
    # Initialize
    sm = ConversationStateMachine(session_id="frontend_demo")
    sm.transition(EventType.INITIALIZE)
    sm.transition(EventType.DOCUMENT_LOADED, {'total_units': 3})
    sm.context.total_units = 3
    sm.transition(EventType.ROLES_ASSIGNED)
    sm.transition(EventType.START_DIALOGUE)
    
    print("\n📚 Document loaded: 'Introduction to Neural Networks' (3 units)")
    display_ui_state(sm)
    
    # =========================================================================
    # UNIT 1: Normal Flow - No Interruption
    # =========================================================================
    print("\n" + "="*70)
    print("UNIT 1: What is Machine Learning?")
    print("="*70)
    
    # Bot starts responding
    sm.start_bot_response()
    simulate_bot_thinking("Machine learning is a subset of artificial intelligence...")
    display_ui_state(sm)
    
    # Bot finishes
    sm.finish_bot_response()
    print("\n   (Bot finished, waiting for user)")
    display_ui_state(sm)
    
    # User responds normally
    print("\n👤 User: 'ok, got it, makes sense'")
    sm.process_user_message("ok, got it, makes sense")
    
    # Advance to next unit
    result = sm.advance_unit()
    print(f"\n➡️  Advanced to unit {result['new_unit'] + 1}")
    
    # =========================================================================
    # UNIT 2: User Clicks INTERRUPT Button
    # =========================================================================
    print("\n" + "="*70)
    print("UNIT 2: How Neural Networks Work")
    print("="*70)
    
    # Bot starts explaining
    sm.start_bot_response()
    simulate_bot_thinking("A neural network consists of layers of neurons...")
    print("   (Bot generating response... streaming words...)")
    display_ui_state(sm)
    
    # USER CLICKS [INTERRUPT] BUTTON
    print("\n" + "-"*70)
    print("👆 USER CLICKS [INTERRUPT] BUTTON")
    print("-"*70)
    
    result = sm.user_clicks_interrupt()
    
    if result['success']:
        print(f"\n✅ Interrupt successful!")
        print(f"   • Interrupted at unit {result['interrupted_at_unit'] + 1}")
        print(f"   • Bot was generating: {result['was_generating']}")
        print(f"   • Message: {result['message']}")
        
        # UI shows interrupt dialog
        print(f"\n   UI: Show interrupt dialog")
        print(f"   ┌─────────────────────────────────────┐")
        print(f"   │ What's your question?              │")
        print(f"   │ [Text input box]                   │")
        print(f"   │ [SUBMIT]                           │")
        print(f"   └─────────────────────────────────────┘")
    
    display_ui_state(sm)
    
    # User submits their interruption question
    print("\n👤 User (interruption): 'wait, what is a neuron exactly?'")
    result = sm.process_interruption_message("wait, what is a neuron exactly?")
    
    print(f"\n📝 Processing interruption...")
    print(f"   • Interrupted at unit: {result['interrupted_unit'] + 1}")
    print(f"   • User message: '{result['user_message']}'")
    print(f"   • Should generate response: {result['should_generate_response']}")
    
    # Bot responds to interruption
    print(f"\n   Bot generates response to interruption...")
    sm.start_bot_response()
    simulate_bot_thinking("Great question! A neuron is a computational unit that...")
    sm.finish_bot_response()
    
    display_ui_state(sm)
    
    # User satisfied with answer
    print("\n👤 User: 'ah okay, that makes sense now'")
    
    # UI shows resume options
    print(f"\n   UI: Show resume options")
    print(f"   ┌─────────────────────────────────────────┐")
    print(f"   │ [RESUME FROM WHERE WE LEFT OFF]        │")
    print(f"   │ [RESTART THIS TOPIC]                   │")
    print(f"   └─────────────────────────────────────────┘")
    
    # User clicks RESUME
    print("\n👆 User clicks [RESUME FROM WHERE WE LEFT OFF]")
    result = sm.resume_conversation(from_start=False)
    
    print(f"\n▶️  {result['message']}")
    print(f"   Resuming from unit {result['resuming_from_unit'] + 1}")
    
    display_ui_state(sm)
    
    # Continue conversation on unit 2
    print(f"\n   Bot continues explaining neural networks...")
    sm.start_bot_response()
    simulate_bot_thinking("So as I was saying, these neurons are organized in layers...")
    sm.finish_bot_response()
    
    print("\n👤 User: 'ok, next topic please'")
    sm.process_user_message("ok, next topic please")
    result = sm.advance_unit()
    print(f"➡️  Advanced to unit {result['new_unit'] + 1}")
    
    # =========================================================================
    # UNIT 3: Final Unit - Completion
    # =========================================================================
    print("\n" + "="*70)
    print("UNIT 3: Training Neural Networks")
    print("="*70)
    
    sm.start_bot_response()
    simulate_bot_thinking("To train a neural network, you need data and a loss function...")
    sm.finish_bot_response()
    
    print("\n👤 User: 'understood, thank you'")
    sm.process_user_message("understood, thank you")
    
    # Try to advance - should complete
    result = sm.advance_unit()
    
    if result['completed']:
        print(f"\n🎉 CONVERSATION COMPLETED!")
        print(f"   {result['message']}")
        
        print(f"\n   UI: Show completion screen")
        print(f"   ┌─────────────────────────────────────────┐")
        print(f"   │  ✅ Lesson Complete!                    │")
        print(f"   │                                         │")
        print(f"   │  You've covered all 3 topics:           │")
        print(f"   │  • What is Machine Learning             │")
        print(f"   │  • How Neural Networks Work             │")
        print(f"   │  • Training Neural Networks             │")
        print(f"   │                                         │")
        print(f"   │  [DOWNLOAD SUMMARY] [START NEW LESSON]  │")
        print(f"   └─────────────────────────────────────────┘")
    
    display_ui_state(sm)
    
    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "="*70)
    print("IMPLEMENTATION SUMMARY")
    print("="*70)
    
    print(f"\n✅ Frontend Integration Points:")
    print(f"   1. start_bot_response() → Show typing indicator")
    print(f"   2. finish_bot_response() → Hide typing, enable input")
    print(f"   3. user_clicks_interrupt() → Show interrupt dialog")
    print(f"   4. process_interruption_message() → Handle user's question")
    print(f"   5. resume_conversation() → Two options (resume/restart)")
    print(f"   6. process_user_message() → Normal user input")
    print(f"   7. advance_unit() → Move to next topic")
    print(f"   8. get_state_summary() → Update UI elements")
    
    print(f"\n🎨 UI Components Required:")
    print(f"   • Chat message list")
    print(f"   • Typing indicator (⏳)")
    print(f"   • [INTERRUPT] button (always visible when engaged)")
    print(f"   • Input box (enabled when awaiting_user_input)")
    print(f"   • Interrupt dialog modal")
    print(f"   • Resume buttons ([RESUME] / [RESTART])")
    print(f"   • Progress bar (unit X of Y)")
    print(f"   • Completion screen")
    
    print(f"\n📊 Final Stats:")
    summary = sm.get_state_summary()
    print(f"   • Units completed: {summary['progress']['current_unit'] + 1}/{summary['progress']['total_units']}")
    print(f"   • Total messages: {summary['messages']}")
    print(f"   • Interruptions handled: {summary['interruptions']}")
    print(f"   • Final state: {summary['current_state']}")


if __name__ == "__main__":
    main()
