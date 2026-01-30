# SYSTEM ARCHITECTURE DIAGRAM
## Document-Segment Driven Role-Oriented Conversational Study System

> **Aligns with**: [Project Architecture](doc/01_PROJECT_ARCHITECTURE.md) | [Module Specifications](doc/03_MODULE_SPECIFICATIONS.md)

> **Core Modules**: 7 functional modules implementing the RQSM-Engine

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             INPUT LAYER                                      │
├────────────────────────────────────┬──────────────────────────────────────────┤
│    Document Input                  │         User Input                       │
│  (PDF/TXT/HTML)                    │   (Query/Interruption)                   │
└────────────────┬───────────────────┴──────────────────────┬───────────────────┘
                 │                                          │
                 ▼                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PROCESSING LAYER                                    │
├──────────────────────────┬──────────────────────┬─────────────────────────────┤
│ Document Processing      │ Role Template        │ Role Assignment Engine      │
│ Module                   │ System               │                             │
│                          │                      │                             │
│ • Text extraction        │ • Explainer          │ • Scoring function          │
│ • Heading detection      │ • Challenger         │ • Deterministic ranking     │
│ • Paragraph grouping     │ • Summarizer         │ • Queue generation          │
│ • Cohesion analysis      │ • Example-Generator  │ • Reproducibility check     │
│ • Semantic segmentation  │ • Misconception-     │                             │
│                          │   Spotter            │                             │
└──────────┬───────────────┴──────────┬───────────┴────────────┬────────────────┘
           │ Semantic Units           │                        │
           │                          │ Role Definitions       │
           └──────────────────────────┼────────────────────────┤
                                      ▼ Scored Role Queue      │
┌─────────────────────────────────────────────────────────────┴──────────────┐
│                      ORCHESTRATION LAYER                                     │
├────────────────┬─────────────────────────────┬───────────────────────────────┤
│ Interruption   │ Role Queue State Machine    │ Role Reallocation Engine      │
│ Monitor        │ (RQSM)                      │                              │
│                │                             │                              │
│ • Intent       │ • Current state tracking    │ • Intent-to-role mapping     │
│   detection    │ • Bounded delays            │ • Priority re-scoring        │
│ • 5+ intent    │ • Hysteresis window         │ • Queue reordering           │
│   categories   │ • State logging             │ • Stability validation       │
│ • Confidence   │ • Transition management     │ • Delay application          │
│   scoring      │ • Auditability              │                              │
└────────┬───────┴────────────┬────────────────┴────────┬─────────────────────┘
         │ Intent Class       │ State Updates          │ Updated Queue
         │                    │                        │
         └────────────────────┼────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DIALOGUE & PERSISTENCE LAYER                              │
├────────────────────┬──────────────────────────┬────────────────────────────┤
│ Session Continuity │ LLM API Adapter          │ Context & History Manager  │
│ Manager            │                          │                            │
│                    │ • OpenAI integration     │ • Continuity pointers      │
│ • Session tracking │ • HuggingFace support    │ • Context summarization    │
│ • History mgmt     │ • Prompt templating      │ • Contradiction prevention │
│ • Context mgt      │ • Response parsing       │ • History indexing         │
│ • Persistence      │ • Context windowing      │ • Session recovery         │
└────────┬───────────┴──────────┬───────────────┴────────────┬────────────────┘
         │                      │ Query + Context            │
         │                      ▼                            │
         │          ┌──────────────────────┐                 │
         │          │   LLM SERVICE        │                 │
         │          │ (OpenAI/HuggingFace) │                 │
         │          │                      │                 │
         │          └──────────────────────┘                 │
         │                      ▲                            │
         │           LLM Response + Role Output              │
         │                      │                            │
         └──────────────────────┼────────────────────────────┘
                                │
┌───────────────────────────────┴──────────────────────────────────────────────┐
│                       PERSISTENCE LAYER                                      │
├────────────────────────────────────────────────────────────────────────────┤
│                         DATABASE (SQLite/PostgreSQL)                        │
│                                                                             │
│  • Session history    • Role queue states      • User interactions         │
│  • Documents         • Interruption logs       • Conversation transcripts  │
│  • Roles metadata    • State transitions       • Context summaries         │
└─────────────────────────────────────────────────────────────────────────────┘
         ▲
         │ Session State / History Retrieval
         │
┌────────┴──────────────────────────────────────────────────────────────────────┐
│                           OUTPUT LAYER                                        │
├─────────────────────────────────┬──────────────────────────────────────────────┤
│    Conversation Output           │      Session Export                         │
│  (Real-time dialogue)            │   (JSON/PDF/Plaintext)                      │
└─────────────────────────────────┴──────────────────────────────────────────────┘
```

## KEY ARCHITECTURAL PRINCIPLES

### 1. **Layered Architecture**
- **Input Layer**: Accepts documents and user interactions
- **Processing Layer**: Transforms raw documents into semantic units; assigns roles deterministically
- **Orchestration Layer**: Manages state transitions, intent-driven reallocations, stability
- **Persistence Layer**: Maintains session continuity and conversation history
- **Output Layer**: Delivers results to learner

### 2. **Core Design Patterns**
- **State Machine Pattern**: RQSM ensures reproducible, auditable role sequencing
- **Strategy Pattern**: Role templates enable pluggable behavioral definitions
- **Adapter Pattern**: LLM API abstraction supports multiple language models
- **Observer Pattern**: Interruption monitor detects user intent changes

### 3. **Critical Data Flows**
| Source → Destination | Data | Purpose |
|---|---|---|
| Document Processing → Role Assignment | Semantic Units | Enable role-specific scoring |
| Role Assignment → RQSM | Role Queue | Provide ordered role sequence |
| Interruption Monitor → Role Reallocation | Intent Class | Trigger dynamic role reordering |
| RQSM → LLM Adapter | Current Role + Context | Generate role-specific response |
| Session Manager → Database | State Update | Persist conversation state |
| Database → Session Manager | Context Retrieved | Restore continuity across sessions |

### 4. **Stability Mechanisms**
- **Bounded Transition Delays**: Prevent rapid oscillation between roles (3 turn minimum delay)
- **Hysteresis Window**: Block demoted roles for 7 turns after demotion
- **Reallocation Threshold**: Confidence must exceed 0.7 to trigger role reallocation
- **State Logging**: Full auditability of all transitions for reproducibility verification

### 5. **LLM-Agnostic Integration**
The LLM API Adapter abstracts the underlying language model, supporting:
- OpenAI GPT-3.5/GPT-4
- HuggingFace Transformers (Llama, Mistral, etc.)
- Any REST-based LLM service

Role-specific prompt templates ensure consistent behavior across models.

