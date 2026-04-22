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
    
    # Hard formatting rules injected into every prompt. The LLM otherwise
    # defaults to textbook-style markdown output (headings, bullet lists,
    # bolded terms), which kills the "study group chat" feel.
    FORMAT_RULES = (
        "FORMATTING RULES (follow strictly):\n"
        "- You are ONE voice in a small study group. Speak only as yourself — "
        "do NOT write lines for the Student, the Explainer, the Challenger, or "
        "any other role. Do NOT prefix your reply with your own name. "
        "Output only your single spoken turn.\n"
        "- Plain prose only. No markdown, no headings (#, ##), no bold (**text**), "
        "no bullet points, no numbered lists.\n"
        "- No preamble like 'Sure!' or 'Great question!'. Just speak.\n"
        "- End your reply on a complete sentence."
    )

    def build_prompt(
        self,
        context: str,
        user_input: Optional[str] = None,
        history: Optional[str] = None,
        *,
        reply_style: str = "auto",
        group_transcript: Optional[List[Dict[str, str]]] = None,
        other_role_names: Optional[List[str]] = None,
    ) -> str:
        """Build a prompt sized for a specific slot in the group conversation.

        Parameters
        ----------
        context : str
            The semantic-unit text for the current topic.
        user_input : Optional[str]
            The student's most recent message, if any. Triggers "reply" style
            when reply_style is "auto".
        history : Optional[str]
            Multi-turn conversation history (across units / earlier in the
            session). Rendered under "Earlier in the session:".
        reply_style : str
            One of:
              - "open"   : you open this topic (2-3 sentences + small hook).
              - "chime"  : you chime in right after another role spoke. React
                           in 1-2 sentences, possibly naming them.
              - "reply"  : you reply to the student's most recent message as
                           the primary responder (2-4 sentences).
              - "reply_chime" : you chime in briefly after the primary replied
                                to the student (1-2 sentences).
              - "wrap"   : wrap-up nudge to move on (1 sentence, offers to
                           move to the next topic).
              - "auto"   : pick "reply" if user_input else "open".
        group_transcript : Optional[List[{"role": str, "text": str}]]
            What the other voices in the group have just said THIS turn (for
            opener or reply_chime). Renders under "So far in this discussion:".
        other_role_names : Optional[List[str]]
            Names of the other voices in the group. Used to tell the LLM it
            MAY name-drop them ("Explainer said X") but MUST NOT write lines
            for them.
        """
        if reply_style == "auto":
            reply_style = "reply" if user_input else "open"

        parts: List[str] = [
            self.system_prompt,
            "",
            self.FORMAT_RULES,
        ]

        if other_role_names:
            others = ", ".join(other_role_names)
            parts.extend(
                [
                    "",
                    f"The other voices in the group right now are: {others}. "
                    f"You may reference them by name (e.g. '{other_role_names[0]} said X, "
                    f"but…'). You must NEVER write a line on their behalf. Only speak as "
                    f"{self.name}.",
                ]
            )

        parts.extend(["", self.instruction, "", "Topic (from the study material):", context.strip()])

        if history:
            parts.extend(["", "Earlier in the session:", history.strip()])

        if group_transcript:
            transcript_lines = [
                f"{t['role']}: {t['text'].strip()}"
                for t in group_transcript
                if t.get("text")
            ]
            if transcript_lines:
                parts.extend(
                    ["", "So far in this discussion (same topic, same turn):", "\n".join(transcript_lines)]
                )

        if user_input:
            parts.extend(["", f'The student just said: "{user_input.strip()}"'])

        # Style-specific closing instructions.
        if reply_style == "open":
            parts.extend(
                [
                    "",
                    f"Open this topic as {self.name}. Two or three short sentences. Stay in your "
                    "role. End by leaving a small conversational thread the next voice (or the "
                    "student) can pick up — either a question or a light invitation.",
                ]
            )
        elif reply_style == "chime":
            parts.extend(
                [
                    "",
                    f"You are chiming in right after the previous voice. Speak as {self.name} for "
                    "ONE or TWO short sentences that react to what was just said. "
                    "Do NOT re-explain the topic. If it fits naturally, address the previous voice "
                    "by name. Finish on a complete sentence.",
                ]
            )
        elif reply_style == "reply":
            parts.extend(
                [
                    "",
                    f"Reply to the student as {self.name} in two to four short sentences. "
                    "Speak directly to what they said. Do not repeat your previous turn and do "
                    "not write for any other role. End with either a complete thought or a short "
                    "check-in question.",
                ]
            )
        elif reply_style == "reply_chime":
            parts.extend(
                [
                    "",
                    f"You are chiming in after the main reply to the student. Speak as {self.name} "
                    "for ONE short sentence (maybe two). Add one fresh angle — a contrast, a quick "
                    "example, a clarifying question — don't restate what was already said. "
                    "You may name-drop the previous voice if it helps.",
                ]
            )
        elif reply_style == "wrap":
            parts.extend(
                [
                    "",
                    f"You are wrapping up this topic as {self.name}. In ONE short sentence, "
                    "gently suggest moving on (e.g. 'I think we've got this one — ready for the "
                    "next?'). No summary, no recap.",
                ]
            )

        parts.extend(["", f"{self.name}:"])
        return "\n".join(parts)
    
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
                "You are the Explainer in a small study group. You're the friend who breaks ideas "
                "down in plain language so they click. You speak casually, like you're across the "
                "table from the student, not reading from a textbook."
            ),
            instruction=(
                "Explain the core idea in plain words. One main point per turn, not a whole overview. "
                "If a quick everyday comparison helps, use one short one. End by leaving a small "
                "opening for the student (e.g. 'make sense so far?')."
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
            temperature=0.6,
            max_tokens=180,
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
                "You are the Challenger in a small study group. You're the friend who kindly "
                "pokes at ideas to see if they hold up. You sound curious, never sarcastic."
            ),
            instruction=(
                "Pick one soft spot in what the student said (or in the topic) and ask one "
                "pointed question about it. Don't list multiple questions. Keep it warm and "
                "short — you're prodding, not interrogating."
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
            temperature=0.6,
            max_tokens=160,
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
                "You are the Summarizer in a small study group. You're the friend who can "
                "compress an idea into the one line that actually matters."
            ),
            instruction=(
                "State the core takeaway in one or two plain sentences. No lists, no recaps "
                "of every subpoint. End with a short check-in like 'does that track?'."
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
            temperature=0.5,
            max_tokens=140,
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
                "You are the Example-Generator in a small study group. You're the friend who "
                "drops a quick 'oh, like when…' example to make the abstract idea click."
            ),
            instruction=(
                "Give ONE concrete, everyday example that illustrates the idea. Don't list "
                "several. Keep it to a sentence or two, then ask if that fits what they had "
                "in mind."
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
            temperature=0.7,
            max_tokens=160,
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
                "You are the Misconception-Spotter in a small study group. You're the friend "
                "who notices when something sounds almost right but isn't, and gently corrects it."
            ),
            instruction=(
                "Name ONE specific thing people commonly get wrong about this topic, then "
                "give the quick correction. Keep the tone kind and casual, not preachy."
            ),
            priority_keywords=[
                "misconception", "misconceptions", "mistake", "error", "confuse", "wrong",
                "common error", "pitfall", "misunderstand", "clarify",
                "distinguish", "difference", "versus", "vs", "common mistake"
            ],
            avoid_keywords=[
                "example", "summarize", "overview", "detail", "explain how"
            ],
            temperature=0.55,
            max_tokens=160,
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
