# Project Architecture Document

## Document-Segment Driven Role-Oriented Conversational Study System (RQSM-Engine)

**Version:** 1.0  
**Date:** January 29, 2026  
**Project Type:** Academic Capstone (MVP Scope)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architectural Principles](#architectural-principles)
3. [System Components](#system-components)
4. [Data Flow Architecture](#data-flow-architecture)
5. [Module Interactions](#module-interactions)
6. [Technology Stack](#technology-stack)
7. [Design Patterns](#design-patterns)

---

## System Overview

### Purpose

The RQSM-Engine is a **deterministic, state-machine-orchestrated dialogue system** that transforms static educational documents into simulated multi-perspective study discussions using five distinct AI roles.

### Core Innovation

- **Deterministic Role Orchestration**: Same input always produces identical output
- **Multi-Role Dialogue**: Five complementary educational perspectives
- **Intelligent Interruption Handling**: Dynamic role reallocation based on user intent
- **Stability Guarantees**: Bounded delays and hysteresis prevent conversation oscillation

### The Five AI Roles

1. **Explainer** - Breaks down complex concepts into accessible terms
2. **Challenger** - Questions assumptions and explores edge cases
3. **Summarizer** - Distills key takeaways into concise points
4. **Example-Generator** - Provides analogies and real-world examples
5. **Misconception-Spotter** - Identifies and corrects common errors

---

## Architectural Principles

### 1. Determinism First

**Principle**: Given identical inputs, the system must produce identical outputs.

**Implementation**:
- LLM temperature = 0.0
- Fixed random seeds
- Deterministic role scoring algorithms
- Reproducible state transitions

### 2. Pedagogical Grounding

**Principle**: System behavior aligns with educational theory (Vygotsky's Zone of Proximal Development).

**Implementation**:
- Scaffolding: Explainer before Challenger
- Accessible roles (Summarizer, Example-Generator) always present
- Error prevention via Misconception-Spotter

### 3. Stability Over Reactivity

**Principle**: Prevent oscillation; gradual adaptation over instant response.

**Implementation**:
- Bounded transition delays (2-3 turns minimum)
- Hysteresis windows (5-10 step cooldown)
- Role usage penalties

### 4. Auditability

**Principle**: Every state transition must be logged and traceable.

**Implementation**:
- Comprehensive session history
- Metadata for every turn
- Reallocation events logged with justification

### 5. Modularity

**Principle**: Each component has a single responsibility with clear interfaces.

**Implementation**:
- 7 independent modules
- Well-defined input/output contracts
- Testable in isolation

---

## System Components

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                       │
│                    (Optional Web/CLI)                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                        API LAYER                            │
│         /upload_document /start_session /next /interrupt   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   DIALOGUE ORCHESTRATOR                     │
│           (Main Controller - Coordinates All Modules)       │
└────┬─────────┬─────────┬─────────┬─────────┬──────────┬────┘
     │         │         │         │         │          │
     ▼         ▼         ▼         ▼         ▼          ▼
┌────────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌───────────┐
│Module 1│ │Mod 2 │ │Mod 3 │ │Mod 4 │ │Mod 5 │ │  Mod 6+7  │
│Document│ │Role  │ │Role  │ │RQSM  │ │Inter │ │Realloc +  │
│Process │ │Templ │ │Assign│ │State │ │ruption│ │ Session   │
│        │ │      │ │      │ │Mach. │ │Monitor│ │           │
└────┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └─────┬─────┘
     │        │        │        │        │            │
     │        └────────┴────────┴────────┴────────────┘
     │                         │
     ▼                         ▼
┌─────────────────┐   ┌──────────────────┐
│   LLM CLIENT    │   │   DATA STORE     │
│  (OpenAI API)   │   │ (Session State)  │
└─────────────────┘   └──────────────────┘
```

### Core Modules

#### Module 1: Document Processor
**Purpose**: Transform raw documents into semantic units

**Inputs**:
- Raw document (PDF, TXT)

**Outputs**:
- List of semantic units with metadata

**Key Algorithms**:
- Heading detection (regex)
- Paragraph grouping (semantic similarity)
- Cohesion scoring

#### Module 2: Role Template System
**Purpose**: Define role behaviors and characteristics

**Inputs**:
- None (static definitions)

**Outputs**:
- Role objects with prompts and weights

**Key Components**:
- Behavioral templates
- Priority weights
- Trigger conditions

#### Module 3: Role Assignment Engine
**Purpose**: Compute deterministic role queues

**Inputs**:
- Semantic unit
- Role templates

**Outputs**:
- Ordered role queue with scores

**Key Algorithms**:
- Structural scoring
- Lexical coherence analysis
- Topic similarity matching

#### Module 4: Role Queue State Machine (RQSM)
**Purpose**: Orchestrate role transitions

**Inputs**:
- Current state
- Role queue
- Interruption signals

**Outputs**:
- Next role to speak
- Updated state

**Key Components**:
- State tracker
- Transition logic
- Bounded delay controller

#### Module 5: Interruption Monitor
**Purpose**: Detect and classify user interruptions

**Inputs**:
- User input text

**Outputs**:
- Intent classification
- Confidence score

**Key Algorithms**:
- Keyword pattern matching
- Intent classification
- Confidence thresholding

#### Module 6: Role Reallocation Engine
**Purpose**: Dynamically reorder role queues

**Inputs**:
- Current queue
- Detected intent
- Usage history

**Outputs**:
- Reordered role queue
- New priorities

**Key Algorithms**:
- Intent-role alignment scoring
- Recent usage penalty
- Stability enforcement

#### Module 7: Session Continuity Manager
**Purpose**: Maintain context across long interactions

**Inputs**:
- Session history
- Current turn

**Outputs**:
- Context-injected prompts
- Updated history

**Key Components**:
- History storage
- Context retrieval
- Contradiction detection

---

## Data Flow Architecture

### Primary Flow (No Interruptions)

```
1. USER UPLOADS DOCUMENT
   ↓
2. Document Processor → Semantic Units [S1, S2, ..., Sn]
   ↓
3. For each Si:
   Role Assignment Engine → Role Queue [R1, R2, R3, R4, R5]
   ↓
4. RQSM initializes:
   - current_segment = S1
   - current_index = 0
   - current_role = R1
   ↓
5. LOOP (while not complete):
   a. Get current role's prompt template
   b. LLM Client generates response
   c. Session Manager logs turn
   d. RQSM transitions to next role
   e. If queue complete → next segment
   ↓
6. DIALOGUE COMPLETE
```

### Interruption Flow

```
1. USER INTERRUPTS (during normal flow)
   ↓
2. Interruption Monitor classifies intent
   ↓
3. IF confidence >= 0.7:
   a. Role Reallocation Engine recomputes priorities
   b. RQSM updates role queue
   c. Apply bounded delay + hysteresis
   d. Resume from new role
   ELSE:
   Continue with current queue
```

### Data Structures

#### Semantic Unit
```python
{
    "id": "S1",
    "title": "Introduction: The Problem",
    "text": "Most students study alone...",
    "document_section": "introduction",
    "similarity_score": 0.92,
    "position": 0
}
```

#### Role Queue
```python
{
    "segment_id": "S1",
    "queue": ["Summarizer", "Explainer", "Challenger", "Example-Generator", "Misconception-Spotter"],
    "scores": {
        "Summarizer": 8.7,
        "Explainer": 8.2,
        "Challenger": 6.5,
        "Example-Generator": 7.1,
        "Misconception-Spotter": 7.8
    }
}
```

#### Dialogue State
```python
{
    "current_segment": "S1",
    "current_index": 2,
    "current_role": "Challenger",
    "role_queue": ["Summarizer", "Explainer", "Challenger", "Example-Generator", "Misconception-Spotter"],
    "interruption_detected": False,
    "transition_lock": 0.0,
    "hysteresis_map": {"Example-Generator": 10},
    "history_pointer": 15
}
```

#### Session History Entry
```python
{
    "turn": 3,
    "segment": "S1",
    "role": "Challenger",
    "message": "But what if the assumption doesn't hold...",
    "timestamp": 1234567950,
    "user_intent": None,
    "is_reallocation": False,
    "metadata": {
        "role_score": 6.5,
        "llm_tokens": 127
    }
}
```

---

## Module Interactions

### Sequence Diagram: Normal Operation

```
User → API: Upload Document
API → DocProcessor: process(document)
DocProcessor → API: [S1, S2, S3]

User → API: Start Session
API → RoleAssignment: assign_roles([S1, S2, S3])
RoleAssignment → API: {S1: [R1, R2], S2: [R3, R4], ...}

API → RQSM: initialize(S1, [R1, R2])
RQSM → LLMClient: generate(R1.prompt, S1.text)
LLMClient → RQSM: response
RQSM → SessionManager: log_turn(response)
RQSM → API: turn_complete

[Loop for each role in queue]

User → API: Next
API → RQSM: advance()
RQSM → LLMClient: generate(R2.prompt, S1.text)
...
```

### Sequence Diagram: Interruption Handling

```
User → API: Interrupt("Give me an example")
API → InterruptionMonitor: classify("Give me an example")
InterruptionMonitor → API: (intent="Example Request", confidence=0.92)

API → RoleReallocation: reorder_queue(
    current_queue=[R1, R2, R3],
    intent="Example Request"
)
RoleReallocation → API: new_queue=[Example-Generator, R1, R2]

API → RQSM: update_queue(new_queue)
RQSM → RQSM: apply_bounded_delay()
RQSM → RQSM: update_hysteresis_map()

[Wait 2-3 turns]

RQSM → LLMClient: generate(Example-Generator.prompt, context)
...
```

---

## Technology Stack

### Backend Framework
- **Python 3.10+**
- **FastAPI** - Modern, fast web framework
- **Pydantic** - Data validation

### Document Processing
- **pdfplumber** - PDF text extraction
- **sentence-transformers** - Semantic embeddings
- **regex** - Heading detection

### LLM Integration
- **OpenAI API** (gpt-3.5-turbo or gpt-4)
- **Temperature = 0.0** for determinism
- **Alternative**: HuggingFace Transformers

### Data Storage
- **SQLite** (MVP) - Session persistence
- **In-memory structures** - Active state
- **Future**: PostgreSQL for production

### Testing
- **pytest** - Unit and integration tests
- **pytest-asyncio** - Async test support

### Development Tools
- **black** - Code formatting
- **mypy** - Static type checking
- **flake8** - Linting

---

## Design Patterns

### 1. State Pattern
**Applied to**: RQSM (Module 4)

**Rationale**: Role queue transitions are state-driven

**Implementation**:
```python
class DialogueState:
    def advance(self) -> Optional[Role]:
        # State transition logic
        pass
    
    def handle_interruption(self, intent: Intent) -> None:
        # Interruption-specific transition
        pass
```

### 2. Strategy Pattern
**Applied to**: Role Assignment (Module 3)

**Rationale**: Different scoring strategies for different document types

**Implementation**:
```python
class ScoringStrategy(ABC):
    def score(self, role: Role, segment: SemanticUnit) -> float:
        pass

class StructuralScorer(ScoringStrategy): ...
class LexicalScorer(ScoringStrategy): ...
```

### 3. Observer Pattern
**Applied to**: Interruption Monitor (Module 5)

**Rationale**: Multiple components need to react to interruptions

**Implementation**:
```python
class InterruptionObserver(ABC):
    def on_interruption(self, intent: Intent) -> None:
        pass

class RQSM(InterruptionObserver): ...
class SessionManager(InterruptionObserver): ...
```

### 4. Template Method Pattern
**Applied to**: Role Templates (Module 2)

**Rationale**: Shared role behavior with role-specific customization

**Implementation**:
```python
class Role(ABC):
    def generate_response(self, context: Context) -> str:
        prompt = self.build_prompt(context)  # Template method
        return llm_client.generate(prompt)
    
    @abstractmethod
    def build_prompt(self, context: Context) -> str:
        pass
```

### 5. Chain of Responsibility
**Applied to**: Intent Classification (Module 5)

**Rationale**: Multiple classifiers can handle intent detection

**Implementation**:
```python
class IntentClassifier(ABC):
    def __init__(self, next_classifier: Optional['IntentClassifier'] = None):
        self.next = next_classifier
    
    def classify(self, text: str) -> Optional[Intent]:
        result = self._try_classify(text)
        if result is None and self.next:
            return self.next.classify(text)
        return result
```

---

## Scalability Considerations

### Current MVP Limitations
- Single-user, single-session
- In-memory state management
- No caching
- No load balancing

### Future Enhancements
1. **Multi-User Support**
   - Session-based architecture
   - User authentication
   - Concurrent session handling

2. **Performance Optimization**
   - LLM response caching
   - Semantic unit precomputation
   - Async role generation

3. **Distributed Architecture**
   - Microservices for modules
   - Message queue (RabbitMQ/Kafka)
   - Distributed state management (Redis)

---

## Security Considerations

### Current State (MVP)
- **No authentication** (trusted users only)
- **No input sanitization**
- **API keys in .env file**

### Production Requirements
1. **Authentication & Authorization**
   - JWT-based auth
   - Role-based access control

2. **Input Validation**
   - Sanitize document uploads
   - Rate limiting
   - Size limits

3. **Secrets Management**
   - Environment-specific configs
   - Encrypted credentials
   - Key rotation

---

## Monitoring & Observability

### Logging Strategy
```python
# Structured logging
logger.info(
    "role_transition",
    segment=state.current_segment,
    from_role=state.current_role,
    to_role=next_role,
    trigger="normal" | "interruption"
)
```

### Metrics to Track
- Average dialogue length
- Role distribution per segment
- Interruption frequency
- Reallocation events
- LLM token usage
- Response time

### Debug Mode
- Full state dumps at each transition
- Role score breakdowns
- Intent classification details

---

## Conclusion

This architecture provides a **modular, deterministic, and pedagogically grounded** foundation for multi-role conversational learning. The design prioritizes:

1. **Determinism** - Reproducible outputs
2. **Stability** - No oscillation
3. **Auditability** - Full traceability
4. **Modularity** - Testable components

The MVP implementation (40-50% of full design) focuses on core functionality while maintaining architectural integrity for future expansion.
