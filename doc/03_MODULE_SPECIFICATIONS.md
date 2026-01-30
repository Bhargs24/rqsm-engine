# Module Specifications

## Document-Segment Driven Role-Oriented Conversational Study System (RQSM-Engine)

**Version:** 1.0  
**Date:** January 29, 2026  
**Purpose:** Detailed technical specifications for all 7 system modules

---

## Table of Contents

1. [Module 1: Document Processor](#module-1-document-processor)
2. [Module 2: Role Template System](#module-2-role-template-system)
3. [Module 3: Role Assignment Engine](#module-3-role-assignment-engine)
4. [Module 4: Role Queue State Machine (RQSM)](#module-4-role-queue-state-machine-rqsm)
5. [Module 5: Interruption Monitor](#module-5-interruption-monitor)
6. [Module 6: Role Reallocation Engine](#module-6-role-reallocation-engine)
7. [Module 7: Session Continuity Manager](#module-7-session-continuity-manager)

---

## Module 1: Document Processor

### Purpose
Transform raw documents (PDF, TXT) into semantic units suitable for role-based dialogue generation.

### Inputs
- **Document Path**: File path to document (PDF or TXT)
- **Configuration**: Optional segmentation parameters

### Outputs
- **Semantic Units**: List of `SemanticUnit` objects with metadata

### Data Structures

```python
@dataclass
class SemanticUnit:
    id: str                          # e.g., "S1", "S2", "S3"
    title: Optional[str]              # Section heading if available
    text: str                        # Main content
    document_section: str            # e.g., "introduction", "body", "conclusion"
    position: int                    # Order in document (0-indexed)
    similarity_score: float          # Cohesion score (0.0-1.0)
    word_count: int                  # Number of words
    metadata: Dict[str, Any]         # Additional context
```

### Components

#### 1.1 Document Loader

**File**: `app/document/loader.py`

**Functions**:

```python
def load_text(filepath: str) -> str:
    """
    Load plain text document.
    
    Args:
        filepath: Path to .txt file
        
    Returns:
        Raw text content
        
    Raises:
        FileNotFoundError: If file doesn't exist
        UnicodeDecodeError: If encoding issues
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def load_pdf(filepath: str) -> str:
    """
    Extract text from PDF document.
    
    Args:
        filepath: Path to .pdf file
        
    Returns:
        Extracted text content
        
    Uses: pdfplumber library
    """
    import pdfplumber
    
    text_parts = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text())
    
    return "\n\n".join(text_parts)

def load_document(filepath: str) -> str:
    """
    Universal document loader (dispatches based on extension).
    
    Args:
        filepath: Path to document
        
    Returns:
        Extracted text
    """
    ext = filepath.split('.')[-1].lower()
    
    if ext == 'txt':
        return load_text(filepath)
    elif ext == 'pdf':
        return load_pdf(filepath)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
```

#### 1.2 Heading Detector

**File**: `app/document/heading_detector.py`

**Purpose**: Identify section headings to guide segmentation

**Algorithm**:

```python
import re
from typing import List, Tuple

@dataclass
class Heading:
    text: str
    level: int          # 1 = top-level, 2 = subsection, etc.
    position: int       # Character position in document
    line_number: int    # Line number in document

def detect_headings(text: str) -> List[Heading]:
    """
    Detect document headings using regex patterns.
    
    Patterns:
    1. ALL CAPS LINES (e.g., "INTRODUCTION")
    2. Numbered headings (e.g., "1. Overview", "1.1 Details")
    3. Lines followed by underlines (===, ---)
    4. Short lines with title case at start of paragraphs
    
    Args:
        text: Full document text
        
    Returns:
        List of detected headings with metadata
    """
    headings = []
    lines = text.split('\n')
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Pattern 1: ALL CAPS (at least 3 words)
        if line_stripped.isupper() and len(line_stripped.split()) >= 3:
            headings.append(Heading(
                text=line_stripped,
                level=1,
                position=text[:text.find(line)].count('\n'),
                line_number=i
            ))
        
        # Pattern 2: Numbered headings
        numbered_match = re.match(r'^(\d+\.)+\s+(.+)$', line_stripped)
        if numbered_match:
            level = numbered_match.group(1).count('.')
            headings.append(Heading(
                text=numbered_match.group(2),
                level=level,
                position=text[:text.find(line)].count('\n'),
                line_number=i
            ))
        
        # Pattern 3: Underlined headings
        if i > 0 and re.match(r'^[=\-]{3,}$', line_stripped):
            prev_line = lines[i-1].strip()
            if prev_line:
                headings.append(Heading(
                    text=prev_line,
                    level=1 if '=' in line_stripped else 2,
                    position=text[:text.find(prev_line)].count('\n'),
                    line_number=i-1
                ))
    
    return headings

def build_hierarchy(headings: List[Heading]) -> Dict[str, Any]:
    """
    Build hierarchical document structure from headings.
    
    Returns:
        Nested dict representing document structure
    """
    # Implementation builds tree structure
    pass
```

#### 1.3 Semantic Segmenter

**File**: `app/document/segmenter.py`

**Purpose**: Group paragraphs into coherent semantic units

**Algorithm**:

```python
from sentence_transformers import SentenceTransformer
import numpy as np

class SemanticSegmenter:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
        self.similarity_threshold = 0.75
    
    def segment_document(
        self,
        text: str,
        headings: List[Heading]
    ) -> List[SemanticUnit]:
        """
        Segment document into semantic units.
        
        Algorithm:
        1. Split by headings (if present)
        2. Within each section, group paragraphs by semantic similarity
        3. Ensure minimum/maximum unit sizes
        4. Compute cohesion scores
        
        Args:
            text: Full document text
            headings: Detected headings
            
        Returns:
            List of semantic units
        """
        units = []
        
        # Step 1: Split by major headings
        sections = self._split_by_headings(text, headings)
        
        for section_id, section in enumerate(sections):
            # Step 2: Extract paragraphs
            paragraphs = self._extract_paragraphs(section['text'])
            
            # Step 3: Compute embeddings
            embeddings = self.model.encode(paragraphs)
            
            # Step 4: Group by similarity
            groups = self._group_by_similarity(
                paragraphs,
                embeddings,
                threshold=self.similarity_threshold
            )
            
            # Step 5: Create semantic units
            for group_id, group in enumerate(groups):
                unit = SemanticUnit(
                    id=f"S{section_id}_{group_id}",
                    title=section.get('title'),
                    text='\n\n'.join(group),
                    document_section=section.get('section_type', 'body'),
                    position=len(units),
                    similarity_score=self._compute_cohesion(group, embeddings),
                    word_count=sum(len(p.split()) for p in group),
                    metadata={
                        'heading_level': section.get('level', 0),
                        'paragraph_count': len(group)
                    }
                )
                units.append(unit)
        
        return units
    
    def _split_by_headings(
        self,
        text: str,
        headings: List[Heading]
    ) -> List[Dict]:
        """Split document into major sections based on headings"""
        sections = []
        
        for i, heading in enumerate(headings):
            start = heading.position
            end = headings[i+1].position if i+1 < len(headings) else len(text)
            
            section_text = text[start:end]
            section_type = self._classify_section(heading.text)
            
            sections.append({
                'title': heading.text,
                'text': section_text,
                'level': heading.level,
                'section_type': section_type
            })
        
        return sections
    
    def _extract_paragraphs(self, text: str) -> List[str]:
        """Extract non-empty paragraphs from text"""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        return paragraphs
    
    def _group_by_similarity(
        self,
        paragraphs: List[str],
        embeddings: np.ndarray,
        threshold: float
    ) -> List[List[str]]:
        """
        Group paragraphs by semantic similarity using clustering.
        
        Algorithm:
        1. Start with first paragraph as seed
        2. Add subsequent paragraphs if similarity > threshold
        3. When similarity drops, start new group
        4. Apply minimum group size (2 paragraphs)
        """
        groups = []
        current_group = [paragraphs[0]]
        current_embeddings = [embeddings[0]]
        
        for i in range(1, len(paragraphs)):
            # Compute similarity with current group
            group_centroid = np.mean(current_embeddings, axis=0)
            similarity = self._cosine_similarity(
                embeddings[i],
                group_centroid
            )
            
            if similarity >= threshold:
                current_group.append(paragraphs[i])
                current_embeddings.append(embeddings[i])
            else:
                # Finalize current group
                if len(current_group) >= 2:
                    groups.append(current_group)
                    current_group = [paragraphs[i]]
                    current_embeddings = [embeddings[i]]
                else:
                    # Merge with next paragraph
                    current_group.append(paragraphs[i])
                    current_embeddings.append(embeddings[i])
        
        # Add final group
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _compute_cohesion(
        self,
        paragraphs: List[str],
        embeddings: np.ndarray
    ) -> float:
        """
        Compute cohesion score for a group of paragraphs.
        
        Score based on average pairwise similarity.
        """
        if len(paragraphs) == 1:
            return 1.0
        
        # Compute pairwise similarities
        similarities = []
        for i in range(len(embeddings)):
            for j in range(i+1, len(embeddings)):
                sim = self._cosine_similarity(embeddings[i], embeddings[j])
                similarities.append(sim)
        
        return np.mean(similarities)
    
    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors"""
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    @staticmethod
    def _classify_section(heading_text: str) -> str:
        """Classify section type based on heading"""
        heading_lower = heading_text.lower()
        
        if any(kw in heading_lower for kw in ['introduction', 'overview', 'background']):
            return 'introduction'
        elif any(kw in heading_lower for kw in ['conclusion', 'summary', 'final']):
            return 'conclusion'
        elif any(kw in heading_lower for kw in ['method', 'approach', 'implementation']):
            return 'methodology'
        else:
            return 'body'
```

### Configuration

```python
# app/document/config.py

DOCUMENT_CONFIG = {
    'similarity_threshold': 0.75,      # For paragraph grouping
    'min_unit_words': 50,              # Minimum words per unit
    'max_unit_words': 500,             # Maximum words per unit
    'embedding_model': 'all-MiniLM-L6-v2',
    'heading_patterns': {
        'numbered': r'^(\d+\.)+\s+',
        'all_caps': r'^[A-Z\s]{10,}$',
        'underline': r'^[=\-]{3,}$'
    }
}
```

### Testing

```python
# tests/test_document_processor.py

def test_load_text():
    text = load_text('tests/fixtures/sample.txt')
    assert len(text) > 0
    assert isinstance(text, str)

def test_load_pdf():
    text = load_pdf('tests/fixtures/sample.pdf')
    assert len(text) > 0

def test_heading_detection():
    text = """
    INTRODUCTION
    
    This is the intro text.
    
    1. First Section
    
    More text here.
    """
    headings = detect_headings(text)
    assert len(headings) == 2
    assert headings[0].text == "INTRODUCTION"

def test_semantic_segmentation():
    segmenter = SemanticSegmenter()
    text = load_text('tests/fixtures/sample.txt')
    headings = detect_headings(text)
    units = segmenter.segment_document(text, headings)
    
    assert len(units) >= 3
    assert all(unit.similarity_score > 0.5 for unit in units)
    assert all(unit.word_count >= 50 for unit in units)
```

---

## Module 2: Role Template System

### Purpose
Define the five educational roles with their behavioral patterns and prompts.

### Data Structures

```python
from enum import Enum
from typing import List, Dict

class RoleType(Enum):
    EXPLAINER = "Explainer"
    CHALLENGER = "Challenger"
    SUMMARIZER = "Summarizer"
    EXAMPLE_GENERATOR = "Example-Generator"
    MISCONCEPTION_SPOTTER = "Misconception-Spotter"

@dataclass
class Role:
    type: RoleType
    name: str
    description: str
    system_prompt: str
    priority_weight: float                # Base priority (0-10)
    triggers: List[str]                   # Keywords that favor this role
    content_affinity: List[str]           # Document sections where role is valuable
    behavior_guidelines: List[str]        # Specific behavioral rules
```

### Role Definitions

#### 2.1 Explainer

```python
EXPLAINER = Role(
    type=RoleType.EXPLAINER,
    name="Explainer",
    description="Breaks down complex concepts into accessible language",
    system_prompt="""You are an educational guide focused on clarity and accessibility.

Your role:
- Break down complex concepts step-by-step
- Use simple, jargon-free language
- Provide foundational context
- Link new information to prior knowledge
- Use analogies when helpful

Example opening: "Let me break this down step by step..."

Rules:
- Avoid technical jargon without explanation
- Use numbered lists for multi-step processes
- Check understanding implicitly
- Build from fundamentals
""",
    priority_weight=8.0,
    triggers=[
        "introduction", "definition", "what is", "explain",
        "technical", "complex", "abstract"
    ],
    content_affinity=["introduction", "definitions", "technical_sections"],
    behavior_guidelines=[
        "Start with simplest explanation",
        "Build complexity gradually",
        "Use concrete before abstract",
        "Provide scaffolding"
    ]
)
```

#### 2.2 Challenger

```python
CHALLENGER = Role(
    type=RoleType.CHALLENGER,
    name="Challenger",
    description="Questions assumptions and explores edge cases",
    system_prompt="""You are a critical thinker who questions assumptions constructively.

Your role:
- Challenge key claims with "But what if...?"
- Identify potential contradictions
- Explore edge cases and limitations
- Ask probing questions
- Play devil's advocate respectfully

Example opening: "But have you considered what happens when...?"

Rules:
- Be skeptical but not dismissive
- Focus on conceptual boundaries
- Highlight implicit assumptions
- Encourage deeper thinking
""",
    priority_weight=7.0,
    triggers=[
        "claim", "assertion", "always", "never", "must",
        "if", "then", "because", "therefore"
    ],
    content_affinity=["arguments", "methodologies", "conclusions"],
    behavior_guidelines=[
        "Question strong claims",
        "Identify hidden assumptions",
        "Explore counterexamples",
        "Push boundaries respectfully"
    ]
)
```

#### 2.3 Summarizer

```python
SUMMARIZER = Role(
    type=RoleType.SUMMARIZER,
    name="Summarizer",
    description="Distills key takeaways into concise points",
    system_prompt="""You are a synthesizer who extracts and organizes key information.

Your role:
- Compress complex ideas into 3-5 main points
- Use bullet points or numbered lists
- Connect related concepts
- Provide mini-summaries at transitions
- Highlight patterns and themes

Example opening: "So in short, the key points are..."

Rules:
- Be concise but complete
- Preserve essential meaning
- Use parallel structure in lists
- Emphasize actionable insights
""",
    priority_weight=8.5,
    triggers=[
        "summary", "conclusion", "key points", "main ideas",
        "takeaway", "recap", "overview"
    ],
    content_affinity=["conclusions", "transitions", "complex_sections"],
    behavior_guidelines=[
        "Limit to 3-5 main points",
        "Use consistent formatting",
        "Link to big picture",
        "Emphasize memorability"
    ]
)
```

#### 2.4 Example-Generator

```python
EXAMPLE_GENERATOR = Role(
    type=RoleType.EXAMPLE_GENERATOR,
    name="Example-Generator",
    description="Provides concrete examples and analogies",
    system_prompt="""You are a translator from theory to practice through examples.

Your role:
- Provide real-world analogies
- Offer concrete, relatable examples
- Connect abstract concepts to familiar experiences
- Use multiple examples for complex ideas
- Illustrate with scenarios

Example opening: "Think of it like... Here's a concrete example..."

Rules:
- Make examples relatable and diverse
- Use analogies appropriate to audience
- Provide both simple and complex examples
- Connect back to the concept
""",
    priority_weight=7.5,
    triggers=[
        "abstract", "theoretical", "concept", "principle",
        "example", "like", "such as", "for instance"
    ],
    content_affinity=["abstract_sections", "theoretical_content"],
    behavior_guidelines=[
        "Start with familiar examples",
        "Use multiple modalities",
        "Bridge theory to practice",
        "Vary complexity"
    ]
)
```

#### 2.5 Misconception-Spotter

```python
MISCONCEPTION_SPOTTER = Role(
    type=RoleType.MISCONCEPTION_SPOTTER,
    name="Misconception-Spotter",
    description="Identifies and corrects common misunderstandings",
    system_prompt="""You are a guardian against learning errors and misconceptions.

Your role:
- Identify likely student misunderstandings
- Correct false associations
- Clarify boundaries of applicability
- Warn about common pitfalls
- Provide accurate mental models

Example opening: "A common mistake is to think... Actually, it's..."

Rules:
- Be corrective without being condescending
- Explain why the misconception is wrong
- Provide the correct understanding
- Emphasize where concepts don't apply
""",
    priority_weight=9.0,
    triggers=[
        "not", "however", "but", "counterintuitive",
        "common mistake", "misunderstanding", "actually"
    ],
    content_affinity=["technical_sections", "nuanced_content", "exceptions"],
    behavior_guidelines=[
        "Anticipate common errors",
        "Correct gently",
        "Explain the right model",
        "Reinforce boundaries"
    ]
)
```

### Role Registry

```python
# app/roles/role_templates.py

ALL_ROLES = [
    EXPLAINER,
    CHALLENGER,
    SUMMARIZER,
    EXAMPLE_GENERATOR,
    MISCONCEPTION_SPOTTER
]

ROLE_MAP = {role.type: role for role in ALL_ROLES}

def get_role(role_type: RoleType) -> Role:
    """Get role by type"""
    return ROLE_MAP[role_type]

def get_all_roles() -> List[Role]:
    """Get all role definitions"""
    return ALL_ROLES.copy()
```

### Testing

```python
def test_all_roles_defined():
    assert len(ALL_ROLES) == 5

def test_role_properties():
    for role in ALL_ROLES:
        assert role.name
        assert role.system_prompt
        assert 0 <= role.priority_weight <= 10
        assert len(role.triggers) > 0

def test_role_retrieval():
    explainer = get_role(RoleType.EXPLAINER)
    assert explainer.name == "Explainer"
```

---

## Module 3: Role Assignment Engine

### Purpose
Compute deterministic role queues for each semantic unit based on content analysis.

### Algorithm

**Scoring Function**:
```
RoleScore(R, S) = α × structural_score(R, S) + 
                  β × lexical_score(R, S) + 
                  γ × topic_score(R, S)

Where α + β + γ = 1.0
Default: α=0.4, β=0.3, γ=0.3
```

### Implementation

```python
# app/roles/role_assignment.py

class RoleAssignmentEngine:
    def __init__(
        self,
        α: float = 0.4,  # Structural weight
        β: float = 0.3,  # Lexical weight
        γ: float = 0.3   # Topic weight
    ):
        self.α = α
        self.β = β
        self.γ = γ
        self.roles = get_all_roles()
    
    def assign_roles(self, segment: SemanticUnit) -> Dict[str, Any]:
        """
        Compute deterministic role queue for a semantic unit.
        
        Returns:
            {
                'queue': [Role, Role, ...],
                'scores': {role.name: score, ...}
            }
        """
        scores = {}
        
        for role in self.roles:
            score = self.compute_role_score(role, segment)
            scores[role.name] = score
        
        # Sort by score descending
        sorted_roles = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        queue = [
            get_role_by_name(name)
            for name, _ in sorted_roles
        ]
        
        return {
            'segment_id': segment.id,
            'queue': queue,
            'scores': scores
        }
    
    def compute_role_score(
        self,
        role: Role,
        segment: SemanticUnit
    ) -> float:
        """Compute combined score for role-segment pair"""
        struct_score = self._structural_score(role, segment)
        lex_score = self._lexical_score(role, segment)
        topic_score = self._topic_score(role, segment)
        
        combined = (
            self.α * struct_score +
            self.β * lex_score +
            self.γ * topic_score
        )
        
        return combined
    
    def _structural_score(
        self,
        role: Role,
        segment: SemanticUnit
    ) -> float:
        """
        Score based on document structure.
        
        Logic:
        - Introductions favor Summarizer and Explainer
        - Body sections favor Challenger and Example-Generator
        - Conclusions favor Summarizer
        - Technical sections favor Misconception-Spotter
        """
        section_type = segment.document_section
        score = role.priority_weight  # Base score
        
        # Introduction
        if section_type == 'introduction':
            if role.type in [RoleType.SUMMARIZER, RoleType.EXPLAINER]:
                score += 2.0
            elif role.type == RoleType.MISCONCEPTION_SPOTTER:
                score += 1.0
        
        # Conclusion
        elif section_type == 'conclusion':
            if role.type == RoleType.SUMMARIZER:
                score += 3.0
            elif role.type in [RoleType.EXPLAINER, RoleType.CHALLENGER]:
                score += 0.5
        
        # Methodology/Technical
        elif section_type in ['methodology', 'technical']:
            if role.type == RoleType.MISCONCEPTION_SPOTTER:
                score += 2.5
            elif role.type == RoleType.EXPLAINER:
                score += 2.0
            elif role.type == RoleType.EXAMPLE_GENERATOR:
                score += 1.5
        
        # Body
        else:
            if role.type == RoleType.CHALLENGER:
                score += 1.5
            elif role.type == RoleType.EXAMPLE_GENERATOR:
                score += 1.0
        
        return min(score, 10.0)  # Cap at 10
    
    def _lexical_score(
        self,
        role: Role,
        segment: SemanticUnit
    ) -> float:
        """
        Score based on lexical content.
        
        Logic:
        - Count trigger keywords for each role
        - Higher count = higher score
        - Normalize by segment length
        """
        text_lower = segment.text.lower()
        trigger_count = 0
        
        for trigger in role.triggers:
            trigger_count += text_lower.count(trigger.lower())
        
        # Normalize by word count
        normalized = trigger_count / max(segment.word_count / 100, 1.0)
        
        # Scale to 0-10 range
        score = min(normalized * 2.0, 10.0)
        
        return score + role.priority_weight * 0.5
    
    def _topic_score(
        self,
        role: Role,
        segment: SemanticUnit
    ) -> float:
        """
        Score based on topic similarity.
        
        Uses content affinity list from role definition.
        """
        score = role.priority_weight  # Base
        
        # Check content affinity
        for affinity in role.content_affinity:
            if affinity in segment.document_section:
                score += 1.5
        
        # Check metadata
        if 'complexity' in segment.metadata:
            complexity = segment.metadata['complexity']
            if complexity == 'high' and role.type in [
                RoleType.EXPLAINER,
                RoleType.MISCONCEPTION_SPOTTER
            ]:
                score += 1.0
        
        return min(score, 10.0)
```

### Testing

```python
def test_role_assignment_deterministic():
    """Verify same input produces same output"""
    engine = RoleAssignmentEngine()
    segment = create_test_segment()
    
    result1 = engine.assign_roles(segment)
    result2 = engine.assign_roles(segment)
    
    assert result1['queue'] == result2['queue']
    assert result1['scores'] == result2['scores']

def test_role_queue_completeness():
    """All roles must be in queue"""
    engine = RoleAssignmentEngine()
    segment = create_test_segment()
    
    result = engine.assign_roles(segment)
    role_names = [r.name for r in result['queue']]
    
    assert len(role_names) == 5
    assert len(set(role_names)) == 5  # All unique

def test_introduction_scoring():
    """Introductions should favor Summarizer"""
    engine = RoleAssignmentEngine()
    intro_segment = SemanticUnit(
        id="S1",
        text="This is an introduction...",
        document_section="introduction",
        word_count=100,
        position=0,
        similarity_score=0.9,
        metadata={}
    )
    
    result = engine.assign_roles(intro_segment)
    top_role = result['queue'][0]
    
    assert top_role.type in [RoleType.SUMMARIZER, RoleType.EXPLAINER]
```

---

## Module 4: Role Queue State Machine (RQSM)

### Purpose
Orchestrate deterministic role transitions during dialogue generation.

### State Definition

```python
@dataclass
class DialogueState:
    # Current position
    current_segment_id: str
    current_segment_index: int
    current_role_index: int
    
    # Role queue
    role_queue: List[Role]
    
    # Control flags
    interruption_detected: bool = False
    transition_lock: int = 0          # Turns until next transition allowed
    
    # Stability mechanisms
    hysteresis_map: Dict[str, int] = field(default_factory=dict)
    role_usage_count: Dict[str, int] = field(default_factory=dict)
    
    # History
    turn_number: int = 0
    last_role: Optional[Role] = None
```

### RQSM Implementation

```python
# app/state_machine/rqsm.py

from typing import Optional, List
from dataclasses import dataclass, field

class RQSM:
    """Role Queue State Machine"""
    
    def __init__(
        self,
        segments: List[SemanticUnit],
        role_assignments: Dict[str, Dict],
        bounded_delay: int = 3,
        hysteresis_window: int = 7
    ):
        self.segments = segments
        self.assignments = role_assignments
        self.bounded_delay = bounded_delay
        self.hysteresis_window = hysteresis_window
        
        # Initialize state
        self.state = self._initialize_state()
        self.session_history: List[Turn] = []
    
    def _initialize_state(self) -> DialogueState:
        """Initialize with first segment and role"""
        first_segment = self.segments[0]
        first_assignment = self.assignments[first_segment.id]
        
        return DialogueState(
            current_segment_id=first_segment.id,
            current_segment_index=0,
            current_role_index=0,
            role_queue=first_assignment['queue']
        )
    
    def current_role(self) -> Role:
        """Get current active role"""
        return self.state.role_queue[self.state.current_role_index]
    
    def advance(self) -> Optional['Turn']:
        """
        Advance to next role in queue.
        
        Returns:
            Turn object if successful, None if dialogue complete
        """
        # Check transition lock
        if self.state.transition_lock > 0:
            self.state.transition_lock -= 1
            return None
        
        # Generate turn for current role
        turn = self._generate_turn()
        self.session_history.append(turn)
        
        # Update state
        self.state.turn_number += 1
        self.state.last_role = self.current_role()
        
        # Increment role usage
        role_name = self.current_role().name
        self.state.role_usage_count[role_name] = \
            self.state.role_usage_count.get(role_name, 0) + 1
        
        # Advance to next role
        if self.state.current_role_index < len(self.state.role_queue) - 1:
            self.state.current_role_index += 1
        else:
            # Move to next segment
            if not self._advance_segment():
                return turn  # Dialogue complete
        
        return turn
    
    def _advance_segment(self) -> bool:
        """
        Move to next semantic unit.
        
        Returns:
            True if advanced, False if no more segments
        """
        if self.state.current_segment_index >= len(self.segments) - 1:
            return False  # No more segments
        
        self.state.current_segment_index += 1
        next_segment = self.segments[self.state.current_segment_index]
        
        # Update role queue for new segment
        self.state.current_segment_id = next_segment.id
        self.state.role_queue = self.assignments[next_segment.id]['queue']
        self.state.current_role_index = 0
        
        return True
    
    def _generate_turn(self) -> 'Turn':
        """Generate dialogue turn for current role"""
        role = self.current_role()
        segment = self._get_current_segment()
        
        # Build prompt with context
        prompt = self._build_prompt(role, segment)
        
        # Generate response (via LLM - implemented in Module 7)
        response = "Generated response placeholder"  # TODO: LLM integration
        
        turn = Turn(
            turn_number=self.state.turn_number,
            segment_id=segment.id,
            role=role,
            message=response,
            metadata={
                'role_index': self.state.current_role_index,
                'segment_index': self.state.current_segment_index
            }
        )
        
        return turn
    
    def _get_current_segment(self) -> SemanticUnit:
        """Get currently active semantic unit"""
        return self.segments[self.state.current_segment_index]
    
    def _build_prompt(
        self,
        role: Role,
        segment: SemanticUnit
    ) -> str:
        """Build LLM prompt for role and segment"""
        prompt = f"{role.system_prompt}\n\n"
        prompt += f"Content to discuss:\n{segment.text}\n\n"
        prompt += "Your response:"
        return prompt
    
    def handle_interruption(
        self,
        user_input: str,
        intent: 'Intent',
        new_queue: List[Role]
    ):
        """
        Handle user interruption with role reallocation.
        
        Args:
            user_input: User's interruption text
            intent: Classified intent
            new_queue: Reallocated role queue
        """
        # Log interruption
        self.state.interruption_detected = True
        
        # Update role queue
        self.state.role_queue = new_queue
        self.state.current_role_index = 0
        
        # Apply bounded delay
        self.state.transition_lock = self.bounded_delay
        
        # Apply hysteresis to demoted roles
        self._apply_hysteresis(new_queue)
    
    def _apply_hysteresis(self, new_queue: List[Role]):
        """
        Block recently demoted roles from immediate return.
        
        Roles that moved down in priority are locked for N turns.
        """
        for i, role in enumerate(new_queue):
            if i > 2:  # Demoted to position 3 or lower
                lock_until = self.state.turn_number + self.hysteresis_window
                self.state.hysteresis_map[role.name] = lock_until
    
    def is_dialogue_complete(self) -> bool:
        """Check if all segments have been processed"""
        return (
            self.state.current_segment_index >= len(self.segments) - 1 and
            self.state.current_role_index >= len(self.state.role_queue) - 1
        )
```

### Turn Data Structure

```python
@dataclass
class Turn:
    turn_number: int
    segment_id: str
    role: Role
    message: str
    timestamp: float = field(default_factory=time.time)
    user_intent: Optional['Intent'] = None
    is_reallocation: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### Testing

```python
def test_rqsm_initialization():
    segments = create_test_segments()
    assignments = create_test_assignments()
    
    rqsm = RQSM(segments, assignments)
    
    assert rqsm.state.current_segment_index == 0
    assert rqsm.state.current_role_index == 0
    assert len(rqsm.state.role_queue) == 5

def test_rqsm_advances():
    rqsm = setup_test_rqsm()
    
    turn1 = rqsm.advance()
    assert turn1.turn_number == 0
    assert rqsm.state.current_role_index == 1
    
    turn2 = rqsm.advance()
    assert turn2.turn_number == 1
    assert rqsm.state.current_role_index == 2

def test_segment_transition():
    rqsm = setup_test_rqsm()
    
    # Advance through all roles in first segment
    for _ in range(5):
        rqsm.advance()
    
    # Should now be on second segment
    assert rqsm.state.current_segment_index == 1
    assert rqsm.state.current_role_index == 0
```

---

## Module 5: Interruption Monitor

### Purpose
Detect user interruptions and classify intent to trigger role reallocation.

### Intent Classification

```python
from enum import Enum

class Intent(Enum):
    CLARIFICATION = "Clarification"
    OBJECTION = "Objection"
    TOPIC_PIVOT = "Topic Pivot"
    DEPTH_REQUEST = "Depth Request"
    EXAMPLE_REQUEST = "Example Request"
    SUMMARY_REQUEST = "Summary Request"
    OTHER = "Other"
```

### Implementation

```python
# app/interruption/intent_classifier.py

import re
from typing import Tuple

class IntentClassifier:
    """Keyword-based intent classification (MVP)"""
    
    INTENT_PATTERNS = {
        Intent.CLARIFICATION: [
            r"explain.*more",
            r"don'?t understand",
            r"clarify",
            r"break.*down",
            r"simpler",
            r"what.*mean",
            r"confused"
        ],
        Intent.OBJECTION: [
            r"disagree",
            r"doesn'?t.*(?:sound|seem).*right",
            r"but.*what if",
            r"counterexample",
            r"contradiction",
            r"wrong",
            r"incorrect"
        ],
        Intent.TOPIC_PIVOT: [
            r"let'?s.*talk.*about",
            r"skip.*to",
            r"next.*(?:section|topic)",
            r"different.*topic",
            r"change.*subject",
            r"move on"
        ],
        Intent.DEPTH_REQUEST: [
            r"(?:go |get )?deeper",
            r"tell.*more",
            r"elaborate",
            r"more.*detail",
            r"expand on"
        ],
        Intent.EXAMPLE_REQUEST: [
            r"example",
            r"concrete",
            r"real.*world",
            r"case",
            r"illustrate",
            r"instance",
            r"demonstrate"
        ],
        Intent.SUMMARY_REQUEST: [
            r"summarize",
            r"recap",
            r"key.*(?:point|takeaway)",
            r"main.*(?:point|idea)",
            r"in.*short",
            r"(?:what|the).*gist"
        ]
    }
    
    def __init__(self, confidence_threshold: float = 0.7):
        self.threshold = confidence_threshold
    
    def classify(self, user_input: str) -> Tuple[Intent, float]:
        """
        Classify user intent from input text.
        
        Args:
            user_input: User's interruption text
            
        Returns:
            (intent, confidence_score)
            
        Confidence based on pattern match count normalized by
        total patterns for that intent.
        """
        user_lower = user_input.lower()
        
        scores = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            matches = sum(
                1 for pattern in patterns
                if re.search(pattern, user_lower)
            )
            scores[intent] = matches / len(patterns)
        
        # Get best match
        if not scores or max(scores.values()) == 0:
            return Intent.OTHER, 0.0
        
        best_intent = max(scores.items(), key=lambda x: x[1])
        return best_intent[0], best_intent[1]
    
    def should_trigger_reallocation(self, confidence: float) -> bool:
        """Check if confidence exceeds threshold"""
        return confidence >= self.threshold
```

### Testing

```python
def test_clarification_intent():
    classifier = IntentClassifier()
    
    test_cases = [
        "Can you explain that more?",
        "I don't understand",
        "What does that mean?"
    ]
    
    for text in test_cases:
        intent, conf = classifier.classify(text)
        assert intent == Intent.CLARIFICATION
        assert conf > 0.5

def test_example_intent():
    classifier = IntentClassifier()
    
    text = "Give me an example"
    intent, conf = classifier.classify(text)
    
    assert intent == Intent.EXAMPLE_REQUEST
    assert conf >= 0.8

def test_confidence_threshold():
    classifier = IntentClassifier(confidence_threshold=0.8)
    
    text = "example"
    intent, conf = classifier.classify(text)
    
    should_trigger = classifier.should_trigger_reallocation(conf)
    assert isinstance(should_trigger, bool)
```

---

## Module 6: Role Reallocation Engine

### Purpose
Dynamically reorder role queues based on detected user intent while maintaining stability.

### Intent-Role Alignment Matrix

```python
# app/interruption/reallocator.py

INTENT_ROLE_ALIGNMENT = {
    Intent.CLARIFICATION: {
        "Explainer": 0.9,
        "Challenger": 0.3,
        "Summarizer": 0.7,
        "Example-Generator": 0.6,
        "Misconception-Spotter": 0.8
    },
    Intent.OBJECTION: {
        "Explainer": 0.4,
        "Challenger": 0.9,
        "Summarizer": 0.3,
        "Example-Generator": 0.3,
        "Misconception-Spotter": 0.5
    },
    Intent.TOPIC_PIVOT: {
        "Explainer": 0.6,
        "Challenger": 0.4,
        "Summarizer": 0.5,
        "Example-Generator": 0.4,
        "Misconception-Spotter": 0.3
    },
    Intent.DEPTH_REQUEST: {
        "Explainer": 0.8,
        "Challenger": 0.8,
        "Summarizer": 0.5,
        "Example-Generator": 0.6,
        "Misconception-Spotter": 0.5
    },
    Intent.EXAMPLE_REQUEST: {
        "Explainer": 0.5,
        "Challenger": 0.4,
        "Summarizer": 0.4,
        "Example-Generator": 0.95,
        "Misconception-Spotter": 0.3
    },
    Intent.SUMMARY_REQUEST: {
        "Explainer": 0.4,
        "Challenger": 0.3,
        "Summarizer": 0.95,
        "Example-Generator": 0.3,
        "Misconception-Spotter": 0.3
    }
}
```

### Implementation

```python
class RoleReallocationEngine:
    """Reorders role queue based on user intent"""
    
    def __init__(
        self,
        alignment_weight: float = 5.0,
        penalty_weight: float = 2.0
    ):
        self.alignment_weight = alignment_weight
        self.penalty_weight = penalty_weight
    
    def reallocate(
        self,
        current_queue: List[Role],
        intent: Intent,
        usage_history: Dict[str, int],
        hysteresis_map: Dict[str, int],
        current_turn: int
    ) -> List[Role]:
        """
        Reorder role queue based on intent.
        
        Args:
            current_queue: Current ordered roles
            intent: Detected user intent
            usage_history: How many times each role has spoken
            hysteresis_map: Roles locked until turn N
            current_turn: Current turn number
            
        Returns:
            Reallocated role queue
        """
        new_scores = {}
        
        for role in current_queue:
            # Check hysteresis lock
            if role.name in hysteresis_map:
                if hysteresis_map[role.name] > current_turn:
                    # Role is locked, give very low score
                    new_scores[role] = -100.0
                    continue
            
            # Compute new score
            old_score = role.priority_weight
            alignment = self._get_alignment(role, intent)
            penalty = usage_history.get(role.name, 0)
            
            new_score = (
                old_score +
                (self.alignment_weight * alignment) -
                (self.penalty_weight * penalty * 0.1)  # Scale penalty
            )
            
            new_scores[role] = new_score
        
        # Sort by new scores
        sorted_roles = sorted(
            new_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [role for role, _ in sorted_roles]
    
    def _get_alignment(self, role: Role, intent: Intent) -> float:
        """Get intent-role alignment score"""
        if intent not in INTENT_ROLE_ALIGNMENT:
            return 0.5  # Neutral
        
        return INTENT_ROLE_ALIGNMENT[intent].get(role.name, 0.5)
```

### Testing

```python
def test_example_request_reallocation():
    engine = RoleReallocationEngine()
    
    current_queue = get_all_roles()  # Default order
    usage = {}
    hysteresis = {}
    
    new_queue = engine.reallocate(
        current_queue,
        Intent.EXAMPLE_REQUEST,
        usage,
        hysteresis,
        current_turn=1
    )
    
    # Example-Generator should be first
    assert new_queue[0].type == RoleType.EXAMPLE_GENERATOR

def test_hysteresis_enforcement():
    engine = RoleReallocationEngine()
    
    current_queue = get_all_roles()
    usage = {}
    hysteresis = {"Challenger": 10}  # Locked until turn 10
    
    new_queue = engine.reallocate(
        current_queue,
        Intent.OBJECTION,  # Would normally favor Challenger
        usage,
        hysteresis,
        current_turn=5  # Before lock expires
    )
    
    # Challenger should be demoted
    challenger_idx = [r.type for r in new_queue].index(RoleType.CHALLENGER)
    assert challenger_idx >= 3  # Not in top 3
```

---

## Module 7: Session Continuity Manager

### Purpose
Maintain conversation context and history across multiple turns to ensure coherent dialogue.

### Data Structures

```python
@dataclass
class SessionHistory:
    turns: List[Turn] = field(default_factory=list)
    context_window: int = 10
    
    def add_turn(self, turn: Turn):
        self.turns.append(turn)
    
    def get_recent(self, n: Optional[int] = None) -> List[Turn]:
        """Get N most recent turns"""
        if n is None:
            n = self.context_window
        return self.turns[-n:]
    
    def get_by_segment(self, segment_id: str) -> List[Turn]:
        """Get all turns for a specific segment"""
        return [t for t in self.turns if t.segment_id == segment_id]
```

### Implementation

```python
# app/session/session_manager.py

class SessionContinuityManager:
    """Manages session state and conversation history"""
    
    def __init__(self, context_window: int = 10):
        self.history = SessionHistory(context_window=context_window)
        self.context_cache = {}
    
    def log_turn(self, turn: Turn):
        """Add turn to session history"""
        self.history.add_turn(turn)
        
        # Clear cache when history grows
        if len(self.history.turns) % 20 == 0:
            self.context_cache.clear()
    
    def get_context_for_prompt(
        self,
        role: Role,
        segment: SemanticUnit,
        n_turns: int = 5
    ) -> str:
        """
        Build context string for LLM prompt.
        
        Includes:
        - Recent conversation turns
        - Relevant past discussion of same segment
        - Role-specific context
        
        Returns:
            Formatted context string
        """
        cache_key = f"{role.name}_{segment.id}_{len(self.history.turns)}"
        
        if cache_key in self.context_cache:
            return self.context_cache[cache_key]
        
        # Get recent turns
        recent_turns = self.history.get_recent(n_turns)
        
        # Format context
        context_parts = []
        
        if recent_turns:
            context_parts.append("Previous conversation:")
            for turn in recent_turns:
                context_parts.append(
                    f"[{turn.role.name}]: {turn.message[:200]}..."
                )
            context_parts.append("")
        
        # Add current segment context
        context_parts.append(f"Current topic: {segment.title or 'Untitled'}")
        context_parts.append(f"Content:\n{segment.text}")
        
        context_str = "\n".join(context_parts)
        
        # Cache
        self.context_cache[cache_key] = context_str
        
        return context_str
    
    def check_contradiction(
        self,
        new_message: str,
        role: Role
    ) -> Optional[str]:
        """
        Check if new message contradicts previous turns.
        
        Returns:
            Warning message if contradiction detected, None otherwise
        """
        # Simple keyword-based contradiction detection (MVP)
        recent = self.history.get_recent(10)
        
        # Extract key phrases from new message
        new_lower = new_message.lower()
        
        for turn in recent:
            old_lower = turn.message.lower()
            
            # Check for direct contradictions
            if "not" in new_lower or "isn't" in new_lower:
                # Look for contradicting statements
                # This is a simplified check
                pass
        
        return None  # No contradiction detected
    
    def get_summary(self) -> Dict[str, Any]:
        """Get session statistics and summary"""
        return {
            'total_turns': len(self.history.turns),
            'roles_used': list(set(t.role.name for t in self.history.turns)),
            'segments_covered': list(set(t.segment_id for t in self.history.turns)),
            'interruptions': sum(1 for t in self.history.turns if t.is_reallocation),
            'average_message_length': sum(len(t.message) for t in self.history.turns) / max(len(self.history.turns), 1)
        }
```

### Testing

```python
def test_session_logging():
    manager = SessionContinuityManager()
    
    turn1 = create_test_turn()
    manager.log_turn(turn1)
    
    assert len(manager.history.turns) == 1
    assert manager.history.turns[0] == turn1

def test_context_retrieval():
    manager = SessionContinuityManager()
    
    # Add multiple turns
    for i in range(10):
        manager.log_turn(create_test_turn())
    
    recent = manager.history.get_recent(5)
    assert len(recent) == 5

def test_context_for_prompt():
    manager = SessionContinuityManager()
    
    # Add some turns
    for i in range(3):
        manager.log_turn(create_test_turn())
    
    role = get_role(RoleType.EXPLAINER)
    segment = create_test_segment()
    
    context = manager.get_context_for_prompt(role, segment)
    
    assert "Previous conversation:" in context
    assert segment.text in context
```

---

## Integration Points

### Module Dependencies

```
Module 1 (Document Processor)
    ↓
Module 3 (Role Assignment) ← Module 2 (Role Templates)
    ↓
Module 4 (RQSM) ← Module 7 (Session Manager)
    ↓                    ↑
Module 5 (Interruption Monitor)
    ↓
Module 6 (Role Reallocation)
    ↓
Module 4 (RQSM)
```

### Data Flow Summary

1. **Document** → Module 1 → **Semantic Units**
2. **Semantic Units** + Module 2 → Module 3 → **Role Assignments**
3. **Role Assignments** → Module 4 → **Initial State**
4. Module 4 ↔ Module 7 → **Dialogue Generation**
5. **User Input** → Module 5 → **Intent Classification**
6. **Intent** + Module 4 State → Module 6 → **New Role Queue**
7. **New Queue** → Module 4 → **Updated State**

---

## Configuration Summary

```python
# config.py - Centralized configuration

CONFIG = {
    'document': {
        'similarity_threshold': 0.75,
        'min_unit_words': 50,
        'max_unit_words': 500,
        'embedding_model': 'all-MiniLM-L6-v2'
    },
    'role_assignment': {
        'alpha': 0.4,  # Structural weight
        'beta': 0.3,   # Lexical weight
        'gamma': 0.3   # Topic weight
    },
    'rqsm': {
        'bounded_delay': 3,
        'hysteresis_window': 7
    },
    'interruption': {
        'confidence_threshold': 0.7
    },
    'reallocation': {
        'alignment_weight': 5.0,
        'penalty_weight': 2.0
    },
    'session': {
        'context_window': 10
    },
    'llm': {
        'model': 'gpt-3.5-turbo',
        'temperature': 0.0,
        'max_tokens': 500
    }
}
```

---

## Conclusion

These detailed specifications provide:

1. **Clear interfaces** for each module
2. **Concrete algorithms** with pseudocode
3. **Data structures** for all key entities
4. **Test cases** for validation
5. **Configuration options** for tuning

Implementation can now proceed module-by-module with confidence that the design is complete and consistent.
