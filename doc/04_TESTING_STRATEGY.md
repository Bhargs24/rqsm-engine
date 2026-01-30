# Testing Strategy Document

## Document-Segment Driven Role-Oriented Conversational Study System (RQSM-Engine)

**Version:** 1.0  
**Date:** January 29, 2026  
**Purpose:** Comprehensive testing plan for validation and quality assurance

---

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Categories](#test-categories)
3. [Unit Tests](#unit-tests)
4. [Integration Tests](#integration-tests)
5. [System Tests](#system-tests)
6. [Validation Tests](#validation-tests)
7. [Performance Tests](#performance-tests)
8. [Test Data](#test-data)
9. [Test Execution Plan](#test-execution-plan)

---

## Testing Philosophy

### Core Principles

1. **Determinism Verification**: Every test must validate reproducibility
2. **Pedagogical Correctness**: Tests verify educational soundness
3. **Stability Assurance**: No oscillations or unstable behavior
4. **Comprehensive Coverage**: ≥80% code coverage target
5. **Automated Validation**: All tests automated via pytest

### Success Criteria

| Category | Metric | Target |
|----------|--------|--------|
| Code Coverage | Lines covered | ≥80% |
| Determinism | Reproducibility rate | 100% |
| Stability | Oscillation count | 0 |
| Intent Classification | Accuracy | ≥85% |
| Test Pass Rate | All tests | 100% |
| Performance | Response time per turn | <5s |

---

## Test Categories

### 1. Unit Tests
**Scope**: Individual functions and methods  
**Coverage**: Each module in isolation  
**Tool**: pytest

### 2. Integration Tests
**Scope**: Module interactions  
**Coverage**: Data flow between modules  
**Tool**: pytest with fixtures

### 3. System Tests
**Scope**: End-to-end workflows  
**Coverage**: Complete dialogue generation  
**Tool**: pytest with integration fixtures

### 4. Validation Tests
**Scope**: Core system properties  
**Coverage**: Determinism, stability, pedagogical alignment  
**Tool**: Custom test suite

### 5. Performance Tests
**Scope**: Speed and efficiency  
**Coverage**: Response times, memory usage  
**Tool**: pytest-benchmark

---

## Unit Tests

### Module 1: Document Processor

#### Test Suite 1.1: Document Loader

```python
# tests/unit/test_document_loader.py

import pytest
from app.document.loader import load_text, load_pdf, load_document

def test_load_text_success():
    """Verify text file loading"""
    text = load_text('tests/fixtures/sample.txt')
    
    assert isinstance(text, str)
    assert len(text) > 0
    assert 'test content' in text.lower()

def test_load_text_file_not_found():
    """Verify error handling for missing file"""
    with pytest.raises(FileNotFoundError):
        load_text('nonexistent.txt')

def test_load_text_encoding():
    """Verify UTF-8 encoding handling"""
    text = load_text('tests/fixtures/unicode.txt')
    assert 'café' in text
    assert '日本語' in text

def test_load_pdf_success():
    """Verify PDF extraction"""
    text = load_pdf('tests/fixtures/sample.pdf')
    
    assert isinstance(text, str)
    assert len(text) > 100
    assert '\n\n' in text  # Page separators

def test_load_pdf_multipage():
    """Verify multi-page PDF handling"""
    text = load_pdf('tests/fixtures/multipage.pdf')
    pages = text.split('\n\n')
    assert len(pages) >= 2

def test_load_document_dispatcher():
    """Verify universal loader dispatches correctly"""
    txt_content = load_document('tests/fixtures/sample.txt')
    pdf_content = load_document('tests/fixtures/sample.pdf')
    
    assert isinstance(txt_content, str)
    assert isinstance(pdf_content, str)

def test_load_document_unsupported_type():
    """Verify error for unsupported file types"""
    with pytest.raises(ValueError, match="Unsupported file type"):
        load_document('tests/fixtures/sample.docx')
```

#### Test Suite 1.2: Heading Detection

```python
# tests/unit/test_heading_detector.py

from app.document.heading_detector import detect_headings, build_hierarchy

def test_detect_all_caps_heading():
    """Verify ALL CAPS heading detection"""
    text = """
    INTRODUCTION TO TESTING
    
    This is the content.
    """
    headings = detect_headings(text)
    
    assert len(headings) >= 1
    assert any(h.text == "INTRODUCTION TO TESTING" for h in headings)
    assert headings[0].level == 1

def test_detect_numbered_heading():
    """Verify numbered heading detection"""
    text = """
    1. Overview
    
    Content here.
    
    1.1 Details
    
    More content.
    """
    headings = detect_headings(text)
    
    assert len(headings) == 2
    assert headings[0].text == "Overview"
    assert headings[0].level == 1
    assert headings[1].text == "Details"
    assert headings[1].level == 2

def test_detect_underlined_heading():
    """Verify underlined heading detection"""
    text = """
    Main Heading
    ============
    
    Content.
    
    Sub Heading
    -----------
    
    More content.
    """
    headings = detect_headings(text)
    
    assert len(headings) == 2
    assert headings[0].level == 1
    assert headings[1].level == 2

def test_no_false_positives():
    """Verify no false heading detections"""
    text = """
    This is normal text with some WORDS IN CAPS.
    
    And some short lines.
    Like this.
    """
    headings = detect_headings(text)
    
    # Should not detect regular caps words as headings
    assert len(headings) == 0

def test_build_hierarchy():
    """Verify hierarchical structure building"""
    text = """
    1. Chapter
    1.1 Section
    1.2 Section
    2. Chapter
    """
    headings = detect_headings(text)
    hierarchy = build_hierarchy(headings)
    
    assert 'children' in hierarchy
    # Further hierarchy checks...
```

#### Test Suite 1.3: Semantic Segmentation

```python
# tests/unit/test_segmenter.py

from app.document.segmenter import SemanticSegmenter

@pytest.fixture
def segmenter():
    return SemanticSegmenter()

def test_segment_simple_document(segmenter):
    """Verify basic document segmentation"""
    text = """
    Introduction to the topic.
    This explains the background.
    
    Main content here.
    More details about the subject.
    
    Conclusion and summary.
    """
    units = segmenter.segment_document(text, [])
    
    assert len(units) >= 2
    assert all(hasattr(u, 'text') for u in units)
    assert all(u.word_count > 0 for u in units)

def test_segment_with_headings(segmenter):
    """Verify segmentation respects headings"""
    text = """
    INTRODUCTION
    
    Intro content.
    
    METHODS
    
    Methods content.
    """
    headings = detect_headings(text)
    units = segmenter.segment_document(text, headings)
    
    assert len(units) >= 2
    assert any('introduction' in u.document_section.lower() for u in units)

def test_cohesion_scoring(segmenter):
    """Verify cohesion scores are computed"""
    text = """
    Machine learning is a field of AI.
    It involves training algorithms on data.
    Neural networks are a popular approach.
    
    Cooking is an art and science.
    Recipes provide instructions.
    """
    units = segmenter.segment_document(text, [])
    
    assert all(0 <= u.similarity_score <= 1.0 for u in units)

def test_minimum_unit_size(segmenter):
    """Verify units meet minimum size"""
    text = "Word. " * 100  # 100 words
    units = segmenter.segment_document(text, [])
    
    assert all(u.word_count >= 50 for u in units)

def test_semantic_grouping(segmenter):
    """Verify semantically similar paragraphs are grouped"""
    text = """
    Python is a programming language.
    It is used for web development.
    Django is a Python framework.
    
    The sky is blue today.
    Birds are flying high.
    Weather looks nice.
    """
    units = segmenter.segment_document(text, [])
    
    # First unit should have high cohesion (Python-related)
    # Second unit should have high cohesion (weather-related)
    assert units[0].similarity_score > 0.7
```

### Module 2: Role Template System

```python
# tests/unit/test_role_templates.py

from app.roles.role_templates import get_all_roles, get_role, RoleType

def test_all_roles_defined():
    """Verify all 5 roles are defined"""
    roles = get_all_roles()
    assert len(roles) == 5

def test_role_properties():
    """Verify each role has required properties"""
    for role in get_all_roles():
        assert role.name
        assert role.description
        assert role.system_prompt
        assert 0 <= role.priority_weight <= 10
        assert len(role.triggers) > 0
        assert len(role.content_affinity) > 0

def test_role_retrieval():
    """Verify role retrieval by type"""
    explainer = get_role(RoleType.EXPLAINER)
    assert explainer.name == "Explainer"
    assert "explain" in explainer.system_prompt.lower()

def test_role_uniqueness():
    """Verify all roles have unique names"""
    roles = get_all_roles()
    names = [r.name for r in roles]
    assert len(names) == len(set(names))

def test_prompt_quality():
    """Verify prompts contain key instructions"""
    explainer = get_role(RoleType.EXPLAINER)
    assert "step-by-step" in explainer.system_prompt.lower()
    
    challenger = get_role(RoleType.CHALLENGER)
    assert "question" in challenger.system_prompt.lower()
```

### Module 3: Role Assignment Engine

```python
# tests/unit/test_role_assignment.py

from app.roles.role_assignment import RoleAssignmentEngine

@pytest.fixture
def engine():
    return RoleAssignmentEngine()

def test_deterministic_assignment(engine):
    """CRITICAL: Verify deterministic role assignment"""
    segment = create_test_segment()
    
    result1 = engine.assign_roles(segment)
    result2 = engine.assign_roles(segment)
    
    assert result1['queue'] == result2['queue']
    assert result1['scores'] == result2['scores']

def test_deterministic_100_trials(engine):
    """Verify determinism over 100 trials"""
    segment = create_test_segment()
    
    results = [engine.assign_roles(segment) for _ in range(100)]
    
    # All queues should be identical
    first_queue = results[0]['queue']
    assert all(r['queue'] == first_queue for r in results)

def test_all_roles_in_queue(engine):
    """Verify all 5 roles are in every queue"""
    segment = create_test_segment()
    result = engine.assign_roles(segment)
    
    assert len(result['queue']) == 5
    role_names = [r.name for r in result['queue']]
    assert len(set(role_names)) == 5  # All unique

def test_introduction_favors_summarizer(engine):
    """Verify introductions prioritize Summarizer"""
    intro_segment = create_segment(
        text="Introduction to the topic...",
        section="introduction"
    )
    
    result = engine.assign_roles(intro_segment)
    top_roles = [r.type for r in result['queue'][:2]]
    
    assert RoleType.SUMMARIZER in top_roles or RoleType.EXPLAINER in top_roles

def test_technical_content_scoring(engine):
    """Verify technical content favors Explainer and Misconception-Spotter"""
    tech_segment = create_segment(
        text="The algorithm complexity is O(n log n)...",
        section="methodology"
    )
    
    result = engine.assign_roles(tech_segment)
    top_roles = [r.type for r in result['queue'][:3]]
    
    assert RoleType.EXPLAINER in top_roles or \
           RoleType.MISCONCEPTION_SPOTTER in top_roles

def test_structural_scoring():
    """Verify structural scoring component"""
    engine = RoleAssignmentEngine()
    explainer = get_role(RoleType.EXPLAINER)
    intro_segment = create_segment(section="introduction")
    
    score = engine._structural_score(explainer, intro_segment)
    assert score > explainer.priority_weight  # Should be boosted

def test_lexical_scoring():
    """Verify lexical scoring with triggers"""
    engine = RoleAssignmentEngine()
    example_gen = get_role(RoleType.EXAMPLE_GENERATOR)
    segment = create_segment(text="For example, consider this case...")
    
    score = engine._lexical_score(example_gen, segment)
    assert score > 5.0  # Should detect "example" trigger
```

### Module 4: Role Queue State Machine

```python
# tests/unit/test_rqsm.py

from app.state_machine.rqsm import RQSM

@pytest.fixture
def rqsm():
    segments = create_test_segments(3)
    assignments = create_test_assignments(segments)
    return RQSM(segments, assignments)

def test_initialization(rqsm):
    """Verify RQSM initializes correctly"""
    assert rqsm.state.current_segment_index == 0
    assert rqsm.state.current_role_index == 0
    assert len(rqsm.state.role_queue) == 5

def test_advance_increments_role(rqsm):
    """Verify advance moves to next role"""
    initial_index = rqsm.state.current_role_index
    turn = rqsm.advance()
    
    assert turn is not None
    assert rqsm.state.current_role_index == initial_index + 1

def test_advance_through_segment(rqsm):
    """Verify advancing through all roles in segment"""
    initial_segment = rqsm.state.current_segment_index
    
    # Advance through all 5 roles
    for _ in range(5):
        turn = rqsm.advance()
        assert turn is not None
    
    # Should now be on next segment
    assert rqsm.state.current_segment_index == initial_segment + 1
    assert rqsm.state.current_role_index == 0

def test_transition_lock(rqsm):
    """Verify bounded delay prevents immediate transitions"""
    rqsm.state.transition_lock = 3
    
    # Should not advance while locked
    result = rqsm.advance()
    assert result is None
    assert rqsm.state.transition_lock == 2

def test_role_usage_tracking(rqsm):
    """Verify role usage is tracked"""
    role_name = rqsm.current_role().name
    rqsm.advance()
    
    assert role_name in rqsm.state.role_usage_count
    assert rqsm.state.role_usage_count[role_name] >= 1

def test_interruption_handling(rqsm):
    """Verify interruption updates state"""
    new_queue = rqsm.state.role_queue[::-1]  # Reverse order
    
    rqsm.handle_interruption(
        "Give me an example",
        Intent.EXAMPLE_REQUEST,
        new_queue
    )
    
    assert rqsm.state.interruption_detected
    assert rqsm.state.role_queue == new_queue
    assert rqsm.state.transition_lock > 0

def test_dialogue_completion(rqsm):
    """Verify dialogue completion detection"""
    # Advance through all segments
    while not rqsm.is_dialogue_complete():
        rqsm.state.transition_lock = 0  # Skip locks for testing
        rqsm.advance()
    
    assert rqsm.is_dialogue_complete()
```

### Module 5: Interruption Monitor

```python
# tests/unit/test_intent_classifier.py

from app.interruption.intent_classifier import IntentClassifier, Intent

@pytest.fixture
def classifier():
    return IntentClassifier()

def test_clarification_intent(classifier):
    """Verify clarification intent detection"""
    test_cases = [
        "Can you explain that more?",
        "I don't understand",
        "What does that mean?",
        "Please clarify"
    ]
    
    for text in test_cases:
        intent, conf = classifier.classify(text)
        assert intent == Intent.CLARIFICATION
        assert conf > 0.5

def test_example_request_intent(classifier):
    """Verify example request detection"""
    test_cases = [
        "Give me an example",
        "Can you provide a concrete case?",
        "Show me a real-world instance"
    ]
    
    for text in test_cases:
        intent, conf = classifier.classify(text)
        assert intent == Intent.EXAMPLE_REQUEST
        assert conf > 0.7

def test_objection_intent(classifier):
    """Verify objection detection"""
    test_cases = [
        "I disagree with that",
        "That doesn't sound right",
        "But what if X?"
    ]
    
    for text in test_cases:
        intent, conf = classifier.classify(text)
        assert intent == Intent.OBJECTION

def test_confidence_scores(classifier):
    """Verify confidence scores are in valid range"""
    texts = [
        "example please",
        "I don't understand",
        "random text here"
    ]
    
    for text in texts:
        intent, conf = classifier.classify(text)
        assert 0.0 <= conf <= 1.0

def test_threshold_filtering(classifier):
    """Verify confidence threshold filtering"""
    classifier.threshold = 0.8
    
    intent, conf = classifier.classify("maybe example")
    should_trigger = classifier.should_trigger_reallocation(conf)
    
    if conf < 0.8:
        assert not should_trigger

def test_no_match_returns_other(classifier):
    """Verify unmatched input returns OTHER"""
    intent, conf = classifier.classify("xyzabc123")
    assert intent == Intent.OTHER
    assert conf == 0.0
```

### Module 6: Role Reallocation Engine

```python
# tests/unit/test_reallocator.py

from app.interruption.reallocator import RoleReallocationEngine

@pytest.fixture
def engine():
    return RoleReallocationEngine()

def test_example_request_promotes_example_gen(engine):
    """Verify example request promotes Example-Generator"""
    current_queue = get_all_roles()
    new_queue = engine.reallocate(
        current_queue,
        Intent.EXAMPLE_REQUEST,
        usage_history={},
        hysteresis_map={},
        current_turn=1
    )
    
    assert new_queue[0].type == RoleType.EXAMPLE_GENERATOR

def test_clarification_promotes_explainer(engine):
    """Verify clarification promotes Explainer"""
    current_queue = get_all_roles()
    new_queue = engine.reallocate(
        current_queue,
        Intent.CLARIFICATION,
        usage_history={},
        hysteresis_map={},
        current_turn=1
    )
    
    assert new_queue[0].type == RoleType.EXPLAINER

def test_usage_penalty(engine):
    """Verify recently used roles are penalized"""
    current_queue = get_all_roles()
    usage = {"Explainer": 5}  # Used 5 times
    
    new_queue = engine.reallocate(
        current_queue,
        Intent.CLARIFICATION,
        usage_history=usage,
        hysteresis_map={},
        current_turn=1
    )
    
    # Explainer should be promoted but with penalty
    # May not be #1 if penalty is strong
    explainer_idx = [r.type for r in new_queue].index(RoleType.EXPLAINER)
    assert explainer_idx < 3  # Should still be in top 3

def test_hysteresis_lock(engine):
    """Verify hysteresis prevents locked roles"""
    current_queue = get_all_roles()
    hysteresis = {"Challenger": 10}  # Locked until turn 10
    
    new_queue = engine.reallocate(
        current_queue,
        Intent.OBJECTION,  # Would normally favor Challenger
        usage_history={},
        hysteresis_map=hysteresis,
        current_turn=5  # Before lock expires
    )
    
    # Challenger should be at bottom
    challenger_idx = [r.type for r in new_queue].index(RoleType.CHALLENGER)
    assert challenger_idx == 4  # Last position

def test_reallocation_preserves_all_roles(engine):
    """Verify all roles remain in queue after reallocation"""
    current_queue = get_all_roles()
    new_queue = engine.reallocate(
        current_queue,
        Intent.SUMMARY_REQUEST,
        usage_history={},
        hysteresis_map={},
        current_turn=1
    )
    
    assert len(new_queue) == 5
    role_types = set(r.type for r in new_queue)
    assert len(role_types) == 5
```

### Module 7: Session Continuity Manager

```python
# tests/unit/test_session_manager.py

from app.session.session_manager import SessionContinuityManager

@pytest.fixture
def manager():
    return SessionContinuityManager()

def test_log_turn(manager):
    """Verify turn logging"""
    turn = create_test_turn()
    manager.log_turn(turn)
    
    assert len(manager.history.turns) == 1
    assert manager.history.turns[0] == turn

def test_get_recent_turns(manager):
    """Verify recent turn retrieval"""
    for i in range(10):
        manager.log_turn(create_test_turn())
    
    recent = manager.history.get_recent(5)
    assert len(recent) == 5

def test_context_for_prompt(manager):
    """Verify context string generation"""
    for i in range(3):
        manager.log_turn(create_test_turn())
    
    role = get_role(RoleType.EXPLAINER)
    segment = create_test_segment()
    
    context = manager.get_context_for_prompt(role, segment)
    
    assert "Previous conversation:" in context
    assert segment.text in context

def test_context_caching(manager):
    """Verify context caching works"""
    manager.log_turn(create_test_turn())
    
    role = get_role(RoleType.EXPLAINER)
    segment = create_test_segment()
    
    # First call - not cached
    context1 = manager.get_context_for_prompt(role, segment)
    
    # Second call - should be cached
    context2 = manager.get_context_for_prompt(role, segment)
    
    assert context1 == context2
    assert len(manager.context_cache) > 0

def test_session_summary(manager):
    """Verify session summary generation"""
    for i in range(10):
        turn = create_test_turn()
        turn.is_reallocation = (i % 3 == 0)
        manager.log_turn(turn)
    
    summary = manager.get_summary()
    
    assert summary['total_turns'] == 10
    assert 'roles_used' in summary
    assert 'interruptions' in summary
```

---

## Integration Tests

### Test Suite: Document to Roles Pipeline

```python
# tests/integration/test_document_to_roles.py

def test_full_document_processing_pipeline():
    """Test complete document → semantic units → role assignment"""
    
    # Step 1: Load document
    text = load_document('tests/fixtures/chapter1.pdf')
    assert len(text) > 0
    
    # Step 2: Detect headings
    headings = detect_headings(text)
    assert len(headings) >= 2
    
    # Step 3: Segment
    segmenter = SemanticSegmenter()
    units = segmenter.segment_document(text, headings)
    assert len(units) >= 3
    
    # Step 4: Assign roles
    engine = RoleAssignmentEngine()
    assignments = {}
    for unit in units:
        result = engine.assign_roles(unit)
        assignments[unit.id] = result
    
    # Verify
    assert len(assignments) == len(units)
    assert all('queue' in a for a in assignments.values())
```

### Test Suite: RQSM with Real Documents

```python
# tests/integration/test_rqsm_integration.py

def test_rqsm_with_real_document():
    """Test RQSM with actual document processing"""
    
    # Process document
    text = load_document('tests/fixtures/sample.pdf')
    headings = detect_headings(text)
    segmenter = SemanticSegmenter()
    units = segmenter.segment_document(text, headings)
    
    # Assign roles
    engine = RoleAssignmentEngine()
    assignments = {u.id: engine.assign_roles(u) for u in units}
    
    # Initialize RQSM
    rqsm = RQSM(units, assignments)
    
    # Generate dialogue
    turns = []
    for _ in range(10):
        if rqsm.is_dialogue_complete():
            break
        rqsm.state.transition_lock = 0  # Skip delays for testing
        turn = rqsm.advance()
        if turn:
            turns.append(turn)
    
    assert len(turns) >= 5
    assert all(isinstance(t.role, Role) for t in turns)
```

### Test Suite: Interruption Flow

```python
# tests/integration/test_interruption_flow.py

def test_complete_interruption_flow():
    """Test user interruption through reallocation"""
    
    # Setup
    rqsm = setup_test_rqsm()
    classifier = IntentClassifier()
    reallocator = RoleReallocationEngine()
    
    # Generate a few turns
    for _ in range(3):
        rqsm.state.transition_lock = 0
        rqsm.advance()
    
    # User interrupts
    user_input = "Give me an example"
    intent, conf = classifier.classify(user_input)
    
    assert intent == Intent.EXAMPLE_REQUEST
    assert conf >= 0.7
    
    # Reallocate
    new_queue = reallocator.reallocate(
        rqsm.state.role_queue,
        intent,
        rqsm.state.role_usage_count,
        rqsm.state.hysteresis_map,
        rqsm.state.turn_number
    )
    
    # Apply to RQSM
    rqsm.handle_interruption(user_input, intent, new_queue)
    
    # Verify
    assert rqsm.state.interruption_detected
    assert rqsm.state.role_queue[0].type == RoleType.EXAMPLE_GENERATOR
```

---

## System Tests

### Test Suite: End-to-End Dialogue Generation

```python
# tests/system/test_end_to_end.py

def test_complete_dialogue_generation():
    """Test full system from document to dialogue"""
    
    # Initialize system
    from app.dialogue_pipeline import DialogueSystem
    system = DialogueSystem()
    
    # Process document
    dialogue = system.process('tests/fixtures/chapter1.pdf')
    
    # Verify structure
    assert isinstance(dialogue, list)
    assert len(dialogue) >= 10
    assert all('role' in turn for turn in dialogue)
    assert all('message' in turn for turn in dialogue)
    
    # Verify role diversity
    roles_used = set(turn['role'] for turn in dialogue)
    assert len(roles_used) >= 4  # At least 4 different roles

def test_dialogue_with_interruptions():
    """Test dialogue with user interruptions"""
    
    system = DialogueSystem()
    document = 'tests/fixtures/chapter1.pdf'
    
    interruptions = [
        {"turn": 3, "text": "Give me an example"},
        {"turn": 7, "text": "Can you clarify that?"},
        {"turn": 12, "text": "Summarize the key points"}
    ]
    
    dialogue = system.process_with_interruptions(document, interruptions)
    
    # Verify interruptions were handled
    reallocation_count = sum(1 for t in dialogue if t.get('is_reallocation'))
    assert reallocation_count == len(interruptions)
```

---

## Validation Tests

### Test Suite 1: Determinism Validation

```python
# tests/validation/test_determinism.py

def test_reproducibility_single_document():
    """CRITICAL: Verify identical output for same input"""
    
    system = DialogueSystem()
    doc = 'tests/fixtures/chapter1.pdf'
    
    # Run twice
    dialogue1 = system.process(doc, seed=42)
    dialogue2 = system.process(doc, seed=42)
    
    # Compare lengths
    assert len(dialogue1) == len(dialogue2), "Different lengths!"
    
    # Compare role sequences
    roles1 = [t['role'] for t in dialogue1]
    roles2 = [t['role'] for t in dialogue2]
    assert roles1 == roles2, "Role sequences differ!"
    
    # Compare messages (if LLM deterministic)
    for t1, t2 in zip(dialogue1, dialogue2):
        assert t1['message'] == t2['message'], f"Messages differ at turn {t1['turn']}"

def test_reproducibility_multiple_documents():
    """Verify determinism across multiple documents"""
    
    system = DialogueSystem()
    documents = [
        'tests/fixtures/doc1.pdf',
        'tests/fixtures/doc2.pdf',
        'tests/fixtures/doc3.pdf'
    ]
    
    for doc in documents:
        dialogue1 = system.process(doc, seed=42)
        dialogue2 = system.process(doc, seed=42)
        
        assert len(dialogue1) == len(dialogue2)
        assert [t['role'] for t in dialogue1] == [t['role'] for t in dialogue2]

def test_reproducibility_100_trials():
    """Verify determinism over 100 trials"""
    
    system = DialogueSystem()
    doc = 'tests/fixtures/sample.pdf'
    
    dialogues = [system.process(doc, seed=42) for _ in range(100)]
    
    # All should be identical
    first = dialogues[0]
    for i, dialogue in enumerate(dialogues[1:], 1):
        assert len(dialogue) == len(first), f"Trial {i} differs in length"
        assert [t['role'] for t in dialogue] == [t['role'] for t in first], \
               f"Trial {i} differs in roles"
```

### Test Suite 2: Stability Validation

```python
# tests/validation/test_stability.py

def detect_oscillation(role_sequence: List[str]) -> int:
    """Count role oscillations (A→B→A→B patterns)"""
    oscillations = 0
    for i in range(len(role_sequence) - 3):
        if (role_sequence[i] == role_sequence[i+2] and
            role_sequence[i+1] == role_sequence[i+3] and
            role_sequence[i] != role_sequence[i+1]):
            oscillations += 1
    return oscillations

def test_no_oscillation_normal_flow():
    """Verify no oscillation in normal dialogue"""
    
    system = DialogueSystem()
    dialogue = system.process('tests/fixtures/chapter1.pdf')
    
    roles = [t['role'] for t in dialogue]
    oscillations = detect_oscillation(roles)
    
    assert oscillations == 0, f"Found {oscillations} oscillations!"

def test_no_oscillation_with_interruptions():
    """Verify stability under interruptions"""
    
    system = DialogueSystem()
    
    # Generate rapid interruptions
    interruptions = [
        {"turn": i, "text": "Give me an example"}
        for i in range(2, 50, 3)
    ]
    
    dialogue = system.process_with_interruptions(
        'tests/fixtures/chapter1.pdf',
        interruptions
    )
    
    roles = [t['role'] for t in dialogue]
    oscillations = detect_oscillation(roles)
    
    assert oscillations == 0, "Oscillation detected under interruptions!"

def test_convergence_time():
    """Verify system converges quickly after interruption"""
    
    system = DialogueSystem()
    interruptions = [{"turn": 5, "text": "Explain more"}]
    
    dialogue = system.process_with_interruptions(
        'tests/fixtures/sample.pdf',
        interruptions
    )
    
    # Find convergence turn (when roles stabilize)
    interruption_turn = 5
    roles_after = [t['role'] for t in dialogue[interruption_turn:]]
    
    # Should stabilize within 5 turns
    # (Implementation depends on bounded delay)
    # Check that within 5 turns, roles are cycling through queue normally
    # (Test logic depends on specific implementation)
```

### Test Suite 3: Pedagogical Alignment

```python
# tests/validation/test_pedagogical_alignment.py

def test_vygotsky_zpd_alignment():
    """Verify dialogue aligns with ZPD principles"""
    
    system = DialogueSystem()
    dialogue = system.process('tests/fixtures/introductory_chapter.pdf')
    
    # Extract role sequences per segment
    segments = {}
    for turn in dialogue:
        seg_id = turn['segment_id']
        if seg_id not in segments:
            segments[seg_id] = []
        segments[seg_id].append(turn['role'])
    
    # Check ZPD principles
    for seg_id, roles in segments.items():
        # Principle 1: Scaffolding (Explainer before Challenger)
        if 'Explainer' in roles and 'Challenger' in roles:
            exp_idx = roles.index('Explainer')
            chal_idx = roles.index('Challenger')
            assert exp_idx < chal_idx, f"Scaffolding violated in {seg_id}"
        
        # Principle 2: Accessible roles present
        accessible = {'Summarizer', 'Example-Generator'}
        assert any(r in roles for r in accessible), \
               f"Missing accessible roles in {seg_id}"

def test_bloom_taxonomy_progression():
    """Verify roles progress through Bloom's taxonomy"""
    
    # Bloom's levels: Remember → Understand → Apply → Analyze → Evaluate
    # Roles mapped:
    # - Explainer: Understand
    # - Example-Generator: Apply
    # - Challenger: Analyze/Evaluate
    # - Summarizer: Remember/Understand
    
    system = DialogueSystem()
    dialogue = system.process('tests/fixtures/complex_chapter.pdf')
    
    # Check that within each segment, there's cognitive progression
    # (Simplified check for MVP)
    segments = {}
    for turn in dialogue:
        seg_id = turn['segment_id']
        if seg_id not in segments:
            segments[seg_id] = []
        segments[seg_id].append(turn['role'])
    
    for roles in segments.values():
        # Should have diverse cognitive levels
        unique_roles = set(roles)
        assert len(unique_roles) >= 3, "Insufficient cognitive diversity"
```

---

## Performance Tests

```python
# tests/performance/test_performance.py

import pytest
from time import time

def test_document_processing_speed():
    """Verify document processing completes in reasonable time"""
    
    start = time()
    text = load_document('tests/fixtures/large_doc.pdf')
    headings = detect_headings(text)
    segmenter = SemanticSegmenter()
    units = segmenter.segment_document(text, headings)
    elapsed = time() - start
    
    assert elapsed < 10.0, f"Processing took {elapsed}s (>10s limit)"

def test_role_assignment_speed():
    """Verify role assignment is fast"""
    
    segment = create_large_segment()
    engine = RoleAssignmentEngine()
    
    start = time()
    for _ in range(100):
        engine.assign_roles(segment)
    elapsed = time() - start
    
    avg_time = elapsed / 100
    assert avg_time < 0.1, f"Average assignment time: {avg_time}s"

def test_turn_generation_speed():
    """Verify turn generation meets performance target"""
    
    rqsm = setup_test_rqsm()
    
    start = time()
    rqsm.state.transition_lock = 0
    turn = rqsm.advance()
    elapsed = time() - start
    
    # Excluding LLM call (mocked)
    assert elapsed < 1.0, f"Turn generation took {elapsed}s"

@pytest.mark.benchmark
def test_end_to_end_performance(benchmark):
    """Benchmark complete dialogue generation"""
    
    system = DialogueSystem()
    
    result = benchmark(system.process, 'tests/fixtures/chapter1.pdf')
    
    # Should complete in reasonable time
    # (Actual threshold depends on LLM speed)
    assert benchmark.stats.mean < 60.0  # 60s average
```

---

## Test Data

### Fixtures Required

```
tests/fixtures/
├── sample.txt                 # Simple text file
├── sample.pdf                 # Basic PDF (3-5 pages)
├── chapter1.pdf              # Academic chapter (10-15 pages)
├── complex_chapter.pdf       # Technical content
├── introductory_chapter.pdf  # Introductory content
├── large_doc.pdf             # Large document (50+ pages)
├── multipage.pdf             # Multi-page test
├── unicode.txt               # UTF-8 encoding test
└── malformed.pdf             # Edge case testing
```

### Mock Data Generators

```python
# tests/conftest.py - Shared fixtures

import pytest

@pytest.fixture
def create_test_segment():
    """Factory for creating test semantic units"""
    def _create(
        text="Test content here.",
        section="body",
        word_count=None
    ):
        return SemanticUnit(
            id="TEST_S1",
            title="Test Segment",
            text=text,
            document_section=section,
            position=0,
            similarity_score=0.85,
            word_count=word_count or len(text.split()),
            metadata={}
        )
    return _create

@pytest.fixture
def create_test_turn():
    """Factory for creating test turns"""
    def _create():
        return Turn(
            turn_number=1,
            segment_id="S1",
            role=get_role(RoleType.EXPLAINER),
            message="Test message",
            metadata={}
        )
    return _create
```

---

## Test Execution Plan

### Daily Testing (During Development)

```bash
# Run unit tests only
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=app --cov-report=html

# Run specific module tests
pytest tests/unit/test_rqsm.py -v
```

### Weekly Integration Testing

```bash
# Run all integration tests
pytest tests/integration/ -v

# Include performance tests
pytest tests/ --benchmark-only
```

### Pre-Milestone Validation

```bash
# Run full test suite
pytest tests/ -v --cov=app

# Run validation tests specifically
pytest tests/validation/ -v --maxfail=1
```

### Final Testing (Week 12)

```bash
# Complete test suite with reports
pytest tests/ -v --cov=app --cov-report=html --cov-report=term

# Generate test report
pytest tests/ --html=test_report.html --self-contained-html

# Run only critical validation tests
pytest tests/validation/ -v -m critical
```

---

## Success Metrics Summary

| Test Category | Target | Measurement |
|--------------|--------|-------------|
| Unit Tests | 100% pass | pytest results |
| Integration Tests | 100% pass | pytest results |
| Code Coverage | ≥80% | pytest-cov |
| Determinism | 100% reproducibility | Validation tests |
| Stability | 0 oscillations | Validation tests |
| Intent Classification | ≥85% accuracy | Classification tests |
| Performance | <5s per turn | Performance tests |
| Pedagogical Alignment | ≥85% ZPD alignment | Validation tests |

---

## Conclusion

This comprehensive testing strategy ensures:

1. **Quality**: All components thoroughly tested
2. **Determinism**: Reproducibility validated at every level
3. **Stability**: No oscillations or unstable behavior
4. **Performance**: Meets speed requirements
5. **Pedagogical Soundness**: Aligns with learning theory

The test suite provides confidence that the RQSM-Engine meets all capstone requirements and technical specifications.
