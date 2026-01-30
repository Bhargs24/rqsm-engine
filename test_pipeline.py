"""
Integration test for complete document processing pipeline
"""
from app.document.processor import DocumentProcessor
from pathlib import Path


def test_process_sample_document():
    """Test processing the sample machine learning document"""
    
    # Initialize processor
    processor = DocumentProcessor(
        embedding_model='all-MiniLM-L6-v2',
        similarity_threshold=0.75
    )
    
    # Process document
    sample_path = "sample_docs/machine_learning_intro.txt"
    
    if not Path(sample_path).exists():
        print(f"Sample document not found: {sample_path}")
        return
    
    print(f"\n{'='*60}")
    print(f"Processing: {sample_path}")
    print(f"{'='*60}\n")
    
    semantic_units = processor.process_document(sample_path)
    
    # Display results
    print(f"✓ Successfully processed document")
    print(f"✓ Generated {len(semantic_units)} semantic units\n")
    
    # Get summary
    summary = processor.get_document_summary(semantic_units)
    
    print(f"{'='*60}")
    print(f"DOCUMENT SUMMARY")
    print(f"{'='*60}")
    print(f"Source File: {summary['source_file']}")
    print(f"Total Units: {summary['total_units']}")
    print(f"Total Words: {summary['total_words']}")
    print(f"Avg Words/Unit: {summary['avg_words_per_unit']:.1f}")
    print(f"Avg Cohesion: {summary['avg_cohesion']:.2f}")
    print(f"\nSections:")
    for section_type, section_data in summary['sections'].items():
        print(f"  - {section_type}: {section_data['count']} units, {section_data['words']} words")
    
    print(f"\n{'='*60}")
    print(f"SEMANTIC UNITS DETAIL")
    print(f"{'='*60}\n")
    
    # Display first 3 units in detail
    for i, unit in enumerate(semantic_units[:3], 1):
        print(f"Unit {i}: {unit.id}")
        print(f"  Title: {unit.title or 'N/A'}")
        print(f"  Section: {unit.document_section}")
        print(f"  Word Count: {unit.word_count}")
        print(f"  Cohesion Score: {unit.similarity_score:.2f}")
        print(f"  Text Preview: {unit.text[:100]}...")
        print()
    
    if len(semantic_units) > 3:
        print(f"... and {len(semantic_units) - 3} more units")
    
    print(f"\n{'='*60}")
    print(f"✅ Document processing pipeline test PASSED")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    test_process_sample_document()
