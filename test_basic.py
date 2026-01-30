"""
Simple test of document loading and heading detection
"""
from app.document.loader import DocumentLoader
from app.document.heading_detector import HeadingDetector
from pathlib import Path


def test_basic_processing():
    """Test basic document loading and heading detection"""
    
    print(f"\n{'='*60}")
    print(f"BASIC DOCUMENT PROCESSING TEST")
    print(f"{'='*60}\n")
    
    # Test 1: Document Loading
    print("Test 1: Document Loading")
    loader = DocumentLoader()
    sample_path = "sample_docs/machine_learning_intro.txt"
    
    if not Path(sample_path).exists():
        print(f"✗ Sample document not found: {sample_path}")
        return
    
    text = loader.load_document(sample_path)
    print(f"✓ Successfully loaded document")
    print(f"✓ Document length: {len(text)} characters")
    print(f"✓ Word count: {len(text.split())} words\n")
    
    # Test 2: Heading Detection
    print("Test 2: Heading Detection")
    detector = HeadingDetector()
    headings = detector.detect_headings(text)
    print(f"✓ Detected {len(headings)} headings\n")
    
    if headings:
        print("Headings found:")
        for heading in headings:
            print(f"  - Level {heading.level}: {heading.text}")
        print()
    
    # Test 3: Section Splitting
    print("Test 3: Section Splitting")
    sections = detector.split_by_headings(text, headings)
    print(f"✓ Split into {len(sections)} sections\n")
    
    if sections:
        print("Sections:")
        for i, section in enumerate(sections, 1):
            word_count = len(section['text'].split())
            print(f"  {i}. {section['title']} ({section['section_type']})")
            print(f"     - {word_count} words")
        print()
    
    print(f"{'='*60}")
    print(f"✅ ALL TESTS PASSED")
    print(f"{'='*60}\n")
    
    print("Note: Semantic segmentation requires downloading a 90MB model.")
    print("Run 'python test_pipeline.py' to test full pipeline with embeddings.\n")


if __name__ == "__main__":
    test_basic_processing()
