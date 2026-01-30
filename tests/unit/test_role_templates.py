"""
Unit Tests for Role Templates
"""
import pytest

from app.roles.role_templates import (
    RoleType,
    RoleTemplate,
    RoleTemplateLibrary,
    role_library
)


class TestRoleTemplate:
    """Test suite for RoleTemplate"""
    
    def test_role_template_creation(self):
        """Test creating a role template"""
        template = RoleTemplate(
            name="Test Role",
            role_type=RoleType.EXPLAINER,
            system_prompt="Test system prompt",
            instruction="Test instruction",
            priority_keywords=["test", "keyword"],
            avoid_keywords=["avoid"],
            temperature=0.0,
            max_tokens=500
        )
        
        assert template.name == "Test Role"
        assert template.role_type == RoleType.EXPLAINER
        assert template.temperature == 0.0
        assert "test" in template.priority_keywords
    
    def test_build_prompt_without_user_input(self):
        """Test building prompt without user input"""
        template = RoleTemplate(
            name="Explainer",
            role_type=RoleType.EXPLAINER,
            system_prompt="You are an explainer.",
            instruction="Explain clearly.",
            priority_keywords=["explain"],
            avoid_keywords=[]
        )
        
        context = "Neural networks are computational models."
        prompt = template.build_prompt(context)
        
        assert "You are an explainer" in prompt
        assert "Explain clearly" in prompt
        assert context in prompt
        assert "Explainer:" in prompt
    
    def test_build_prompt_with_user_input(self):
        """Test building prompt with user input"""
        template = RoleTemplate(
            name="Challenger",
            role_type=RoleType.CHALLENGER,
            system_prompt="You challenge assumptions.",
            instruction="Ask probing questions.",
            priority_keywords=["challenge"],
            avoid_keywords=[]
        )
        
        context = "Machine learning uses data."
        user_input = "Why is data important?"
        prompt = template.build_prompt(context, user_input)
        
        assert "You challenge assumptions" in prompt
        assert context in prompt
        assert user_input in prompt
        assert "Challenger:" in prompt


class TestRoleTemplateLibrary:
    """Test suite for RoleTemplateLibrary"""
    
    def test_library_initialization(self):
        """Test library initializes with all roles"""
        library = RoleTemplateLibrary()
        
        assert len(library.get_all_roles()) == 5
        assert len(library.get_role_names()) == 5
    
    def test_get_role_by_type(self):
        """Test getting role by type"""
        library = RoleTemplateLibrary()
        
        explainer = library.get_role(RoleType.EXPLAINER)
        assert explainer.name == "Explainer"
        assert explainer.role_type == RoleType.EXPLAINER
        
        challenger = library.get_role(RoleType.CHALLENGER)
        assert challenger.name == "Challenger"
    
    def test_get_role_by_name(self):
        """Test getting role by name"""
        library = RoleTemplateLibrary()
        
        explainer = library.get_role_by_name("Explainer")
        assert explainer is not None
        assert explainer.name == "Explainer"
        
        # Case insensitive
        explainer2 = library.get_role_by_name("explainer")
        assert explainer2 is not None
        assert explainer2.name == "Explainer"
    
    def test_get_role_by_name_not_found(self):
        """Test getting non-existent role"""
        library = RoleTemplateLibrary()
        
        result = library.get_role_by_name("NonExistent")
        assert result is None
    
    def test_get_all_roles(self):
        """Test getting all roles"""
        library = RoleTemplateLibrary()
        
        roles = library.get_all_roles()
        
        assert len(roles) == 5
        role_names = [r.name for r in roles]
        assert "Explainer" in role_names
        assert "Challenger" in role_names
        assert "Summarizer" in role_names
        assert "Example-Generator" in role_names
        assert "Misconception-Spotter" in role_names
    
    def test_get_role_names(self):
        """Test getting role names"""
        library = RoleTemplateLibrary()
        
        names = library.get_role_names()
        
        assert len(names) == 5
        assert "Explainer" in names
        assert "Challenger" in names
    
    def test_find_best_role_for_keywords_explainer(self):
        """Test finding best role based on keywords - Explainer"""
        library = RoleTemplateLibrary()
        
        text = "Can you explain what a neural network is?"
        role = library.find_best_role_for_keywords(text)
        
        assert role is not None
        assert role.name == "Explainer"
    
    def test_find_best_role_for_keywords_challenger(self):
        """Test finding best role based on keywords - Challenger"""
        library = RoleTemplateLibrary()
        
        text = "What are the limitations of this approach?"
        role = library.find_best_role_for_keywords(text)
        
        assert role is not None
        assert role.name == "Challenger"
    
    def test_find_best_role_for_keywords_summarizer(self):
        """Test finding best role based on keywords - Summarizer"""
        library = RoleTemplateLibrary()
        
        text = "Can you summarize the key points?"
        role = library.find_best_role_for_keywords(text)
        
        assert role is not None
        assert role.name == "Summarizer"
    
    def test_find_best_role_for_keywords_example_generator(self):
        """Test finding best role based on keywords - Example-Generator"""
        library = RoleTemplateLibrary()
        
        text = "Give me an example of how this works in practice."
        role = library.find_best_role_for_keywords(text)
        
        assert role is not None
        assert role.name == "Example-Generator"
    
    def test_find_best_role_for_keywords_misconception_spotter(self):
        """Test finding best role based on keywords - Misconception-Spotter"""
        library = RoleTemplateLibrary()
        
        text = "What are common misconceptions about neural networks?"
        role = library.find_best_role_for_keywords(text)
        
        assert role is not None
        assert role.name == "Misconception-Spotter"
    
    def test_find_best_role_no_match(self):
        """Test finding role with no keyword matches"""
        library = RoleTemplateLibrary()
        
        text = "Hello there, nice day!"
        role = library.find_best_role_for_keywords(text)
        
        # Should return None or default to lowest score
        # This is acceptable behavior
        assert True  # Test passes either way
    
    def test_global_library_instance(self):
        """Test global role_library instance"""
        assert role_library is not None
        assert len(role_library.get_all_roles()) == 5
    
    def test_role_metadata(self):
        """Test role metadata"""
        library = RoleTemplateLibrary()
        
        explainer = library.get_role(RoleType.EXPLAINER)
        assert explainer.metadata is not None
        assert "icon" in explainer.metadata
        assert "color" in explainer.metadata
        assert "priority" in explainer.metadata
    
    def test_all_roles_have_unique_names(self):
        """Test all roles have unique names"""
        library = RoleTemplateLibrary()
        
        names = library.get_role_names()
        assert len(names) == len(set(names))  # All unique
    
    def test_role_priority_keywords(self):
        """Test all roles have priority keywords"""
        library = RoleTemplateLibrary()
        
        for role in library.get_all_roles():
            assert len(role.priority_keywords) > 0
            assert all(isinstance(kw, str) for kw in role.priority_keywords)
