"""
Role Templates Module
Defines the 5 pedagogical roles with prompts and metadata
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
from loguru import logger


class RoleType(Enum):
    """Enumeration of available pedagogical roles"""
    EXPLAINER = "Explainer"
    CHALLENGER = "Challenger"
    SUMMARIZER = "Summarizer"
    EXAMPLE_GENERATOR = "Example-Generator"
    MISCONCEPTION_SPOTTER = "Misconception-Spotter"


@dataclass
class RoleTemplate:
    """
    Template for a pedagogical role.
    
    Attributes:
        name: Role name (e.g., "Explainer")
        role_type: RoleType enum value
        system_prompt: Base system prompt for the role
        instruction: Specific instructions for generating responses
        priority_keywords: Keywords that indicate this role should be prioritized
        avoid_keywords: Keywords that indicate this role should be avoided
        temperature: Suggested temperature for generation (0.0-1.0)
        max_tokens: Suggested max tokens for responses
        metadata: Additional role-specific metadata
    """
    name: str
    role_type: RoleType
    system_prompt: str
    instruction: str
    priority_keywords: List[str]
    avoid_keywords: List[str]
    temperature: float = 0.0
    max_tokens: int = 500
    metadata: Optional[Dict] = None
    
    def build_prompt(self, context: str, user_input: Optional[str] = None) -> str:
        """
        Build complete prompt for LLM generation.
        
        Args:
            context: Document context/semantic unit text
            user_input: Optional user question or input
            
        Returns:
            Complete formatted prompt
        """
        prompt = f"""{self.system_prompt}

{self.instruction}

Context:
{context}
"""
        
        if user_input:
            prompt += f"\n\nUser Question: {user_input}\n\n{self.name}:"
        else:
            prompt += f"\n\n{self.name}:"
        
        return prompt
    
    def __repr__(self) -> str:
        return f"RoleTemplate(name='{self.name}', type={self.role_type.value})"


class RoleTemplateLibrary:
    """
    Library of all available role templates.
    Provides access to the 5 pedagogical roles.
    """
    
    def __init__(self):
        """Initialize role template library"""
        self._templates: Dict[RoleType, RoleTemplate] = {}
        self._initialize_templates()
        logger.info(f"RoleTemplateLibrary initialized with {len(self._templates)} roles")
    
    def _initialize_templates(self):
        """Initialize all role templates"""
        
        # Role 1: Explainer
        self._templates[RoleType.EXPLAINER] = RoleTemplate(
            name="Explainer",
            role_type=RoleType.EXPLAINER,
            system_prompt=(
                "You are the Explainer, a patient and clear educator. "
                "Your role is to break down complex concepts into understandable parts, "
                "provide clear definitions, and explain 'how' and 'why' things work. "
                "Use simple language and build understanding step-by-step."
            ),
            instruction=(
                "Explain the following concept clearly and thoroughly. "
                "Focus on:\n"
                "- Breaking down complex ideas into simpler components\n"
                "- Providing clear definitions and explanations\n"
                "- Using analogies or comparisons when helpful\n"
                "- Ensuring the explanation is accessible to learners"
            ),
            priority_keywords=[
                "explain", "definition", "meaning",
                "understand", "concept", "basics", "fundamental", "principle",
                "what is", "how does", "tell me about"
            ],
            avoid_keywords=[
                "challenge", "question", "critique", "example", "instance",
                "misconception", "mistake", "error", "summary", "overview"
            ],
            temperature=0.0,
            max_tokens=500,
            metadata={
                "color": "#4CAF50",
                "icon": "💡",
                "priority": 1,
                "zpd_level": "foundational"
            }
        )
        
        # Role 2: Challenger
        self._templates[RoleType.CHALLENGER] = RoleTemplate(
            name="Challenger",
            role_type=RoleType.CHALLENGER,
            system_prompt=(
                "You are the Challenger, a critical thinker who encourages deeper analysis. "
                "Your role is to question assumptions, probe for edge cases, "
                "stimulate critical thinking, and push learners beyond surface understanding. "
                "Ask thought-provoking questions without being confrontational."
            ),
            instruction=(
                "Challenge the learner's understanding by:\n"
                "- Asking probing questions about the concept\n"
                "- Identifying assumptions that should be questioned\n"
                "- Presenting edge cases or limitations\n"
                "- Encouraging deeper critical analysis\n"
                "- Pushing beyond surface-level understanding"
            ),
            priority_keywords=[
                "limitation", "limitations", "edge case", "alternative",
                "critique", "challenge", "deeper", "analysis",
                "implications", "consequences", "trade-off", "assume",
                "why not", "what if", "consider"
            ],
            avoid_keywords=[
                "explain", "define", "summarize", "example", "instance",
                "misconception", "mistake", "basic", "simple"
            ],
            temperature=0.1,
            max_tokens=400,
            metadata={
                "color": "#FF9800",
                "icon": "🤔",
                "priority": 2,
                "zpd_level": "advanced"
            }
        )
        
        # Role 3: Summarizer
        self._templates[RoleType.SUMMARIZER] = RoleTemplate(
            name="Summarizer",
            role_type=RoleType.SUMMARIZER,
            system_prompt=(
                "You are the Summarizer, skilled at distilling complex information. "
                "Your role is to synthesize key points, create concise overviews, "
                "and help learners see the big picture. "
                "Extract and organize the most important information efficiently."
            ),
            instruction=(
                "Provide a clear, concise summary by:\n"
                "- Identifying and extracting key points\n"
                "- Organizing information logically\n"
                "- Highlighting the most important concepts\n"
                "- Creating a coherent overview\n"
                "- Using bullet points or structured format when helpful"
            ),
            priority_keywords=[
                "summary", "summarize", "overview", "key points", "main idea",
                "briefly", "concise", "recap", "synthesize", "gist",
                "takeaway", "essence", "core"
            ],
            avoid_keywords=[
                "detail", "explain", "depth", "challenge", "question",
                "example", "instance", "misconception", "elaborate"
            ],
            temperature=0.0,
            max_tokens=300,
            metadata={
                "color": "#2196F3",
                "icon": "📋",
                "priority": 3,
                "zpd_level": "review"
            }
        )
        
        # Role 4: Example-Generator
        self._templates[RoleType.EXAMPLE_GENERATOR] = RoleTemplate(
            name="Example-Generator",
            role_type=RoleType.EXAMPLE_GENERATOR,
            system_prompt=(
                "You are the Example-Generator, adept at creating concrete illustrations. "
                "Your role is to provide real-world examples, use cases, and practical applications "
                "that make abstract concepts tangible. "
                "Create clear, relevant examples that reinforce understanding."
            ),
            instruction=(
                "Generate concrete examples by:\n"
                "- Providing real-world applications or use cases\n"
                "- Creating practical illustrations of the concept\n"
                "- Using familiar contexts when possible\n"
                "- Showing multiple examples if helpful\n"
                "- Making abstract concepts concrete and relatable"
            ),
            priority_keywords=[
                "example", "instance", "case", "application", "use case",
                "scenario", "practical", "real-world", "demonstrate",
                "illustrate", "show", "sample", "analogy"
            ],
            avoid_keywords=[
                "define", "explain", "theory", "challenge", "question",
                "summarize", "overview", "misconception", "mistake"
            ],
            temperature=0.2,
            max_tokens=450,
            metadata={
                "color": "#9C27B0",
                "icon": "💼",
                "priority": 2,
                "zpd_level": "application"
            }
        )
        
        # Role 5: Misconception-Spotter
        self._templates[RoleType.MISCONCEPTION_SPOTTER] = RoleTemplate(
            name="Misconception-Spotter",
            role_type=RoleType.MISCONCEPTION_SPOTTER,
            system_prompt=(
                "You are the Misconception-Spotter, vigilant about common errors. "
                "Your role is to identify typical misunderstandings, correct faulty assumptions, "
                "and clarify confusing points before they become ingrained. "
                "Be gentle but clear in addressing misconceptions."
            ),
            instruction=(
                "Address potential misconceptions by:\n"
                "- Identifying common misunderstandings about this concept\n"
                "- Explaining why these misconceptions occur\n"
                "- Providing clear corrections\n"
                "- Distinguishing between similar but different concepts\n"
                "- Preventing confusion before it develops"
            ),
            priority_keywords=[
                "misconception", "misconceptions", "mistake", "error", "confuse", "wrong",
                "common error", "pitfall", "misunderstand", "clarify",
                "distinguish", "difference", "versus", "vs", "common mistake"
            ],
            avoid_keywords=[
                "example", "summarize", "overview", "detail", "explain how"
            ],
            temperature=0.0,
            max_tokens=400,
            metadata={
                "color": "#F44336",
                "icon": "⚠️",
                "priority": 3,
                "zpd_level": "corrective"
            }
        )
    
    def get_role(self, role_type: RoleType) -> RoleTemplate:
        """
        Get role template by type.
        
        Args:
            role_type: RoleType enum value
            
        Returns:
            RoleTemplate instance
            
        Raises:
            KeyError: If role type not found
        """
        if role_type not in self._templates:
            raise KeyError(f"Role type {role_type} not found in library")
        
        return self._templates[role_type]
    
    def get_role_by_name(self, name: str) -> Optional[RoleTemplate]:
        """
        Get role template by name (case-insensitive).
        
        Args:
            name: Role name (e.g., "Explainer", "explainer")
            
        Returns:
            RoleTemplate instance or None if not found
        """
        name_lower = name.lower()
        
        for role_type, template in self._templates.items():
            if template.name.lower() == name_lower:
                return template
        
        return None
    
    def get_all_roles(self) -> List[RoleTemplate]:
        """
        Get all role templates.
        
        Returns:
            List of all RoleTemplate instances
        """
        return list(self._templates.values())
    
    def get_role_names(self) -> List[str]:
        """
        Get names of all available roles.
        
        Returns:
            List of role names
        """
        return [template.name for template in self._templates.values()]
    
    def find_best_role_for_keywords(self, text: str) -> Optional[RoleTemplate]:
        """
        Find the best role based on keyword matching in text.
        
        Args:
            text: Text to analyze (user input, question, etc.)
            
        Returns:
            Best matching RoleTemplate or None
        """
        text_lower = text.lower()
        
        # Score each role based on keyword matches
        scores = {}
        
        for role_type, template in self._templates.items():
            score = 0
            
            # Add points for priority keywords
            for keyword in template.priority_keywords:
                if keyword in text_lower:
                    score += 2
            
            # Subtract points for avoid keywords
            for keyword in template.avoid_keywords:
                if keyword in text_lower:
                    score -= 1
            
            scores[role_type] = score
        
        # Find role with highest score
        if scores:
            best_role_type = max(scores, key=scores.get)
            if scores[best_role_type] > 0:
                logger.debug(f"Best role for text: {self._templates[best_role_type].name} (score: {scores[best_role_type]})")
                return self._templates[best_role_type]
        
        return None


# Global instance
role_library = RoleTemplateLibrary()
