"""
Test script for role templates
Demonstrates the 5 pedagogical roles
"""
from app.roles.role_templates import role_library, RoleType


def demo_all_roles():
    """Demo all 5 role templates"""
    print("=" * 80)
    print("RQSM-Engine Role Templates Demo")
    print("=" * 80)
    print()
    
    # Get all roles
    roles = role_library.get_all_roles()
    
    print(f"Total Roles Available: {len(roles)}\n")
    
    # Display each role
    for i, role in enumerate(roles, 1):
        print(f"{i}. {role.name} {role.metadata.get('icon', '')}")
        print(f"   Type: {role.role_type.value}")
        print(f"   Temperature: {role.temperature}")
        print(f"   Max Tokens: {role.max_tokens}")
        print(f"   Priority Keywords: {', '.join(role.priority_keywords[:5])}...")
        print(f"   System Prompt: {role.system_prompt[:100]}...")
        print()
    
    print("=" * 80)
    print("Keyword-Based Role Detection Demo")
    print("=" * 80)
    print()
    
    # Test keyword matching
    test_queries = [
        "Can you explain what a neural network is?",
        "What are the limitations of this approach?",
        "Summarize the key points from this section.",
        "Give me an example of how this works in practice.",
        "What are common misconceptions about machine learning?"
    ]
    
    for query in test_queries:
        best_role = role_library.find_best_role_for_keywords(query)
        if best_role:
            print(f"Query: \"{query}\"")
            print(f"→ Best Role: {best_role.name} {best_role.metadata.get('icon', '')}")
            print()
    
    print("=" * 80)
    print("Prompt Building Demo")
    print("=" * 80)
    print()
    
    # Demo prompt building
    explainer = role_library.get_role(RoleType.EXPLAINER)
    context = "Neural networks are computational models inspired by biological neurons."
    user_input = "How do neural networks learn?"
    
    prompt = explainer.build_prompt(context, user_input)
    
    print(f"Role: {explainer.name}")
    print(f"Context: {context}")
    print(f"User Input: {user_input}")
    print()
    print("Generated Prompt:")
    print("-" * 80)
    print(prompt)
    print("-" * 80)


if __name__ == "__main__":
    demo_all_roles()
