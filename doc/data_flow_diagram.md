# DATA FLOW DIAGRAM (DFD LEVEL 0 & 1)
## Five-Process Model with External Entities and Data Stores

> **Maps to Modules**: Document Processing (M1), Role Assignment (M3), RQSM (M4), Interruption Detection (M5), Role Reallocation (M6)

> **See Also**: [Module Specifications](doc/03_MODULE_SPECIFICATIONS.md) for detailed algorithms

## LEVEL 0: CONTEXT DIAGRAM
```
                              ┌─────────────────────────────┐
                              │    STUDY DIALOGUE SYSTEM    │
                              │   (Black Box View)          │
                              └─────────────────────────────┘
                                      │         │
        ┌─────────────────────────────┼─────────┼────────────────────────┐
        │                             │         │                        │
        ▼                             ▼         ▼                        ▼
    ┌────────┐          ┌──────────┐ ┌──────────────┐          ┌─────────────┐
    │ LEARNER│          │   LLM    │ │  DATABASE    │          │  INSTRUCTOR │
    │        │          │ SERVICE  │ │  (SQLite/    │          │  (Optional) │
    │Input:  │          │          │ │   PostgreSQL)│          │             │
    │ Doc    │ Output:  │Input:    │ │Input: State  │          │Input:Config │
    │ Query  │ Response │ Prompt   │ │Output:Context│          │Output:Rules │
    └────────┘          │          │ │              │          └─────────────┘
                        └──────────┘ └──────────────┘

```

## LEVEL 1: DETAILED DATA FLOW DIAGRAM

```
┌────────────┐
│  LEARNER   │
│            │
│ Inputs:    │
│ • Document │
│ • Query    │
│ • Interrupt│
└─────┬──────┘
      │
      │ Document (PDF/Text)
      ├─────────────────────────────────────────────────────┐
      │                                                     │
      ▼                                                     ▼
 ┌─────────────────────┐                          ┌──────────────────────┐
 │ 1.0 DOCUMENT        │                          │ 4.0 INTERRUPTION     │
 │ PROCESSING          │                          │ DETECTION            │
 │                     │                          │                      │
 │ • Extract text      │                          │ • Monitor user input │
 │ • Detect structure  │                          │ • Classify intent    │
 │ • Segment content   │                          │ • Score confidence   │
 │ • Compute cohesion  │                          │ • Log event          │
 │                     │                          │                      │
 └──────────┬──────────┘                          └────────┬─────────────┘
            │                                              │
            │ Semantic Units                               │ Intent Class
            │ [Unit ID, Text, Topic,                       │ [User Input,
            │  Coherence Score]                            │  Intent Type,
            │                                              │  Confidence]
            │                                              │
            ▼                                              ▼
 ┌─────────────────────┐                          ┌──────────────────────┐
 │ 2.0 ROLE ASSIGNMENT │                          │ 5.0 ROLE REALLOCATION│
 │ ENGINE              │                          │ ENGINE               │
 │                     │                          │                      │
 │ • Score units       │                          │ • Map intent→role    │
 │ • Rank roles        │                          │ • Rescore priority   │
 │ • Deterministic tie │                          │ • Reorder queue      │
 │   breaking          │                          │ • Validate stability │
 │ • Generate queue    │                          │                      │
 │                     │                          │                      │
 └──────────┬──────────┘                          └────────┬─────────────┘
            │                                              │
            │ Role Queue                                   │ Reallocation
            │ [Segment ID,                                 │ Command
            │  Role1, Role2,                               │ [New Role Order,
            │  Role3, ...]                                 │  Delay Applied,
            │                                              │  Hysteresis OK]
            │                                              │
            └──────────────────────┬───────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────────────┐
            │ 3.0 DIALOGUE ORCHESTRATION (RQSM)            │
            │                                              │
            │ • Retrieve current state                     │
            │ • Select current role                        │
            │ • Apply transition delay                     │
            │ • Prepare context window                     │
            │ • Format LLM query                           │
            │ • Parse LLM response                         │
            │ • Update role queue                          │
            │ • Log state transition                       │
            │                                              │
            └───────────┬─────────────────────────┬────────┘
                        │                         │
        ┌───────────────┘                         │
        │                                         │
        │ LLM Query                               │ State Update
        │ [Current Role,                          │ [Segment ID,
        │  Context,                               │  Role Index,
        │  User Input,                            │  Timestamp,
        │  Role Prompt]                           │  Transition Log]
        │                                         │
        ▼                                         │
    ┌────────────┐                               │
    │ LLM SERVICE│                               │
    │ (OpenAI/   │                               │
    │ HuggingFace)                               │
    │            │                               │
    └────────────┘                               │
        │                                         │
        │ LLM Response                            │
        │ [Role Output,                           │
        │  Confidence,                            │
        │  Metadata]                              │
        │                                         │
        └──────────────────┬──────────────────────┘
                           │
                           ▼
            ┌──────────────────────────────────┐
            │ SESSION CONTINUITY MANAGER       │
            │                                  │
            │ • Store state update             │
            │ • Update context summary         │
            │ • Maintain history index         │
            │ • Track continuity pointer       │
            │ • Prevent contradictions         │
            │ • Manage session persistence     │
            │                                  │
            └───────────┬──────────┬───────────┘
                        │          │
        ┌───────────────┘          │
        │                          │
        │ Session State            │ Context
        │ [User ID,                │ Retrieved
        │  Session ID,             │ [History,
        │  Document ID,            │  Summary,
        │  Conversation Log]       │  Pointers]
        │                          │
        ▼                          │
    ┌─────────────┐               │
    │  DATABASE   │◄──────────────┘
    │ (SQLite/    │
    │ PostgreSQL) │
    │             │
    │ STORES:     │
    │ • Documents │
    │ • Sessions  │
    │ • States    │
    │ • Roles     │
    │ • History   │
    └─────────────┘
        │
        │ Conversation Output
        │ [Dialogue Turn,
        │  Role,
        │  Response,
        │  Metadata]
        │
        ▼
    ┌─────────────────────────┐
    │    LEARNER (OUTPUT)     │
    │                         │
    │ Receives:               │
    │ • Role response         │
    │ • Context cues          │
    │ • Visual indicators     │
    │ • Session history       │
    │ • Export options        │
    └─────────────────────────┘
```

---

## DATA DICTIONARY

### PROCESS 1.0: DOCUMENT PROCESSING
**Inputs:**
- Raw Document: PDF, TXT, HTML file
- Processing Rules: Segmentation threshold, max unit length

**Outputs:**
- Semantic Units: Array of [Unit_ID, Text, Topic, Coherence_Score, Position]
- Document Metadata: [Doc_ID, Title, Domain, Total_Units, Processed_Timestamp]

**Processing Logic:**
1. Extract text from document (remove formatting)
2. Normalize and clean text
3. Detect structural headings
4. Group paragraphs into units
5. Compute semantic cohesion scores
6. Assign unique IDs to each unit

---

### PROCESS 2.0: ROLE ASSIGNMENT ENGINE
**Inputs:**
- Semantic Units: Array of segmented document pieces
- Role Templates: 5 role definitions with behavioral specs
- Scoring Weights: α (structure), β (lexical), γ (similarity)

**Outputs:**
- Role Queues: For each semantic unit, ordered list of [Role_1, Role_2, ..., Role_5]
- Assignment Metadata: [Segment_ID, Scores_Per_Role, Determinism_Check]

**Processing Logic:**
```
For each Semantic Unit (S_i):
    For each Role (R):
        RoleScore(R, S_i) = 0.4*structural_score + 0.3*lexical_coherence + 0.3*topic_similarity
    Sort roles by RoleScore (descending)
    Apply deterministic tie-breaking (use role_id as tiebreaker)
    Output: RoleQueue[S_i] = [Top 5 roles in sorted order]
    
Reproducibility Check:
    Run assignment twice on identical input
    Assert RoleQueue_Run1 == RoleQueue_Run2 (100% reproducibility)
```

---

### PROCESS 3.0: DIALOGUE ORCHESTRATION (RQSM)
**Inputs:**
- Role Queue: [Role_1, Role_2, ..., Role_N] for current segment
- Current State: {Segment_ID, Role_Index, Continuity_Pointer, Timestamp}
- User Context: Previous turns, session history, user profile
- LLM Response: Parsed output from language model

**Outputs:**
- Conversation Output: [Role_Name, Response_Text, Metadata]
- State Update: [New_Segment_ID, New_Role_Index, New_Timestamp, Transition_Log]
- Next State: Ready for subsequent turn

**State Machine Logic:**
```
Current_State = {segment_id, role_index, timestamp}

ON_NEW_TURN:
    1. Retrieve_State(session_id)
    2. current_role = RoleQueue[segment_id][role_index]
    3. Check_Transition_Lock(decrement if >0, skip if locked)
    4. context = Build_Context_Window(history, summary, continuity_pointer)
    5. prompt = Format_Role_Prompt(current_role, context, user_input)
    6. response = Query_LLM(prompt)
    7. Log_Transition(current_state, next_state)
    8. Save_State(new_state)
    9. Return response to learner

NEXT_ROLE_TRANSITION:
    Advance role_index: role_index = (role_index + 1) % len(RoleQueue)
    Check if next segment should be engaged
```

---

### PROCESS 4.0: INTERRUPTION DETECTION
**Inputs:**
- User Input: Any text input from learner
- Intent Keywords: Pre-defined patterns for 5+ intent types
- Current Context: Segment, role, conversation state

**Outputs:**
- Intent Classification: [Intent_Type, Confidence_Score, User_Input_Text]
- Interruption Event: Logged for audit trail

**Intent Categories:**
| Intent Type | Keywords | Confidence Threshold |
|---|---|---|
| Clarification Request | "explain", "clarify", "what do you mean" | 0.6 |
| Objection | "disagree", "but", "no", "wrong" | 0.65 |
| Depth Request | "deeper", "more detail", "why" | 0.6 |
| Topic Pivot | "different topic", "change", "instead" | 0.7 |
| Example Request | "example", "like what", "show me" | 0.6 |

---

### PROCESS 5.0: ROLE REALLOCATION ENGINE
**Inputs:**
- Intent Classification: [Intent_Type, Confidence]
- Current Role Queue: [Role_1, ..., Role_N]
- Intent-to-Role Mapping: Domain-specific rules

**Outputs:**
- Reallocation Command: [New_Role_Order, Delay_Applied, Stability_Check_Passed]
- Updated Queue: Reordered role sequence

**Reallocation Logic:**
```
IF confidence_score >= 0.7 AND hysteresis_window_expired:
    new_role_priority = Map_Intent_To_Role(intent_type)
    new_queue = Reorder_Queue(current_queue, new_role_priority)
    
    IF Stability_Check(new_queue):
        Apply_Bounded_Delay(3 turns minimum)
        Apply_Hysteresis(demoted roles blocked for 7 turns)
        Update_Role_Queue(new_queue)
        Log_Reallocation_Event()
    ELSE:
        Reject reallocation
        Maintain current queue
```

---

## DATA STORES

### D1: DOCUMENT STORE
```
Documents Table:
- document_id (PK)
- user_id (FK)
- filename
- content (raw text)
- domain
- processed_timestamp
- num_segments
```

### D2: SESSION STATE STORE
```
Sessions Table:
- session_id (PK)
- user_id (FK)
- document_id (FK)
- start_time
- current_segment_id
- current_role_index
- continuity_pointer
- last_update_timestamp

Conversation_History Table:
- turn_id (PK)
- session_id (FK)
- role_id
- user_input
- role_response
- timestamp
- state_after_turn (JSON)
```

### D3: ROLE TEMPLATES STORE
```
Roles Table:
- role_id (PK)
- role_name
- behavioral_template
- system_prompt
- role_description
- learning_science_grounding
- priority_weight
```

### D4: INTERRUPTION LOG STORE
```
Interruption_Events Table:
- event_id (PK)
- session_id (FK)
- user_input
- detected_intent
- confidence_score
- reallocation_applied
- timestamp
```

---

## CRITICAL DATA FLOWS AND TIMING

| Flow | Source | Destination | Data | Frequency | Latency Requirement |
|---|---|---|---|---|---|
| Document Load | Learner | Document Processing | Raw File | 1x per session | <5s total |
| Segment Data | Doc Processing | Role Assignment | Semantic Units | 1x per document | <2s |
| Role Queue | Role Assignment | Dialogue Orch. | Ordered Roles | 1x per segment | <0.1s |
| Intent | Interruption Detect | Role Reallocation | Intent+Confidence | Per user input | <0.5s |
| State Update | Dialogue Orch. | Session Manager | State JSON | Every turn | <0.1s |
| Context | Session Manager | Dialogue Orch. | History+Summary | Per turn | <0.2s |
| LLM Query | Dialogue Orch. | LLM Service | Prompt | Per turn | <3s |
| LLM Response | LLM Service | Session Manager | Output | Per turn | Model latency |
| Persistence | Session Manager | Database | Session State | Every turn | <1s |
| History Retrieval | Database | Session Manager | Conversation Log | Session resume | <0.5s |

