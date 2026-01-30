"""
Role Assignment Engine
Implements deterministic role-to-segment mapping using scoring algorithms
Formula: Score = α(structural) + β(lexical) + γ(topic)
Where: α=0.4, β=0.3, γ=0.3
"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import re
from loguru import logger

from app.document.segmenter import SemanticUnit
from app.roles.role_templates import RoleType, RoleTemplate, role_library


# Weight constants for scoring formula
ALPHA = 0.4  # Structural weight
BETA = 0.3   # Lexical weight
GAMMA = 0.3  # Topic weight


@dataclass
class RoleScore:
    """Score for a specific role assignment"""
    role_type: RoleType
    total_score: float
    structural_score: float
    lexical_score: float
    topic_score: float
    
    def __repr__(self) -> str:
        return (f"RoleScore({self.role_type.value}: {self.total_score:.3f} "
                f"[S:{self.structural_score:.2f}, L:{self.lexical_score:.2f}, T:{self.topic_score:.2f}])")


@dataclass
class RoleAssignment:
    """Assignment of a role to a semantic unit"""
    semantic_unit: SemanticUnit
    assigned_role: RoleType
    role_template: RoleTemplate
    score: RoleScore
    confidence: float  # 0.0-1.0
    
    def __repr__(self) -> str:
        return (f"RoleAssignment({self.assigned_role.value} -> Unit {self.semantic_unit.id}, "
                f"conf={self.confidence:.2f})")


class RoleScorer:
    """
    Scores semantic units for role suitability using multi-factor analysis.
    
    Scoring Formula: Score = α(structural) + β(lexical) + γ(topic)
    - Structural (α=0.4): Position, section type, length
    - Lexical (β=0.3): Keyword matching, linguistic patterns
    - Topic (γ=0.3): Content relevance, complexity indicators
    """
    
    def __init__(self):
        """Initialize role scorer"""
        self._initialize_patterns()
    
    def _initialize_patterns(self):
        """Initialize regex patterns for lexical analysis"""
        # Question patterns
        self.question_pattern = re.compile(r'\b(what|why|how|when|where|who)\b', re.IGNORECASE)
        
        # Definition patterns
        self.definition_pattern = re.compile(
            r'\b(is defined as|refers to|means|is|are|defined as)\b', re.IGNORECASE
        )
        
        # Example patterns
        self.example_pattern = re.compile(
            r'\b(for example|for instance|such as|e\.g\.|like|consider)\b', re.IGNORECASE
        )
        
        # Misconception patterns
        self.misconception_pattern = re.compile(
            r'\b(mistake|error|misconception|incorrect|wrong|not|confuse|misunderstand)\b',
            re.IGNORECASE
        )
        
        # Summary patterns
        self.summary_pattern = re.compile(
            r'\b(in summary|in conclusion|overall|to summarize|key points|main|important)\b',
            re.IGNORECASE
        )
        
        # Challenge/critical patterns
        self.challenge_pattern = re.compile(
            r'\b(however|but|limitation|issue|problem|challenge|consider|alternative)\b',
            re.IGNORECASE
        )
    
    def score_unit_for_role(
        self,
        unit: SemanticUnit,
        role_type: RoleType,
        total_units: int
    ) -> RoleScore:
        """
        Score a semantic unit for a specific role.
        
        Args:
            unit: Semantic unit to score
            role_type: Role type to score for
            total_units: Total number of units in document
            
        Returns:
            RoleScore with breakdown
        """
        structural = self._compute_structural_score(unit, role_type, total_units)
        lexical = self._compute_lexical_score(unit, role_type)
        topic = self._compute_topic_score(unit, role_type)
        
        total = ALPHA * structural + BETA * lexical + GAMMA * topic
        
        return RoleScore(
            role_type=role_type,
            total_score=total,
            structural_score=structural,
            lexical_score=lexical,
            topic_score=topic
        )
    
    def _compute_structural_score(
        self,
        unit: SemanticUnit,
        role_type: RoleType,
        total_units: int
    ) -> float:
        """
        Compute structural score based on position, section, and length.
        
        Returns: Score in range [0.0, 1.0]
        """
        score = 0.0
        
        # Position score (0.4 weight)
        relative_position = unit.position / max(total_units, 1)
        
        if role_type == RoleType.EXPLAINER:
            # Explainers work best early in document
            score += 0.4 * (1.0 - relative_position)
        
        elif role_type == RoleType.SUMMARIZER:
            # Summarizers work best late in document
            score += 0.4 * relative_position
        
        elif role_type == RoleType.CHALLENGER:
            # Challengers work best in middle sections
            score += 0.4 * (1.0 - abs(0.5 - relative_position) * 2)
        
        else:
            # Example-Generator and Misconception-Spotter neutral on position
            score += 0.2
        
        # Section type score (0.4 weight)
        section = unit.document_section.lower()
        
        if role_type == RoleType.EXPLAINER:
            if section in ['introduction', 'background']:
                score += 0.4
            elif section == 'body':
                score += 0.2
        
        elif role_type == RoleType.SUMMARIZER:
            if section in ['conclusion', 'summary']:
                score += 0.4
            elif section == 'body':
                score += 0.1
        
        elif role_type == RoleType.CHALLENGER:
            if section in ['body', 'methodology', 'discussion']:
                score += 0.4
        
        elif role_type == RoleType.EXAMPLE_GENERATOR:
            if section == 'body':
                score += 0.3
            else:
                score += 0.15
        
        elif role_type == RoleType.MISCONCEPTION_SPOTTER:
            if section in ['body', 'background']:
                score += 0.3
            else:
                score += 0.15
        
        # Length score (0.2 weight)
        word_count = unit.word_count
        
        if role_type == RoleType.SUMMARIZER:
            # Summarizers prefer shorter units
            if word_count < 100:
                score += 0.2
            elif word_count < 200:
                score += 0.1
        
        elif role_type == RoleType.EXPLAINER:
            # Explainers prefer medium-length units
            if 100 <= word_count <= 300:
                score += 0.2
            else:
                score += 0.1
        
        else:
            # Others prefer medium length
            if 50 <= word_count <= 250:
                score += 0.15
            else:
                score += 0.05
        
        return min(score, 1.0)
    
    def _compute_lexical_score(self, unit: SemanticUnit, role_type: RoleType) -> float:
        """
        Compute lexical score based on keyword matching and patterns.
        
        Returns: Score in range [0.0, 1.0]
        """
        text = unit.text.lower()
        score = 0.0
        
        # Get role template for keyword matching
        template = role_library.get_role(role_type)
        
        # Priority keywords (0.5 weight)
        priority_matches = sum(1 for kw in template.priority_keywords if kw.lower() in text)
        priority_ratio = min(priority_matches / 5.0, 1.0)  # Normalize to max 5 matches
        score += 0.5 * priority_ratio
        
        # Avoid keywords penalty (0.2 weight)
        avoid_matches = sum(1 for kw in template.avoid_keywords if kw.lower() in text)
        avoid_penalty = min(avoid_matches / 3.0, 1.0)
        score -= 0.2 * avoid_penalty
        
        # Pattern matching (0.3 weight)
        if role_type == RoleType.EXPLAINER:
            def_matches = len(self.definition_pattern.findall(text))
            score += 0.3 * min(def_matches / 3.0, 1.0)
        
        elif role_type == RoleType.CHALLENGER:
            challenge_matches = len(self.challenge_pattern.findall(text))
            question_matches = len(self.question_pattern.findall(text))
            score += 0.3 * min((challenge_matches + question_matches) / 4.0, 1.0)
        
        elif role_type == RoleType.SUMMARIZER:
            summary_matches = len(self.summary_pattern.findall(text))
            score += 0.3 * min(summary_matches / 2.0, 1.0)
        
        elif role_type == RoleType.EXAMPLE_GENERATOR:
            example_matches = len(self.example_pattern.findall(text))
            score += 0.3 * min(example_matches / 2.0, 1.0)
        
        elif role_type == RoleType.MISCONCEPTION_SPOTTER:
            misc_matches = len(self.misconception_pattern.findall(text))
            score += 0.3 * min(misc_matches / 3.0, 1.0)
        
        return max(0.0, min(score, 1.0))
    
    def _compute_topic_score(self, unit: SemanticUnit, role_type: RoleType) -> float:
        """
        Compute topic score based on content relevance and complexity.
        
        Returns: Score in range [0.0, 1.0]
        """
        text = unit.text.lower()
        score = 0.0
        
        # Complexity indicators (0.4 weight)
        technical_terms = len(re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', unit.text))
        has_numbers = bool(re.search(r'\d+', text))
        has_formulas = bool(re.search(r'[=+\-*/]', text))
        
        complexity = (technical_terms / 10.0 + 
                     (0.2 if has_numbers else 0) + 
                     (0.2 if has_formulas else 0))
        complexity = min(complexity, 1.0)
        
        if role_type == RoleType.EXPLAINER:
            # Explainers prefer moderate complexity
            score += 0.4 * (1.0 - abs(0.5 - complexity) * 2)
        
        elif role_type == RoleType.CHALLENGER:
            # Challengers prefer high complexity
            score += 0.4 * complexity
        
        elif role_type == RoleType.EXAMPLE_GENERATOR:
            # Examples prefer concrete content (moderate complexity)
            score += 0.4 * (1.0 - abs(0.4 - complexity) * 2)
        
        else:
            # Others neutral on complexity
            score += 0.2
        
        # Cohesion score from semantic segmentation (0.3 weight)
        cohesion = unit.similarity_score
        score += 0.3 * cohesion
        
        # Title/heading presence (0.3 weight)
        if unit.title:
            title_lower = unit.title.lower()
            
            if role_type == RoleType.EXPLAINER:
                if any(w in title_lower for w in ['introduction', 'overview', 'what', 'basics']):
                    score += 0.3
            
            elif role_type == RoleType.SUMMARIZER:
                if any(w in title_lower for w in ['summary', 'conclusion', 'recap']):
                    score += 0.3
            
            elif role_type == RoleType.EXAMPLE_GENERATOR:
                if any(w in title_lower for w in ['example', 'application', 'case']):
                    score += 0.3
            
            elif role_type == RoleType.MISCONCEPTION_SPOTTER:
                if any(w in title_lower for w in ['pitfall', 'error', 'mistake', 'caution']):
                    score += 0.3
            
            else:
                score += 0.1
        
        return min(score, 1.0)


class RoleAssigner:
    """
    Assigns roles to semantic units using deterministic scoring.
    Implements role queue generation and assignment logic.
    """
    
    def __init__(self):
        """Initialize role assigner"""
        self.scorer = RoleScorer()
        logger.info("RoleAssigner initialized")
    
    def assign_roles(
        self,
        semantic_units: List[SemanticUnit],
        balance_roles: bool = True
    ) -> List[RoleAssignment]:
        """
        Assign roles to all semantic units.
        
        Args:
            semantic_units: List of semantic units from document
            balance_roles: If True, balance role distribution across document
            
        Returns:
            List of role assignments
        """
        if not semantic_units:
            return []
        
        assignments = []
        total_units = len(semantic_units)
        
        # Score each unit for each role
        all_scores: Dict[str, Dict[RoleType, RoleScore]] = {}
        
        for unit in semantic_units:
            unit_scores = {}
            for role_type in RoleType:
                score = self.scorer.score_unit_for_role(unit, role_type, total_units)
                unit_scores[role_type] = score
            all_scores[unit.id] = unit_scores
        
        # Assign roles based on scores
        if balance_roles:
            assignments = self._assign_with_balancing(semantic_units, all_scores)
        else:
            assignments = self._assign_greedy(semantic_units, all_scores)
        
        logger.info(f"Assigned roles to {len(assignments)} semantic units")
        return assignments
    
    def _assign_greedy(
        self,
        semantic_units: List[SemanticUnit],
        all_scores: Dict[str, Dict[RoleType, RoleScore]]
    ) -> List[RoleAssignment]:
        """
        Greedy assignment: assign best-scoring role to each unit.
        
        Args:
            semantic_units: List of units
            all_scores: Scores for all units and roles
            
        Returns:
            List of role assignments
        """
        assignments = []
        
        for unit in semantic_units:
            unit_scores = all_scores[unit.id]
            
            # Find best role
            best_role = max(unit_scores.keys(), key=lambda r: unit_scores[r].total_score)
            best_score = unit_scores[best_role]
            
            # Compute confidence (normalized score)
            confidence = best_score.total_score
            
            # Get role template
            template = role_library.get_role(best_role)
            
            assignment = RoleAssignment(
                semantic_unit=unit,
                assigned_role=best_role,
                role_template=template,
                score=best_score,
                confidence=confidence
            )
            assignments.append(assignment)
        
        return assignments
    
    def _assign_with_balancing(
        self,
        semantic_units: List[SemanticUnit],
        all_scores: Dict[str, Dict[RoleType, RoleScore]]
    ) -> List[RoleAssignment]:
        """
        Balanced assignment: ensure reasonable distribution of roles.
        
        Args:
            semantic_units: List of units
            all_scores: Scores for all units and roles
            
        Returns:
            List of role assignments
        """
        assignments = []
        total_units = len(semantic_units)
        
        # Target distribution (can be adjusted)
        target_ratios = {
            RoleType.EXPLAINER: 0.30,
            RoleType.CHALLENGER: 0.20,
            RoleType.SUMMARIZER: 0.15,
            RoleType.EXAMPLE_GENERATOR: 0.20,
            RoleType.MISCONCEPTION_SPOTTER: 0.15
        }
        
        # Track role counts
        role_counts = {role: 0 for role in RoleType}
        
        # Create list of (unit, best_role, score) tuples
        unit_preferences = []
        for unit in semantic_units:
            unit_scores = all_scores[unit.id]
            best_role = max(unit_scores.keys(), key=lambda r: unit_scores[r].total_score)
            best_score = unit_scores[best_role]
            unit_preferences.append((unit, best_role, best_score))
        
        # Sort by score (highest first)
        unit_preferences.sort(key=lambda x: x[2].total_score, reverse=True)
        
        # Assign roles with balancing
        for unit, preferred_role, score in unit_preferences:
            # Check if preferred role is over-allocated
            current_ratio = role_counts[preferred_role] / max(len(assignments), 1)
            target_ratio = target_ratios[preferred_role]
            
            if current_ratio <= target_ratio or len(assignments) == 0:
                # Assign preferred role
                assigned_role = preferred_role
            else:
                # Find best alternative role that's under-allocated
                unit_scores = all_scores[unit.id]
                alternative_roles = sorted(
                    unit_scores.keys(),
                    key=lambda r: unit_scores[r].total_score,
                    reverse=True
                )
                
                assigned_role = preferred_role
                for role in alternative_roles:
                    current_ratio = role_counts[role] / max(len(assignments), 1)
                    if current_ratio < target_ratios[role]:
                        assigned_role = role
                        break
            
            # Create assignment
            final_score = all_scores[unit.id][assigned_role]
            template = role_library.get_role(assigned_role)
            
            assignment = RoleAssignment(
                semantic_unit=unit,
                assigned_role=assigned_role,
                role_template=template,
                score=final_score,
                confidence=final_score.total_score
            )
            assignments.append(assignment)
            role_counts[assigned_role] += 1
        
        # Log distribution
        logger.debug(f"Role distribution: {role_counts}")
        
        return assignments
    
    def get_role_queue(
        self,
        assignments: List[RoleAssignment]
    ) -> List[Tuple[RoleType, SemanticUnit]]:
        """
        Generate role queue for sequential dialogue.
        
        Args:
            assignments: List of role assignments
            
        Returns:
            Ordered list of (role, unit) tuples
        """
        # Sort by semantic unit position (document order)
        sorted_assignments = sorted(assignments, key=lambda a: a.semantic_unit.position)
        
        queue = [(a.assigned_role, a.semantic_unit) for a in sorted_assignments]
        
        logger.info(f"Generated role queue with {len(queue)} entries")
        return queue
    
    def get_statistics(self, assignments: List[RoleAssignment]) -> Dict:
        """
        Get statistics about role assignments.
        
        Args:
            assignments: List of role assignments
            
        Returns:
            Dictionary with statistics
        """
        if not assignments:
            return {}
        
        # Count roles
        role_counts = {role: 0 for role in RoleType}
        for assignment in assignments:
            role_counts[assignment.assigned_role] += 1
        
        # Average confidence per role
        role_confidences = {role: [] for role in RoleType}
        for assignment in assignments:
            role_confidences[assignment.assigned_role].append(assignment.confidence)
        
        avg_confidences = {
            role: sum(scores) / len(scores) if scores else 0.0
            for role, scores in role_confidences.items()
        }
        
        # Overall statistics
        total = len(assignments)
        avg_confidence = sum(a.confidence for a in assignments) / total
        
        return {
            'total_assignments': total,
            'role_counts': role_counts,
            'role_percentages': {role: count / total * 100 for role, count in role_counts.items()},
            'average_confidences': avg_confidences,
            'overall_confidence': avg_confidence
        }
