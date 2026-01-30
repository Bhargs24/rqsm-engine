# UML CLASS DIAGRAM
## 15 Classes Across 6 Functional Layers

> **Implements**: 7 Core Modules from [Module Specifications](doc/03_MODULE_SPECIFICATIONS.md)

> **Architecture**: See [Project Architecture](doc/01_PROJECT_ARCHITECTURE.md) for system design

## COMPLETE CLASS STRUCTURE

```
╔════════════════════════════════════════════════════════════════════════════╗
║                        CORE ENTITY CLASSES (Layer 1)                       ║
╚════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────┐
│      Document            │
├──────────────────────────┤
│ - id: String (PK)        │
│ - content: String        │
│ - title: String          │
│ - domain: String         │
│ - upload_timestamp: DT   │
│ - segments: List<SU>     │
│ - metadata: Map          │
├──────────────────────────┤
│ + parse(): void          │
│ + segment(): void        │
│ + export(): String       │
│ + validate(): Boolean    │
└─────────────┬────────────┘
              │ 1:Many composition
              ▼
┌──────────────────────────┐       ┌──────────────────────────┐
│   SemanticUnit           │       │      Role                │
├──────────────────────────┤       ├──────────────────────────┤
│ - id: String (PK)        │       │ - id: String (PK)        │
│ - document_id: FK        │       │ - name: String           │
│ - text: String           │       │ - description: String    │
│ - start_pos: Integer     │       │ - behavioral_template: S │
│ - end_pos: Integer       │       │ - system_prompt: String  │
│ - topic: String          │       │ - priority_weight: Float │
│ - coherence_score: Float │       │ - learning_science_basis │
│ - content_hash: String   │       ├──────────────────────────┤
├──────────────────────────┤       │ + execute(ctx): String   │
│ + compute_similarity():  │       │ + score_unit(su): Float  │
│   Float                  │       │ + validate_prompt(): Boo │
│ + get_metadata(): Map    │       │ + get_template(): String │
│ + to_json(): String      │       └──────────────────────────┘
└──────────────┬───────────┘
               │ 1:1 association
               ▼
┌──────────────────────────┐
│    RoleQueue             │
├──────────────────────────┤
│ - id: String (PK)        │
│ - segment_id: FK         │
│ - roles: List<Role>      │
│ - queue_order: List<Int> │
│ - created_timestamp: DT  │
│ - modified_timestamp: DT │
├──────────────────────────┤
│ + add_role(r: Role): v   │
│ + remove_role(id): v     │
│ + reorder(new_order): v  │
│ + get_current_role(): Ro │
│ + peek_next(): Role      │
│ + advance(): void        │
└──────────────────────────┘


╔════════════════════════════════════════════════════════════════════════════╗
║               STATE MACHINE & ORCHESTRATION CLASSES (Layer 2)              ║
╚════════════════════════════════════════════════════════════════════════════╝

┌────────────────────────────────────────┐
│  RoleQueueStateMachine (RQSM)          │
├────────────────────────────────────────┤
│ - current_state: State                 │
│ - state_log: List<StateTransition>     │
│ - state_index: Integer                 │
│ - transition_delay: Integer = 3        │
│ - hysteresis_window: Integer = 7       │
│ - last_transition: DateTime            │
│ - stability_enabled: Boolean           │
├────────────────────────────────────────┤
│ + transition(new_state): Boolean       │
│ + log_state(s: State): void            │
│ + validate_state(s: State): Boolean    │
│ + apply_delay(): void                  │
│ + check_hysteresis(): Boolean          │
│ + get_state_log(): List<ST>            │
│ + ensure_stability(): Boolean          │
│ + export_audit_trail(): JSON           │
└──────────────┬────────────────────────┘
               │ tracks 1:1
               ▼
┌────────────────────────────────────────┐
│         State                          │
├────────────────────────────────────────┤
│ - state_id: String (PK)                │
│ - segment_id: String                   │
│ - role_index: Integer                  │
│ - role_id: String                      │
│ - continuity_pointer: String           │
│ - timestamp: DateTime                  │
│ - context_hash: String                 │
│ - user_input_hash: String              │
│ - transition_reason: String            │
├────────────────────────────────────────┤
│ + update(): void                       │
│ + serialize(): JSON                    │
│ + deserialize(json): State             │
│ + validate_consistency(): Boolean      │
│ + get_context_for_role(): String       │
└────────────────────────────────────────┘


╔════════════════════════════════════════════════════════════════════════════╗
║                      ENGINE CLASSES (Layer 3)                              ║
╚════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────┐
│  RoleAssignmentEngine                   │
├─────────────────────────────────────────┤
│ - scoring_weights: Map<String, Float>   │
│   α (structural): 0.4                   │
│   β (lexical): 0.3                      │
│   γ (topic): 0.3                        │
│ - role_templates: List<Role>            │
│ - similarity_threshold: Float = 0.6     │
│ - determinism_checks: Boolean = true    │
├─────────────────────────────────────────┤
│ + compute_score(r: Role, s: SU): Float │
│ + assign_roles(segments): RoleQueues    │
│ + ensure_determinism(): Boolean         │
│ + rank_roles(roles): List<Role>         │
│ + apply_tie_breaking(equal): Role       │
│ + validate_scoring(): Boolean           │
│ + export_score_report(): JSON           │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  RoleReallocationEngine                 │
├─────────────────────────────────────────┤
│ - intent_mapping: Map<Intent, Role>     │
│ - priority_rules: List<Rule>            │
│ - reallocation_log: List<Event>         │
│ - stability_threshold: Float = 0.7      │
│ - max_realloc_per_turn: Integer = 2     │
├─────────────────────────────────────────┤
│ + reorder_queue(intent): RoleQueue      │
│ + apply_intent(ic): Command             │
│ + validate_stability(): Boolean         │
│ + compute_new_priority(): Map           │
│ + apply_hysteresis(old, new): Boo       │
│ + log_reallocation(): void              │
│ + get_confidence_score(): Float         │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  DocumentProcessorEngine                │
├─────────────────────────────────────────┤
│ - text_extractor: TextExtractor         │
│ - similarity_threshold: Float = 0.6     │
│ - max_unit_length: Integer = 1000       │
│ - min_unit_length: Integer = 50         │
│ - embedding_model: String               │
├─────────────────────────────────────────┤
│ + extract_text(doc): String             │
│ + detect_headings(text): List<Heading>  │
│ + compute_cohesion(sents): Float        │
│ + segment_document(): List<SU>          │
│ + normalize_text(): String              │
│ + validate_segments(): Boolean          │
│ + export_segments_json(): JSON          │
└─────────────────────────────────────────┘


╔════════════════════════════════════════════════════════════════════════════╗
║               SESSION MANAGEMENT CLASSES (Layer 4)                         ║
╚════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────┐
│         Session                          │
├──────────────────────────────────────────┤
│ - id: String (PK)                        │
│ - user_id: String (FK)                   │
│ - document_id: String (FK)               │
│ - start_time: DateTime                   │
│ - end_time: DateTime (nullable)          │
│ - status: String (active/paused/end)     │
│ - conversation_history: List<Turn>       │
│ - metadata: Map                          │
├──────────────────────────────────────────┤
│ + save(): void                           │
│ + load(session_id): Session              │
│ + export(format): String                 │
│ + pause(): void                          │
│ + resume(): void                         │
│ + close(): void                          │
│ + get_duration(): Long                   │
│ + get_turn_count(): Integer              │
└────────────┬───────────────────────────┘
             │ 1:Many
             ▼
┌──────────────────────────────────────────┐
│      ContinuityManager                   │
├──────────────────────────────────────────┤
│ - continuity_pointers: Map               │
│ - context_summary: String                │
│ - history_index: Integer                 │
│ - max_context_window: Integer = 4096     │
│ - summary_algorithm: String              │
│ - compression_ratio: Float               │
├──────────────────────────────────────────┤
│ + track_position(seg_id): void           │
│ + summarize_context(): String            │
│ + retrieve_history(offset): List<Turn>   │
│ + compute_pointer(state): String         │
│ + prevent_contradiction(new): Boolean    │
│ + manage_window(turns): List<Turn>       │
│ + export_continuity_log(): JSON          │
│ + validate_consistency(): Boolean        │
└──────────────────────────────────────────┘


╔════════════════════════════════════════════════════════════════════════════╗
║          INTERRUPTION & INTENT HANDLING CLASSES (Layer 5)                  ║
╚════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────┐
│     IntentClassifier                     │
├──────────────────────────────────────────┤
│ - intent_categories: List<String>        │
│   • Clarification                        │
│   • Objection                            │
│   • Depth Request                        │
│   • Topic Pivot                          │
│   • Example Request                      │
│ - keyword_patterns: Map<Intent, Regex>   │
│ - confidence_thresholds: Map             │
│ - ml_model: Classifier (optional)        │
├──────────────────────────────────────────┤
│ + classify_intent(input): Intent         │
│ + confidence_score(intent): Float        │
│ + get_intent_keywords(): List<Str>       │
│ + validate_intent(): Boolean             │
│ + train_classifier(data): void           │
│ + export_model(): String                 │
└────────────┬───────────────────────────┘
             │ 1:Many uses
             ▼
┌──────────────────────────────────────────┐
│    InterruptionEvent                     │
├──────────────────────────────────────────┤
│ - event_id: String (PK)                  │
│ - session_id: String (FK)                │
│ - timestamp: DateTime                    │
│ - user_input: String                     │
│ - detected_intent: String                │
│ - confidence: Float                      │
│ - reallocation_applied: Boolean          │
│ - new_role_order: List<Role>             │
├──────────────────────────────────────────┤
│ + log_event(): void                      │
│ + get_intent_type(): String              │
│ + was_reallocation_applied(): Boolean    │
│ + export_event_data(): JSON              │
│ + validate_event(): Boolean              │
└──────────────────────────────────────────┘


╔════════════════════════════════════════════════════════════════════════════╗
║              LLM INTEGRATION CLASSES (Layer 6)                             ║
╚════════════════════════════════════════════════════════════════════════════╝

┌────────────────────────────────────────┐
│       LLMAdapter                       │
├────────────────────────────────────────┤
│ - api_key: String (env var)            │
│ - model_name: String                   │
│ - provider: String (openai/hf/other)   │
│ - role_templates: Map<Role, Template>  │
│ - context_window: Integer              │
│ - temperature: Float = 0.0             │
│ - max_tokens: Integer = 500            │
├────────────────────────────────────────┤
│ + query_llm(prompt): String            │
│ + format_prompt(role, ctx): String     │
│ + parse_response(response): JSON       │
│ + validate_response(): Boolean         │
│ + handle_context_overflow(): String    │
│ + switch_provider(new): void           │
│ + get_model_info(): JSON               │
└──────────────┬────────────────────────┘
               │ uses 1:Many
               ▼
┌────────────────────────────────────────┐
│    PromptTemplate                      │
├────────────────────────────────────────┤
│ - role: String                         │
│ - context_window: Integer              │
│ - system_prompt: String                │
│ - user_prompt_template: String         │
│ - examples: List<Example>              │
│ - output_format: String                │
│ - metadata: Map                        │
├────────────────────────────────────────┤
│ + render(context): String              │
│ + validate(): Boolean                  │
│ + inject_context(ctx): void            │
│ + export_template(): JSON              │
│ + import_template(json): void          │
│ + optimize_for_model(model): void      │
└────────────────────────────────────────┘


╔════════════════════════════════════════════════════════════════════════════╗
║                    CLASS RELATIONSHIPS SUMMARY                             ║
╚════════════════════════════════════════════════════════════════════════════╝

COMPOSITION (Strong Ownership - "has-a"):
├─ Document     1:Many──→ SemanticUnit
├─ RoleQueue    1:Many──→ Role
├─ RQSM         1:1─────→ State
├─ Session      1:Many──→ InterruptionEvent
├─ LLMAdapter   1:Many──→ PromptTemplate
└─ IntentClassifier 1:Many──→ (Keywords)

ASSOCIATION (Reference - "uses-a"):
├─ RoleAssignmentEngine ──uses──→ Role
├─ RoleAssignmentEngine ──uses──→ SemanticUnit
├─ RoleReallocationEngine ──uses──→ IntentClassifier
├─ RoleReallocationEngine ──updates──→ RoleQueue
├─ DocumentProcessorEngine ──generates──→ SemanticUnit
├─ ContinuityManager ──manages──→ Session
└─ LLMAdapter ──queries──→ (External LLM Service)

AGGREGATION (Weak Ownership):
├─ RoleQueue ──contains──→ Role (can exist independently)
└─ Session ──contains──→ InterruptionEvent (can exist independently)

INHERITANCE (if applicable):
├─ IntentClassifier ◄──extends── MLClassifier (optional advanced implementation)
└─ LLMAdapter ◄──adapts── (Implements LLMProvider interface)


╔════════════════════════════════════════════════════════════════════════════╗
║                      MULTIPLICITY REFERENCE                               ║
╚════════════════════════════════════════════════════════════════════════════╝

1:1     One-to-One (Each instance relates to exactly one other)
1:Many  One-to-Many (One instance can relate to many others)
*:*     Many-to-Many (Theoretically possible but not used in this design)

PK   = Primary Key (unique identifier)
FK   = Foreign Key (reference to another entity)
DT   = DateTime
Boo  = Boolean
V    = void (method returns nothing)
S    = String


╔════════════════════════════════════════════════════════════════════════════╗
║                    KEY DESIGN PATTERNS EMPLOYED                            ║
╚════════════════════════════════════════════════════════════════════════════╝

1. **STATE MACHINE PATTERN**
   - RQSM manages state transitions deterministically
   - Full audit trail via state_log
   - Ensures reproducibility and stability

2. **STRATEGY PATTERN**
   - Role defines behavioral strategies
   - Templates enable role-specific behavior without hardcoding
   - Roles can be swapped/reordered dynamically

3. **ADAPTER PATTERN**
   - LLMAdapter abstracts different LLM providers
   - Supports OpenAI, HuggingFace, or custom models
   - PromptTemplate adapts prompts for different roles

4. **OBSERVER PATTERN**
   - IntentClassifier detects user input changes
   - InterruptionEvent triggered on detection
   - RoleReallocationEngine reacts to interruption

5. **FAÇADE PATTERN**
   - Session acts as simplified interface to complex subsystems
   - ContinuityManager shields complexity of context management
   - DocumentProcessorEngine encapsulates parsing complexity

6. **FACTORY PATTERN**
   - RoleAssignmentEngine creates role queues
   - DocumentProcessorEngine creates semantic units
   - Ensures consistent object creation

```

---

## ATTRIBUTE AND METHOD REFERENCE

### Document Class
```java
public class Document {
    private String id;
    private String content;
    private String title;
    private String domain;
    private DateTime uploadTimestamp;
    private List<SemanticUnit> segments;
    private Map<String, Object> metadata;
    
    public void parse() { /* Extract and normalize text */ }
    public void segment() { /* Decompose into semantic units */ }
    public String export() { /* Export to JSON/PDF */ }
    public boolean validate() { /* Verify document integrity */ }
}
```

### RoleQueueStateMachine Class
```java
public class RoleQueueStateMachine {
    private State currentState;
    private List<StateTransition> stateLog;
    private int stateIndex;
    private int transitionDelay; // milliseconds
    private float hysteresisWindow; // seconds
    private DateTime lastTransition;
    
    public boolean transition(State newState) {
        /* 1. Validate new state
           2. Check hysteresis window
           3. Apply bounded delay
           4. Update state
           5. Log transition
           6. Return success flag */
    }
    
    public void logState(State s) {
        stateLog.add(new StateTransition(currentState, s));
        currentState = s;
    }
    
    public boolean validateState(State s) {
        /* Ensure state consistency and validity */
    }
    
    public List<StateTransition> getStateLog() {
        return stateLog;
    }
}
```

### IntentClassifier Class
```java
public class IntentClassifier {
    private List<String> intentCategories;
    private Map<String, Pattern> keywordPatterns;
    private Map<String, Float> confidenceThresholds;
    
    public Intent classifyIntent(String userInput) {
        /* 1. Apply regex patterns
           2. Compute confidence scores
           3. Return highest confidence intent
           4. If <threshold, return UNKNOWN */
    }
    
    public float confidenceScore(Intent intent) {
        /* Calculate semantic similarity and pattern match score */
    }
}
```

### RoleAssignmentEngine Class
```java
public class RoleAssignmentEngine {
    private Map<String, Float> scoringWeights;
    private List<Role> roleTemplates;
    
    public RoleQueue assignRoles(SemanticUnit segment) {
        List<Role> rankedRoles = new ArrayList<>();
        for (Role r : roleTemplates) {
            float score = computeScore(r, segment);
            rankedRoles.add(new RoleScorePair(r, score));
        }
        Collections.sort(rankedRoles);
        return new RoleQueue(segment.getId(), rankedRoles);
    }
    
    public float computeScore(Role r, SemanticUnit su) {
        float α = 0.4;  // structural weight
        float β = 0.3;  // lexical weight
        float γ = 0.3;  // topic similarity weight
        
        float structScore = computeStructuralScore(su);
        float lexScore = computeLexicalCoherence(su, r);
        float simScore = computeTopicSimilarity(su, r);
        
        return α * structScore + β * lexScore + γ * simScore;
    }
    
    public boolean ensureDeterminism() {
        /* Run assignment twice on identical input
           Assert 100% reproducibility */
    }
}
```

---

## INSTANTIATION AND WORKFLOW

### Typical Initialization Sequence
```
1. Create DocumentProcessorEngine
2. Create RoleAssignmentEngine with scoring weights
3. Create IntentClassifier with 5+ intent types
4. Create RoleReallocationEngine with intent mapping
5. Create RoleQueueStateMachine (empty)
6. Create ContinuityManager
7. Create LLMAdapter with model_name and api_key
8. Create Session (empty, ready for document)

Load Document:
9. Document.parse()
10. DocumentProcessorEngine.segment()
   → Produces List<SemanticUnit>
11. RoleAssignmentEngine.assignRoles(segments)
   → Produces Map<SegmentID, RoleQueue>

Start Conversation:
12. Initialize RQSM with first role queue
13. Begin dialogue loop:
    a. Get current role from queue
    b. Format prompt via LLMAdapter
    c. Query LLM
    d. IntentClassifier.classify(userInput)
    e. If reallocation needed: RoleReallocationEngine.reorder()
    f. RQSM.transition(newState)
    g. ContinuityManager.trackPosition()
    h. Session.save() to database
```

