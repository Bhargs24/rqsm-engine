# Frontend Integration API Guide

## Overview
Clean, button-based API for building chat UI. No complex timing logic - just explicit user actions.

---

## UI Components Needed

```
┌─────────────────────────────────────────────┐
│  Chat Window                                │
│  ┌───────────────────────────────────────┐  │
│  │ Bot: Let me explain neural networks...│  │
│  │ [Bot is typing... ⏳]                  │  │  <- Show when bot_is_generating = true
│  │                                       │  │
│  │ User: ok got it                       │  │
│  │                                       │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  [INTERRUPT BUTTON] 🛑                      │  <- Always visible, enabled when ENGAGED
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │ Type your message...                  │  │  <- Enable when awaiting_user_input = true
│  │ [SEND]                                │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  After Interruption:                        │
│  [RESUME FROM WHERE WE LEFT OFF]            │
│  [RESTART THIS TOPIC]                       │
└─────────────────────────────────────────────┘
```

---

## Core Methods (Frontend → Backend)

### 1. **Starting Conversation**
```python
# Step 1: Initialize
state_machine = ConversationStateMachine(session_id="user_123")
state_machine.transition(EventType.INITIALIZE)

# Step 2: Load document
state_machine.transition(EventType.DOCUMENT_LOADED, {'total_units': 10})
state_machine.context.total_units = 10

# Step 3: Assign roles
state_machine.transition(EventType.ROLES_ASSIGNED)

# Step 4: Start dialogue
state_machine.transition(EventType.START_DIALOGUE)
```

### 2. **Bot Response Flow**
```python
# When bot STARTS generating
state_machine.start_bot_response()
# UI: Show "Bot is typing..." indicator

# ... bot generates response via LLM ...

# When bot FINISHES
state_machine.finish_bot_response()
# UI: Hide typing indicator, enable input box
```

### 3. **User Clicks [INTERRUPT] Button**
```python
result = state_machine.user_clicks_interrupt()

if result['success']:
    # UI: Show interrupt dialog
    print(f"Interrupted at unit {result['interrupted_at_unit']}")
    # Prompt user: "What's your question?"
```

### 4. **User Submits Interruption Message**
```python
user_message = "wait, I don't understand X"

result = state_machine.process_interruption_message(user_message)

# IMPORTANT: This method only RECORDS the message
# You must ALSO trigger bot response:
state_machine.start_bot_response()
# ... generate bot's answer to interruption via LLM ...
bot_answer = generate_llm_response(user_message)
state_machine.finish_bot_response()

# Now user can choose to resume or ask follow-ups
```

**Complete Interruption Flow**:
1. User clicks [INTERRUPT] → `user_clicks_interrupt()`
2. User types question → `process_interruption_message(message)`
3. Bot responds → `start_bot_response()` + LLM call + `finish_bot_response()`
4. User reads answer, optionally sends more messages (repeat 2-3)
5. User clicks [RESUME] → `resume_conversation()`

### 5. **Resume After Interruption**
```python
# User clicks [RESUME FROM WHERE WE LEFT OFF]
result = state_machine.resume_conversation(from_start=False)

# OR user clicks [RESTART THIS TOPIC]
result = state_machine.resume_conversation(from_start=True)

# Continue normal flow
```

### 6. **Regular User Message (Not Interruption)**
```python
user_message = "that makes sense, thanks"

result = state_machine.process_user_message(user_message)
# Bot generates response
```

### 7. **Advancing to Next Topic**
```python
# When bot or user decides to move forward
result = state_machine.advance_unit()

if result['completed']:
    # Conversation finished!
    print("All topics covered")
else:
    print(f"Now on unit {result['new_unit']}")
```

---

## State Checks (Backend → Frontend)

### Get Current State
```python
summary = state_machine.get_state_summary()

# Use for UI rendering:
summary = {
    'current_state': 'engaged',  # idle, ready, engaged, interrupted, etc.
    'bot_status': {
        'is_generating': False,     # Show typing indicator?
        'awaiting_input': True,     # Enable input box?
    },
    'progress': {
        'current_unit': 3,
        'total_units': 10,
        'percentage': 30.0
    },
    'interruptions': 2,
    'can_resume': False,            # Show resume buttons?
    'is_complete': False
}
```

### UI Rendering Logic
```javascript
// Pseudocode for frontend
if (state.bot_status.is_generating) {
    showTypingIndicator();
    disableInputBox();
    enableInterruptButton();
}

if (state.bot_status.awaiting_input) {
    hideTypingIndicator();
    enableInputBox();
    enableInterruptButton();
}

if (state.current_state === 'interrupted') {
    showResumeButtons();
}

if (state.is_complete) {
    showCompletionMessage();
    disableAllInputs();
}
```

---

## Complete Flow Example

```python
from app.state_machine.conversation_state import ConversationStateMachine, EventType

# Setup
sm = ConversationStateMachine(session_id="demo")
sm.transition(EventType.INITIALIZE)
sm.transition(EventType.DOCUMENT_LOADED, {'total_units': 5})
sm.context.total_units = 5
sm.transition(EventType.ROLES_ASSIGNED)
sm.transition(EventType.START_DIALOGUE)

# === Unit 1: Normal Flow ===
print("Unit 1: Explaining ML basics...")

sm.start_bot_response()
bot_message = generate_llm_response("Explain machine learning")  # Your LLM call
sm.finish_bot_response()

user_input = get_user_input()  # "ok, got it"
sm.process_user_message(user_input)
sm.advance_unit()

# === Unit 2: User Interrupts ===
print("Unit 2: Explaining neural networks...")

sm.start_bot_response()
# Bot starts generating...

# USER CLICKS [INTERRUPT] BUTTON
result = sm.user_clicks_interrupt()
print(f"Interrupted at unit {result['interrupted_at_unit']}")

# Get user's interruption question
user_question = get_user_input()  # "wait, what is a neuron?"
sm.process_interruption_message(user_question)

# Bot answers the interruption
sm.start_bot_response()
bot_answer = generate_llm_response(user_question)
sm.finish_bot_response()

# User satisfied
user_response = get_user_input()  # "ah ok, thanks"

# Resume conversation
result = sm.resume_conversation(from_start=False)
# Continue from unit 2...
```

---

## Error Handling

### Invalid State Transitions
```python
result = sm.user_clicks_interrupt()

if not result['success']:
    # Show error: result['message']
    # Example: "Cannot interrupt - conversation is idle"
```

### Completion Check
```python
result = sm.advance_unit()

if result['completed']:
    # Show completion screen
    # Disable further input
    # Show summary stats
```

---

## Persistence (Save/Load Sessions)

```python
# Save state
state_data = sm.save_state()
save_to_database(session_id="user_123", state=state_data)

# Load state (e.g., user returns later)
state_data = load_from_database(session_id="user_123")
sm = ConversationStateMachine()
sm.load_state(state_data)

# Continue from where they left off
summary = sm.get_state_summary()
print(f"Welcome back! You're at unit {summary['progress']['current_unit']}")
```

---

## Key Design Decisions

✅ **Explicit Interruption** - Button makes intent clear, no guessing  
✅ **Two-Phase Interrupt** - Click interrupt → Type question → Submit  
✅ **Clear Resume Options** - User chooses: continue or restart topic  
✅ **State Indicators** - UI always knows what to show (typing, input, buttons)  
✅ **No Timing Logic** - Frontend doesn't need to track timestamps  
✅ **Separation of Concerns** - State machine = logic, Frontend = presentation  

---

## Testing Checklist for Frontend

- [ ] "Bot is typing..." shows when `bot_is_generating = True`
- [ ] Input box enables when `awaiting_user_input = True`
- [ ] [INTERRUPT] button works during bot response
- [ ] Interrupt dialog appears after clicking interrupt
- [ ] Resume buttons show after interruption resolved
- [ ] Progress bar updates on `advance_unit()`
- [ ] Completion screen shows when `is_complete = True`
- [ ] State persists on page refresh
