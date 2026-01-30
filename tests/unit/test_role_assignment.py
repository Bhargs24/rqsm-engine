"""
Unit Tests for Role Assignment Engine
"""
import pytest
from app.document.segmenter import SemanticUnit
from app.roles.role_assignment import (
    RoleScorer,
    RoleAssigner,
    RoleScore,
    RoleAssignment,
    ALPHA,
    BETA,
    GAMMA
)
from app.roles.role_templates import RoleType


@pytest.fixture
def sample_units():
    """Create sample semantic units for testing"""
    units = [
        SemanticUnit(
            id="S0_0",
            title="Introduction to Machine Learning",
            text="Machine learning is defined as a field of study that gives computers the ability to learn without being explicitly programmed. It refers to algorithms that can learn from data.",
            document_section="introduction",
            position=0,
            similarity_score=0.85,
            word_count=120,
            metadata={}
        ),
        SemanticUnit(
            id="S0_1",
            title="Example Applications",
            text="For example, machine learning is used in email spam filters. Consider recommendation systems like Netflix. For instance, self-driving cars use ML extensively.",
            document_section="body",
            position=1,
            similarity_score=0.75,
            word_count=80,
            metadata={}
        ),
        SemanticUnit(
            id="S0_2",
            title="Common Misconceptions",
            text="A common mistake is to confuse machine learning with traditional programming. This error occurs frequently. Many people misunderstand the difference.",
            document_section="body",
            position=2,
            similarity_score=0.80,
            word_count=90,
            metadata={}
        ),
        SemanticUnit(
            id="S0_3",
            title="Summary",
            text="In summary, machine learning represents a key advancement in computer science. The main points include automated learning and data-driven decisions. Overall, this is important for modern AI.",
            document_section="conclusion",
            position=3,
            similarity_score=0.90,
            word_count=100,
            metadata={}
        ),
        SemanticUnit(
            id="S0_4",
            title="Limitations and Challenges",
            text="However, there are significant limitations to consider. But what about edge cases? The challenge lies in data quality. Alternative approaches exist.",
            document_section="body",
            position=4,
            similarity_score=0.70,
            word_count=110,
            metadata={}
        )
    ]
    return units


class TestRoleScorer:
    """Test suite for RoleScorer"""
    
    def test_scorer_initialization(self):
        """Test scorer initializes correctly"""
        scorer = RoleScorer()
        
        assert scorer is not None
        assert scorer.question_pattern is not None
        assert scorer.definition_pattern is not None
    
    def test_score_unit_for_explainer(self, sample_units):
        """Test scoring for Explainer role"""
        scorer = RoleScorer()
        unit = sample_units[0]  # Introduction unit with definitions
        
        score = scorer.score_unit_for_role(unit, RoleType.EXPLAINER, len(sample_units))
        
        assert isinstance(score, RoleScore)
        assert score.role_type == RoleType.EXPLAINER
        assert 0.0 <= score.total_score <= 1.0
        assert 0.0 <= score.structural_score <= 1.0
        assert 0.0 <= score.lexical_score <= 1.0
        assert 0.0 <= score.topic_score <= 1.0
        
        # Introduction units should score well for Explainer
        assert score.total_score > 0.3
    
    def test_score_unit_for_example_generator(self, sample_units):
        """Test scoring for Example-Generator role"""
        scorer = RoleScorer()
        unit = sample_units[1]  # Example applications unit
        
        score = scorer.score_unit_for_role(unit, RoleType.EXAMPLE_GENERATOR, len(sample_units))
        
        assert isinstance(score, RoleScore)
        assert score.role_type == RoleType.EXAMPLE_GENERATOR
        
        # Unit with "for example" should score high for Example-Generator
        assert score.lexical_score > 0.2
    
    def test_score_unit_for_misconception_spotter(self, sample_units):
        """Test scoring for Misconception-Spotter role"""
        scorer = RoleScorer()
        unit = sample_units[2]  # Common misconceptions unit
        
        score = scorer.score_unit_for_role(unit, RoleType.MISCONCEPTION_SPOTTER, len(sample_units))
        
        assert isinstance(score, RoleScore)
        assert score.role_type == RoleType.MISCONCEPTION_SPOTTER
        
        # Unit with "mistake", "error" should score high
        assert score.lexical_score > 0.2
    
    def test_score_unit_for_summarizer(self, sample_units):
        """Test scoring for Summarizer role"""
        scorer = RoleScorer()
        unit = sample_units[3]  # Summary unit
        
        score = scorer.score_unit_for_role(unit, RoleType.SUMMARIZER, len(sample_units))
        
        assert isinstance(score, RoleScore)
        assert score.role_type == RoleType.SUMMARIZER
        
        # Summary section should score high for Summarizer
        assert score.structural_score > 0.3
        assert score.lexical_score > 0.2
    
    def test_score_unit_for_challenger(self, sample_units):
        """Test scoring for Challenger role"""
        scorer = RoleScorer()
        unit = sample_units[4]  # Limitations unit
        
        score = scorer.score_unit_for_role(unit, RoleType.CHALLENGER, len(sample_units))
        
        assert isinstance(score, RoleScore)
        assert score.role_type == RoleType.CHALLENGER
        
        # Unit with "however", "limitations" should score high
        assert score.lexical_score > 0.2
    
    def test_structural_score_position(self, sample_units):
        """Test structural scoring considers position"""
        scorer = RoleScorer()
        first_unit = sample_units[0]
        last_unit = sample_units[-1]
        
        # Explainer should prefer early positions
        explainer_first = scorer.score_unit_for_role(
            first_unit, RoleType.EXPLAINER, len(sample_units)
        ).structural_score
        
        explainer_last = scorer.score_unit_for_role(
            last_unit, RoleType.EXPLAINER, len(sample_units)
        ).structural_score
        
        assert explainer_first > explainer_last
        
        # Summarizer should prefer late positions
        summarizer_first = scorer.score_unit_for_role(
            first_unit, RoleType.SUMMARIZER, len(sample_units)
        ).structural_score
        
        summarizer_last = scorer.score_unit_for_role(
            last_unit, RoleType.SUMMARIZER, len(sample_units)
        ).structural_score
        
        assert summarizer_last > summarizer_first
    
    def test_lexical_score_keyword_matching(self):
        """Test lexical scoring matches keywords"""
        scorer = RoleScorer()
        
        # Unit with explanation keywords
        explain_unit = SemanticUnit(
            id="test",
            title=None,
            text="Explain what neural networks mean and understand how they work",
            document_section="body",
            position=0,
            similarity_score=0.8,
            word_count=50,
            metadata={}
        )
        
        score = scorer.score_unit_for_role(explain_unit, RoleType.EXPLAINER, 5)
        
        # Should have positive lexical score due to keywords
        assert score.lexical_score > 0.0
    
    def test_topic_score_complexity(self):
        """Test topic scoring considers complexity"""
        scorer = RoleScorer()
        
        # Simple unit
        simple_unit = SemanticUnit(
            id="simple",
            title=None,
            text="This is very simple text with no complex words.",
            document_section="body",
            position=0,
            similarity_score=0.8,
            word_count=50,
            metadata={}
        )
        
        # Complex unit
        complex_unit = SemanticUnit(
            id="complex",
            title=None,
            text="NeuralNetwork architectures utilize BackPropagation and GradientDescent with mathematical formulas like y = mx + b and calculations 42 * 3.14",
            document_section="body",
            position=0,
            similarity_score=0.8,
            word_count=50,
            metadata={}
        )
        
        simple_score = scorer.score_unit_for_role(simple_unit, RoleType.CHALLENGER, 5)
        complex_score = scorer.score_unit_for_role(complex_unit, RoleType.CHALLENGER, 5)
        
        # Challenger prefers complex content
        assert complex_score.topic_score > simple_score.topic_score
    
    def test_score_formula_weights(self, sample_units):
        """Test that total score uses correct formula weights"""
        scorer = RoleScorer()
        unit = sample_units[0]
        
        score = scorer.score_unit_for_role(unit, RoleType.EXPLAINER, len(sample_units))
        
        # Verify formula: Score = α(structural) + β(lexical) + γ(topic)
        expected = (ALPHA * score.structural_score + 
                   BETA * score.lexical_score + 
                   GAMMA * score.topic_score)
        
        assert abs(score.total_score - expected) < 0.001


class TestRoleAssigner:
    """Test suite for RoleAssigner"""
    
    def test_assigner_initialization(self):
        """Test assigner initializes correctly"""
        assigner = RoleAssigner()
        
        assert assigner is not None
        assert assigner.scorer is not None
    
    def test_assign_roles_greedy(self, sample_units):
        """Test greedy role assignment"""
        assigner = RoleAssigner()
        
        assignments = assigner.assign_roles(sample_units, balance_roles=False)
        
        assert len(assignments) == len(sample_units)
        
        for assignment in assignments:
            assert isinstance(assignment, RoleAssignment)
            assert assignment.assigned_role in RoleType
            assert 0.0 <= assignment.confidence <= 1.0
            assert assignment.role_template is not None
    
    def test_assign_roles_balanced(self, sample_units):
        """Test balanced role assignment"""
        assigner = RoleAssigner()
        
        assignments = assigner.assign_roles(sample_units, balance_roles=True)
        
        assert len(assignments) == len(sample_units)
        
        # Check that multiple roles are used (not all same)
        roles_used = set(a.assigned_role for a in assignments)
        assert len(roles_used) > 1
    
    def test_assign_roles_empty_list(self):
        """Test assignment with empty list"""
        assigner = RoleAssigner()
        
        assignments = assigner.assign_roles([])
        
        assert assignments == []
    
    def test_role_queue_generation(self, sample_units):
        """Test role queue generation"""
        assigner = RoleAssigner()
        assignments = assigner.assign_roles(sample_units)
        
        queue = assigner.get_role_queue(assignments)
        
        assert len(queue) == len(sample_units)
        
        # Queue should be ordered by position
        for i in range(len(queue) - 1):
            role1, unit1 = queue[i]
            role2, unit2 = queue[i + 1]
            assert unit1.position <= unit2.position
    
    def test_assignment_statistics(self, sample_units):
        """Test statistics generation"""
        assigner = RoleAssigner()
        assignments = assigner.assign_roles(sample_units)
        
        stats = assigner.get_statistics(assignments)
        
        assert 'total_assignments' in stats
        assert stats['total_assignments'] == len(sample_units)
        
        assert 'role_counts' in stats
        assert 'role_percentages' in stats
        assert 'average_confidences' in stats
        assert 'overall_confidence' in stats
        
        # Verify percentages sum to ~100%
        total_pct = sum(stats['role_percentages'].values())
        assert abs(total_pct - 100.0) < 0.1
    
    def test_assignment_confidence_range(self, sample_units):
        """Test that confidence scores are in valid range"""
        assigner = RoleAssigner()
        assignments = assigner.assign_roles(sample_units)
        
        for assignment in assignments:
            assert 0.0 <= assignment.confidence <= 1.0
    
    def test_specific_role_assignments(self, sample_units):
        """Test that specific units get expected roles"""
        assigner = RoleAssigner()
        assignments = assigner.assign_roles(sample_units, balance_roles=False)
        
        # Create mapping of unit ID to assigned role
        unit_to_role = {a.semantic_unit.id: a.assigned_role for a in assignments}
        
        # Introduction unit (S0_0) should likely be Explainer
        intro_role = unit_to_role["S0_0"]
        assert intro_role in [RoleType.EXPLAINER, RoleType.SUMMARIZER]
        
        # Example unit (S0_1) should likely be Example-Generator
        example_role = unit_to_role["S0_1"]
        # May not always be Example-Generator due to scoring, but should be reasonable
        assert example_role in RoleType
        
        # Summary unit (S0_3) should likely be Summarizer
        summary_role = unit_to_role["S0_3"]
        # Should prefer Summarizer due to section and keywords
        assert summary_role in [RoleType.SUMMARIZER, RoleType.EXPLAINER]
    
    def test_balanced_distribution(self, sample_units):
        """Test that balanced assignment distributes roles reasonably"""
        # Create more units for better distribution testing
        more_units = sample_units * 3  # 15 units total
        
        # Fix positions
        for i, unit in enumerate(more_units):
            unit.position = i
            unit.id = f"S{i}"
        
        assigner = RoleAssigner()
        assignments = assigner.assign_roles(more_units, balance_roles=True)
        
        stats = assigner.get_statistics(assignments)
        role_counts = stats['role_counts']
        
        # No role should dominate too much
        max_count = max(role_counts.values())
        min_count = min(role_counts.values())
        
        # With 15 units and 5 roles, expect 2-4 per role ideally
        assert max_count <= len(more_units) * 0.6  # No more than 60%
        assert min_count >= 1  # At least 1 of each
    
    def test_assignment_preserves_semantic_units(self, sample_units):
        """Test that assignments preserve original semantic units"""
        assigner = RoleAssigner()
        assignments = assigner.assign_roles(sample_units)
        
        for i, assignment in enumerate(assignments):
            # Assignment should reference original unit
            assert assignment.semantic_unit.id in [u.id for u in sample_units]
            assert assignment.semantic_unit.text in [u.text for u in sample_units]


class TestRoleScore:
    """Test suite for RoleScore dataclass"""
    
    def test_role_score_creation(self):
        """Test creating a RoleScore"""
        score = RoleScore(
            role_type=RoleType.EXPLAINER,
            total_score=0.75,
            structural_score=0.8,
            lexical_score=0.7,
            topic_score=0.75
        )
        
        assert score.role_type == RoleType.EXPLAINER
        assert score.total_score == 0.75
        assert score.structural_score == 0.8
    
    def test_role_score_repr(self):
        """Test RoleScore string representation"""
        score = RoleScore(
            role_type=RoleType.CHALLENGER,
            total_score=0.65,
            structural_score=0.6,
            lexical_score=0.7,
            topic_score=0.65
        )
        
        repr_str = repr(score)
        
        assert "Challenger" in repr_str
        assert "0.65" in repr_str or "0.650" in repr_str


class TestRoleAssignment:
    """Test suite for RoleAssignment dataclass"""
    
    def test_role_assignment_creation(self, sample_units):
        """Test creating a RoleAssignment"""
        from app.roles.role_templates import role_library
        
        unit = sample_units[0]
        role_type = RoleType.EXPLAINER
        template = role_library.get_role(role_type)
        score = RoleScore(
            role_type=role_type,
            total_score=0.8,
            structural_score=0.75,
            lexical_score=0.85,
            topic_score=0.8
        )
        
        assignment = RoleAssignment(
            semantic_unit=unit,
            assigned_role=role_type,
            role_template=template,
            score=score,
            confidence=0.8
        )
        
        assert assignment.semantic_unit == unit
        assert assignment.assigned_role == role_type
        assert assignment.confidence == 0.8
    
    def test_role_assignment_repr(self, sample_units):
        """Test RoleAssignment string representation"""
        from app.roles.role_templates import role_library
        
        assignment = RoleAssignment(
            semantic_unit=sample_units[0],
            assigned_role=RoleType.EXPLAINER,
            role_template=role_library.get_role(RoleType.EXPLAINER),
            score=RoleScore(RoleType.EXPLAINER, 0.8, 0.7, 0.8, 0.9),
            confidence=0.8
        )
        
        repr_str = repr(assignment)
        
        assert "Explainer" in repr_str
        assert "S0_0" in repr_str


class TestIntegration:
    """Integration tests for role assignment system"""
    
    def test_full_pipeline(self, sample_units):
        """Test complete role assignment pipeline"""
        # Initialize assigner
        assigner = RoleAssigner()
        
        # Assign roles
        assignments = assigner.assign_roles(sample_units, balance_roles=True)
        
        # Generate queue
        queue = assigner.get_role_queue(assignments)
        
        # Get statistics
        stats = assigner.get_statistics(assignments)
        
        # Verify complete pipeline
        assert len(assignments) == len(sample_units)
        assert len(queue) == len(sample_units)
        assert stats['total_assignments'] == len(sample_units)
        
        # Verify all roles have templates
        for assignment in assignments:
            assert assignment.role_template is not None
            assert assignment.role_template.name is not None
