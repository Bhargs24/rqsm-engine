# Implementation Roadmap

## Document-Segment Driven Role-Oriented Conversational Study System (RQSM-Engine)

**Version:** 1.0  
**Date:** January 29, 2026  
**Target:** Academic Capstone MVP (40-50% Implementation)

---

## Table of Contents

1. [Project Timeline](#project-timeline)
2. [Phase Breakdown](#phase-breakdown)
3. [MVP Scope Definition](#mvp-scope-definition)
4. [Implementation Phases](#implementation-phases)
5. [Milestones & Deliverables](#milestones--deliverables)
6. [Risk Management](#risk-management)
7. [Success Criteria](#success-criteria)

---

## Project Timeline

**Total Duration:** 12 weeks

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│  Weeks 1-3  │  Weeks 4-6  │  Weeks 7-9  │ Weeks 10-12 │
│             │             │             │             │
│  PHASE 1    │  PHASE 2    │  PHASE 3    │  PHASE 4    │
│  Foundation │  Roles &    │  State      │ Integration │
│             │  Assignment │  Machine    │ & Testing   │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

### Weekly Breakdown

| Week | Focus | Key Deliverable |
|------|-------|----------------|
| 1 | Project setup, document processing | Document loader + segmenter |
| 2 | Semantic unit extraction | Heading detection + cohesion scoring |
| 3 | Test document collection | 5-10 sample documents |
| 4 | Role template definitions | 5 role templates with prompts |
| 5 | Role assignment algorithm | Deterministic scoring engine |
| 6 | Assignment testing | Validation of role queues |
| 7 | RQSM state machine | State transitions implemented |
| 8 | Interruption monitor | Intent classification (keyword-based) |
| 9 | Role reallocation | Dynamic queue reordering |
| 10 | Session continuity | History tracking + context injection |
| 11 | End-to-end integration | Full pipeline working |
| 12 | Testing & documentation | Test suite + final report |

---

## Phase Breakdown

### Phase 1: Foundation (Weeks 1-3)
**Goal**: Establish document processing pipeline

**Core Activities**:
1. Set up project structure
2. Implement document loading (TXT, PDF)
3. Build semantic segmentation
4. Create test dataset

**Success Criteria**:
- ✓ Load documents successfully
- ✓ Extract semantic units with metadata
- ✓ Test on 5+ different documents

### Phase 2: Roles & Assignment (Weeks 4-6)
**Goal**: Define roles and assign them deterministically

**Core Activities**:
1. Define 5 role templates
2. Implement scoring algorithms
3. Create role assignment engine
4. Validate determinism

**Success Criteria**:
- ✓ All 5 roles defined with prompts
- ✓ Same input → same role queue
- ✓ Score computation documented

### Phase 3: State Machine & Interruption (Weeks 7-9)
**Goal**: Orchestrate dialogue with interruption handling

**Core Activities**:
1. Implement RQSM
2. Build interruption monitor
3. Create role reallocation logic
4. Add stability mechanisms

**Success Criteria**:
- ✓ State machine transitions correctly
- ✓ Intent classification works (5+ types)
- ✓ No oscillation in test cases

### Phase 4: Integration & Validation (Weeks 10-12)
**Goal**: Complete system integration and testing

**Core Activities**:
1. Integrate all modules
2. Add session continuity
3. LLM integration
4. Comprehensive testing
5. Documentation

**Success Criteria**:
- ✓ End-to-end dialogue generation
- ✓ All test suites passing
- ✓ Documentation complete

---

## MVP Scope Definition

### What IS Included (40-50% Implementation)

#### Core Modules (All 7)
1. ✅ **Document Processing** - Semantic segmentation
2. ✅ **Role Templates** - 5 roles defined
3. ✅ **Role Assignment** - Deterministic scoring
4. ✅ **RQSM** - State machine implementation
5. ✅ **Interruption Monitor** - Keyword-based intent detection
6. ✅ **Role Reallocation** - Queue reordering with stability
7. ✅ **Session Continuity** - History tracking

#### Key Features
- Deterministic dialogue generation (temperature=0)
- All 5 roles operational
- Basic interruption handling
- Simple keyword-based intent classification
- Bounded delay + hysteresis
- Session history logging

#### Testing
- Unit tests for each module
- Integration tests for pipeline
- Reproducibility validation
- Stability tests (no oscillation)

### What is NOT Included (We dont need)

#### Advanced Features
- ❌ ML-based intent classification
- ❌ User authentication
- ❌ Multi-user support
- ❌ Real-time collaborative features
- ❌ Mobile application
- ❌ Advanced UI/UX

#### Optimization
- ❌ LLM response caching
- ❌ Distributed architecture
- ❌ Performance tuning
- ❌ Scalability enhancements

#### Advanced Document Processing
- ❌ OCR for scanned documents
- ❌ Multi-format support (DOCX, HTML)
- ❌ Image/diagram handling
- ❌ Complex table extraction

---

## Implementation Phases

### PHASE 1: Foundation (Weeks 1-3)

#### Week 1: Project Setup
**Day 1-2: Environment Setup**
```bash
# Initialize project
mkdir rqsm-engine
cd rqsm-engine
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install fastapi uvicorn pydantic
pip install pdfplumber sentence-transformers
pip install openai python-dotenv
pip install pytest pytest-asyncio black mypy
```

**Day 3-5: Document Loader**
- Create `app/document/loader.py`
- Implement:
  - `load_text(filepath: str) -> str`
  - `load_pdf(filepath: str) -> str`
  - Basic error handling

**Day 6-7: Testing**
- Write unit tests
- Test with sample documents

#### Week 2: Semantic Segmentation
**Day 1-3: Heading Detection**
```python
# app/document/segmenter.py

def detect_headings(text: str) -> List[Heading]:
    """Use regex to identify document headings"""
    # Pattern: Lines with ALL CAPS or starting with numbers
    pass

def build_hierarchy(headings: List[Heading]) -> DocumentStructure:
    """Build hierarchical structure from headings"""
    pass
```

**Day 4-5: Paragraph Grouping**
```python
def compute_semantic_similarity(para1: str, para2: str) -> float:
    """Use sentence embeddings for similarity"""
    # SentenceTransformer('all-MiniLM-L6-v2')
    pass

def group_paragraphs(paragraphs: List[str], threshold: float = 0.75) -> List[SemanticUnit]:
    """Group semantically similar paragraphs"""
    pass
```

**Day 6-7: Cohesion Scoring**
```python
def compute_cohesion_score(unit: SemanticUnit) -> float:
    """Score semantic cohesiveness"""
    # Based on intra-unit similarity
    pass
```

#### Week 3: Test Dataset & Validation
**Day 1-3: Collect Documents**
- 5-10 academic texts (PDFs, TXT)
- Cover diverse topics
- Varying complexity

**Day 4-5: Integration Testing**
```python
# tests/test_document_processing.py

def test_document_to_semantic_units():
    doc_path = "tests/fixtures/sample.pdf"
    units = process_document(doc_path)
    
    assert len(units) >= 3
    assert all('id' in u for u in units)
    assert all('text' in u for u in units)
```

**Day 6-7: Refine & Document**
- Fix edge cases
- Write documentation
- Prepare for Phase 2

---

### PHASE 2: Roles & Assignment (Weeks 4-6)

#### Week 4: Role Template System
**Day 1-2: Define Role Structure**
```python
# app/roles/role_templates.py

@dataclass
class Role:
    name: str
    description: str
    system_prompt: str
    priority_weight: float
    triggers: List[str]

# Define all 5 roles
EXPLAINER = Role(
    name="Explainer",
    description="Breaks down complex concepts",
    system_prompt="""You are an educational guide...""",
    priority_weight=8.0,
    triggers=["introduction", "definition", "technical_term"]
)

CHALLENGER = Role(...)
SUMMARIZER = Role(...)
EXAMPLE_GENERATOR = Role(...)
MISCONCEPTION_SPOTTER = Role(...)
```

**Day 3-5: Prompt Engineering**
- Craft effective system prompts for each role
- Test prompts with OpenAI API
- Refine based on output quality

**Day 6-7: Unit Tests**
```python
def test_role_templates():
    assert len(ALL_ROLES) == 5
    assert all(r.priority_weight > 0 for r in ALL_ROLES)
```

#### Week 5: Role Assignment Engine
**Day 1-3: Scoring Functions**
```python
# app/roles/role_assignment.py

def structural_score(segment: SemanticUnit, role: Role) -> float:
    """Score based on document structure"""
    if segment.document_section == "introduction":
        if role.name == "Summarizer":
            return 9.0
        elif role.name == "Explainer":
            return 8.5
    # ... more logic
    return 5.0

def lexical_coherence_score(segment: SemanticUnit, role: Role) -> float:
    """Score based on text content"""
    # Count technical terms → favor Explainer
    # Count question words → favor Challenger
    pass

def topic_similarity_score(segment: SemanticUnit, role: Role) -> float:
    """Score based on topic matching"""
    # Use embeddings to match segment to role expertise
    pass
```

**Day 4-5: Combined Scoring**
```python
def compute_role_score(segment: SemanticUnit, role: Role) -> float:
    """Deterministic combined score"""
    α, β, γ = 0.4, 0.3, 0.3
    
    score = (
        α * structural_score(segment, role) +
        β * lexical_coherence_score(segment, role) +
        γ * topic_similarity_score(segment, role)
    )
    return score

def assign_roles(segment: SemanticUnit) -> List[Role]:
    """Return ordered role queue"""
    scores = {role: compute_role_score(segment, role) for role in ALL_ROLES}
    sorted_roles = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [role for role, score in sorted_roles]
```

**Day 6-7: Determinism Validation**
```python
def test_deterministic_assignment():
    """Same segment must produce same role queue"""
    segment = create_test_segment()
    
    queue1 = assign_roles(segment)
    queue2 = assign_roles(segment)
    
    assert queue1 == queue2
    
    # Run 100 times
    queues = [assign_roles(segment) for _ in range(100)]
    assert all(q == queues[0] for q in queues)
```

#### Week 6: Validation & Refinement
**Day 1-3: Test on Real Documents**
- Run assignment on all test documents
- Verify role queues make pedagogical sense
- Adjust weights if needed

**Day 4-5: Edge Case Handling**
- Very short segments
- Very long segments
- Technical vs. narrative content

**Day 6-7: Documentation**
- Document scoring algorithms
- Add examples
- Prepare for Phase 3

---

### PHASE 3: State Machine & Interruption (Weeks 7-9)

#### Week 7: RQSM Implementation
**Day 1-2: State Structure**
```python
# app/state_machine/rqsm.py

@dataclass
class DialogueState:
    current_segment: str
    current_index: int
    current_role: Role
    role_queue: List[Role]
    interruption_detected: bool = False
    transition_lock: float = 0.0
    hysteresis_map: Dict[str, int] = field(default_factory=dict)
    history_pointer: int = 0
```

**Day 3-5: Transition Logic**
```python
class RQSM:
    def __init__(self, segments: List[SemanticUnit], role_assignments: Dict):
        self.segments = segments
        self.assignments = role_assignments
        self.state = self._initialize_state()
    
    def advance(self) -> Optional[Turn]:
        """Advance to next role in queue"""
        if self.state.current_index >= len(self.state.role_queue) - 1:
            # Move to next segment
            return self._next_segment()
        else:
            # Next role in current segment
            self.state.current_index += 1
            self.state.current_role = self.state.role_queue[self.state.current_index]
            return self._generate_turn()
    
    def _generate_turn(self) -> Turn:
        """Generate dialogue for current role"""
        # Prepare prompt with context
        # Call LLM
        # Log turn
        pass
```

**Day 6-7: Testing**
```python
def test_rqsm_transitions():
    rqsm = setup_test_rqsm()
    
    # Advance through full segment
    turns = []
    while not rqsm.is_segment_complete():
        turn = rqsm.advance()
        turns.append(turn)
    
    assert len(turns) == 5  # All 5 roles spoke
    assert turns[0].role.name == "Summarizer"  # Based on assignment
```

#### Week 8: Interruption Monitor
**Day 1-2: Intent Patterns**
```python
# app/interruption/intent_classifier.py

INTENT_PATTERNS = {
    "Clarification": [
        r"explain.*more",
        r"don't understand",
        r"clarify",
        r"what.*mean"
    ],
    "Objection": [
        r"disagree",
        r"doesn't.*right",
        r"but.*what if"
    ],
    "Example": [
        r"example",
        r"concrete",
        r"real.*world"
    ],
    "Depth": [
        r"deeper",
        r"more.*detail",
        r"elaborate"
    ],
    "Summary": [
        r"summarize",
        r"key.*points",
        r"recap"
    ]
}
```

**Day 3-4: Classification Logic**
```python
def classify_intent(user_input: str) -> Tuple[Intent, float]:
    """Classify user interruption intent"""
    user_lower = user_input.lower()
    
    scores = {}
    for intent, patterns in INTENT_PATTERNS.items():
        matches = sum(1 for p in patterns if re.search(p, user_lower))
        scores[intent] = matches / len(patterns)
    
    best_intent = max(scores.items(), key=lambda x: x[1])
    return best_intent[0], best_intent[1]
```

**Day 5-7: Testing & Refinement**
```python
def test_intent_classification():
    test_cases = [
        ("Can you explain that more?", "Clarification", 0.8),
        ("Give me an example", "Example", 0.9),
        ("I disagree with that", "Objection", 0.85)
    ]
    
    for text, expected, min_conf in test_cases:
        intent, conf = classify_intent(text)
        assert intent == expected
        assert conf >= min_conf
```

#### Week 9: Role Reallocation
**Day 1-3: Alignment Matrix**
```python
# app/interruption/reallocator.py

INTENT_ROLE_ALIGNMENT = {
    "Clarification": {
        "Explainer": 0.9,
        "Challenger": 0.3,
        "Summarizer": 0.7,
        "Example-Generator": 0.6,
        "Misconception-Spotter": 0.8
    },
    "Example": {
        "Explainer": 0.5,
        "Challenger": 0.4,
        "Summarizer": 0.4,
        "Example-Generator": 0.95,
        "Misconception-Spotter": 0.3
    },
    # ... more intents
}
```

**Day 4-5: Reallocation Algorithm**
```python
def reallocate_roles(
    current_queue: List[Role],
    intent: Intent,
    usage_history: Dict[str, int]
) -> List[Role]:
    """Reorder queue based on intent"""
    
    new_scores = {}
    for role in current_queue:
        old_score = role.priority_weight
        alignment = INTENT_ROLE_ALIGNMENT[intent][role.name]
        penalty = usage_history.get(role.name, 0) * 0.5
        
        new_score = old_score + (5.0 * alignment) - penalty
        new_scores[role] = new_score
    
    sorted_roles = sorted(new_scores.items(), key=lambda x: x[1], reverse=True)
    return [role for role, _ in sorted_roles]
```

**Day 6-7: Stability Mechanisms**
```python
def apply_bounded_delay(state: DialogueState, delay: int = 3):
    """Prevent immediate role switching"""
    state.transition_lock = delay

def apply_hysteresis(state: DialogueState, role: Role, window: int = 7):
    """Block demoted role from returning"""
    state.hysteresis_map[role.name] = state.history_pointer + window
```

---

### PHASE 4: Integration & Validation (Weeks 10-12)

#### Week 10: Session Continuity & LLM Integration
**Day 1-2: Session Manager**
```python
# app/session/session_manager.py

class SessionManager:
    def __init__(self):
        self.history: List[Turn] = []
        self.context_window = 10
    
    def log_turn(self, turn: Turn):
        self.history.append(turn)
    
    def get_context(self, n: int = 10) -> List[Turn]:
        return self.history[-n:]
    
    def inject_context(self, prompt: str) -> str:
        """Add relevant past context to prompt"""
        context = self.get_context()
        context_str = "\n".join([f"{t.role.name}: {t.message}" for t in context])
        return f"Previous context:\n{context_str}\n\n{prompt}"
```

**Day 3-4: LLM Client**
```python
# app/llm/client.py

class LLMClient:
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        openai.api_key = api_key
        self.model = model
    
    def generate(self, prompt: str, temperature: float = 0.0) -> str:
        """Generate response from LLM"""
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[{"role": "system", "content": prompt}],
            temperature=temperature
        )
        return response.choices[0].message.content
```

**Day 5-7: Integration**
- Connect all modules
- Test end-to-end flow
- Fix integration bugs

#### Week 11: Comprehensive Testing
**Day 1-2: Reproducibility Tests**
```python
def test_full_reproducibility():
    """End-to-end determinism check"""
    doc = "tests/fixtures/chapter1.pdf"
    
    dialogue1 = run_system(doc, seed=42)
    dialogue2 = run_system(doc, seed=42)
    
    assert len(dialogue1) == len(dialogue2)
    for t1, t2 in zip(dialogue1, dialogue2):
        assert t1.role.name == t2.role.name
        assert t1.message == t2.message
```

**Day 3-4: Stability Tests**
```python
def test_no_oscillation():
    """Verify no role oscillation under interruptions"""
    doc = "tests/fixtures/chapter1.pdf"
    interruptions = generate_test_interruptions(50)
    
    dialogue = run_system_with_interruptions(doc, interruptions)
    role_sequence = [t.role.name for t in dialogue]
    
    oscillations = detect_oscillations(role_sequence)
    assert oscillations == 0
```

**Day 5-7: Integration Tests**
- Test all modules together
- Edge case handling
- Performance benchmarking

#### Week 12: Documentation & Finalization
**Day 1-3: Documentation**
- API documentation
- Architecture guide
- Usage examples
- Deployment instructions

**Day 4-5: Final Testing**
- Run full test suite
- Fix any remaining bugs
- Code cleanup

**Day 6-7: Presentation Prep**
- Demo script
- Slides
- Final report

---

## Milestones & Deliverables

### Milestone 1: Document Processing Complete (Week 3)
**Deliverables**:
- ✅ Document loader (TXT, PDF)
- ✅ Semantic segmentation working
- ✅ Test dataset (5-10 documents)
- ✅ Unit tests passing

**Success Criteria**:
- Can process all test documents
- Semantic units have good cohesion (score > 0.75)
- No crashes on edge cases

### Milestone 2: Role System Complete (Week 6)
**Deliverables**:
- ✅ 5 role templates defined
- ✅ Role assignment engine working
- ✅ Determinism validated
- ✅ Scoring algorithms documented

**Success Criteria**:
- Same input → same role queue (100 trials)
- Role assignments make pedagogical sense
- All unit tests passing

### Milestone 3: State Machine & Interruption (Week 9)
**Deliverables**:
- ✅ RQSM implemented
- ✅ Interruption monitor working
- ✅ Role reallocation functional
- ✅ Stability mechanisms active

**Success Criteria**:
- State transitions work correctly
- Intent classification ≥85% accuracy
- No oscillation in test scenarios
- Bounded delay and hysteresis working

### Milestone 4: Integration Complete (Week 12)
**Deliverables**:
- ✅ Full system integrated
- ✅ LLM integration working
- ✅ Session continuity active
- ✅ All tests passing
- ✅ Documentation complete

**Success Criteria**:
- End-to-end dialogue generation works
- Reproducibility validated
- Stability validated
- Code documented
- Demo ready

---

## Risk Management

### Risk 1: LLM API Costs
**Likelihood**: High  
**Impact**: Medium

**Mitigation**:
- Use gpt-3.5-turbo (cheaper than GPT-4)
- Implement response caching
- Use mock responses for testing
- Set usage limits

**Fallback**:
- Use HuggingFace open models
- Pre-generated responses for demo

### Risk 2: Document Segmentation Quality
**Likelihood**: Medium  
**Impact**: High

**Mitigation**:
- Test on diverse documents early
- Implement multiple segmentation strategies
- Manual validation of output

**Fallback**:
- Allow manual segment boundaries
- Use simpler paragraph-based segmentation

### Risk 3: Determinism Not Achievable
**Likelihood**: Low  
**Impact**: Very High

**Mitigation**:
- Set temperature=0 from start
- Fix random seeds everywhere
- Test determinism continuously

**Fallback**:
- Accept "quasi-deterministic" (95%+ consistency)
- Document deviations

### Risk 4: Integration Complexity
**Likelihood**: Medium  
**Impact**: Medium

**Mitigation**:
- Modular design with clear interfaces
- Continuous integration testing
- Weekly integration checks

**Fallback**:
- Reduce module count
- Simplify interactions

### Risk 5: Time Constraints
**Likelihood**: High  
**Impact**: High

**Mitigation**:
- Agile sprints with weekly deliverables
- MVP scope clearly defined
- Buffer time in Week 12

**Fallback**:
- Cut advanced features
- Focus on core functionality

---

## Success Criteria

### Technical Success
1. ✅ **Determinism**: 100% reproducibility on test cases
2. ✅ **Stability**: Zero oscillations in interruption tests
3. ✅ **Completeness**: All 7 modules implemented
4. ✅ **Testing**: ≥80% code coverage
5. ✅ **Performance**: <5s response time per turn

### Academic Success
1. ✅ **Novelty**: Demonstrates unique approach (RQSM)
2. ✅ **Validation**: Meets pedagogical alignment criteria
3. ✅ **Documentation**: Complete technical documentation
4. ✅ **Presentation**: Clear demonstration of system

### Functional Success
1. ✅ **Document Processing**: Processes 10+ different documents
2. ✅ **Role Quality**: Roles provide distinct perspectives
3. ✅ **Interruption Handling**: Responds appropriately to intents
4. ✅ **Dialogue Quality**: Coherent multi-turn conversations

---

## Next Steps After Capstone

### Short-Term Improvements (1-3 months)
1. ML-based intent classification
2. Response caching
3. Web UI
4. More robust error handling

### Medium-Term Enhancements (3-6 months)
1. Multi-user support
2. User authentication
3. Role customization per domain
4. A/B testing framework

### Long-Term Vision (6-12 months)
1. Mobile application
2. Real-time collaboration
3. Multi-language support
4. Patent filing
5. Commercial pilot

---

## Conclusion

This roadmap provides a **clear, achievable path** to implementing a functional MVP of the RQSM-Engine within 12 weeks. The phased approach ensures:

1. **Progressive complexity** - Build foundation before advanced features
2. **Continuous validation** - Test at each phase
3. **Risk mitigation** - Fallback plans for major risks
4. **Clear deliverables** - Measurable progress at each milestone

By focusing on the **core 40-50% implementation**, we deliver a working prototype that demonstrates the novel concepts while staying within capstone constraints.
