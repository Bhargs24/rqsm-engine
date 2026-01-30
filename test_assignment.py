"""
Demo script for Role Assignment Engine
Shows end-to-end document processing with role assignment
"""
from app.document.processor import DocumentProcessor
from app.roles.role_assignment import RoleAssigner
from pathlib import Path


def demo_role_assignment():
    """Demonstrate role assignment on sample document"""
    print("=" * 80)
    print("RQSM-Engine Role Assignment Demo")
    print("=" * 80)
    print()
    
    # Load and process document
    doc_path = Path("sample_docs/machine_learning_intro.txt")
    
    if not doc_path.exists():
        print(f"Error: Sample document not found at {doc_path}")
        return
    
    print(f"Processing document: {doc_path.name}")
    print()
    
    # Initialize processor
    processor = DocumentProcessor()
    
    # Process document
    semantic_units = processor.process_document(str(doc_path))
    
    print(f"Document processed: {len(semantic_units)} semantic units created")
    print()
    
    # Initialize role assigner
    assigner = RoleAssigner()
    
    # Assign roles with balancing
    print("Assigning roles (with balancing)...")
    assignments = assigner.assign_roles(semantic_units, balance_roles=True)
    print(f"✓ Assigned roles to {len(assignments)} units")
    print()
    
    # Display first few assignments
    print("=" * 80)
    print("Sample Role Assignments")
    print("=" * 80)
    print()
    
    for i, assignment in enumerate(assignments[:5], 1):
        unit = assignment.semantic_unit
        role_icon = assignment.role_template.metadata.get('icon', '')
        
        print(f"{i}. Unit {unit.id} → {assignment.assigned_role.value} {role_icon}")
        print(f"   Title: {unit.title or '(no title)'}")
        print(f"   Section: {unit.document_section}")
        print(f"   Position: {unit.position}/{len(semantic_units)}")
        print(f"   Confidence: {assignment.confidence:.2f}")
        print(f"   Score Breakdown:")
        print(f"     - Structural: {assignment.score.structural_score:.2f}")
        print(f"     - Lexical: {assignment.score.lexical_score:.2f}")
        print(f"     - Topic: {assignment.score.topic_score:.2f}")
        print(f"   Text Preview: {unit.text[:100]}...")
        print()
    
    if len(assignments) > 5:
        print(f"... and {len(assignments) - 5} more assignments")
        print()
    
    # Generate role queue
    print("=" * 80)
    print("Role Queue (Document Order)")
    print("=" * 80)
    print()
    
    queue = assigner.get_role_queue(assignments)
    
    for i, (role, unit) in enumerate(queue[:10], 1):
        role_template = assigner.scorer.scorer if hasattr(assigner.scorer, 'scorer') else None
        from app.roles.role_templates import role_library
        template = role_library.get_role(role)
        icon = template.metadata.get('icon', '')
        
        print(f"{i:2d}. {role.value:25s} {icon} → Unit {unit.id} ({unit.document_section})")
    
    if len(queue) > 10:
        print(f"     ... and {len(queue) - 10} more in queue")
    print()
    
    # Get statistics
    print("=" * 80)
    print("Role Distribution Statistics")
    print("=" * 80)
    print()
    
    stats = assigner.get_statistics(assignments)
    
    print(f"Total Assignments: {stats['total_assignments']}")
    print(f"Overall Confidence: {stats['overall_confidence']:.2f}")
    print()
    
    print("Role Distribution:")
    from app.roles.role_templates import role_library
    
    for role_type, count in stats['role_counts'].items():
        template = role_library.get_role(role_type)
        icon = template.metadata.get('icon', '')
        percentage = stats['role_percentages'][role_type]
        avg_conf = stats['average_confidences'][role_type]
        
        bar_length = int(percentage / 2)  # Scale to 50 chars max
        bar = "█" * bar_length
        
        print(f"{role_type.value:25s} {icon}: {count:2d} ({percentage:5.1f}%) {bar}")
        print(f"{'':27s}    Avg Confidence: {avg_conf:.2f}")
    
    print()
    print("=" * 80)
    
    # Compare with non-balanced assignment
    print()
    print("Comparison: Greedy vs Balanced Assignment")
    print("=" * 80)
    print()
    
    greedy_assignments = assigner.assign_roles(semantic_units, balance_roles=False)
    greedy_stats = assigner.get_statistics(greedy_assignments)
    
    print(f"{'Role':<25s} {'Greedy':<12s} {'Balanced':<12s} {'Difference'}")
    print("-" * 80)
    
    for role_type in stats['role_counts'].keys():
        greedy_pct = greedy_stats['role_percentages'][role_type]
        balanced_pct = stats['role_percentages'][role_type]
        diff = balanced_pct - greedy_pct
        
        print(f"{role_type.value:<25s} {greedy_pct:5.1f}%       {balanced_pct:5.1f}%       {diff:+5.1f}%")
    
    print()


if __name__ == "__main__":
    demo_role_assignment()
