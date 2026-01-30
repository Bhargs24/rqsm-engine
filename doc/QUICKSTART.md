# Quick Start Guide

## Getting Started with RQSM-Engine

### Prerequisites
- Python 3.10+ installed
- Virtual environment activated

### Initial Setup

```bash
# Navigate to project directory
cd "d:\Projects\Capstone\Deterministic, Multi-Role, Interruption-Resilient Conversational Learning Engine\rqsm-engine"

# Activate virtual environment (already created)
.\.venv\Scripts\activate

# Verify dependencies are installed
pip list
```

### Running Tests

```bash
# Run all unit tests
pytest

# Run specific test file
pytest tests/unit/test_document_loader.py -v

# Run without coverage (faster)
pytest --no-cov -v
```

### Using the Document Processor

#### Example 1: Load and Process a Document

```python
from app.document.loader import DocumentLoader

# Initialize loader
loader = DocumentLoader()

# Load a document
text = loader.load_document("sample_docs/machine_learning_intro.txt")

print(f"Loaded {len(text)} characters")
print(f"Word count: {len(text.split())}")
```

#### Example 2: Detect Headings

```python
from app.document.heading_detector import HeadingDetector

detector = HeadingDetector()

# Detect headings in text
headings = detector.detect_headings(text)

print(f"Found {len(headings)} headings:")
for heading in headings:
    print(f"  Level {heading.level}: {heading.text}")

# Split into sections
sections = detector.split_by_headings(text, headings)
print(f"\nSplit into {len(sections)} sections")
```

#### Example 3: Full Document Processing Pipeline

```python
from app.document.processor import DocumentProcessor

# Initialize processor (downloads model on first run)
processor = DocumentProcessor(
    embedding_model='all-MiniLM-L6-v2',
    similarity_threshold=0.75
)

# Process document
semantic_units = processor.process_document("sample_docs/machine_learning_intro.txt")

print(f"Generated {len(semantic_units)} semantic units")

# Get summary
summary = processor.get_document_summary(semantic_units)

print(f"\nDocument Summary:")
print(f"  Total Words: {summary['total_words']}")
print(f"  Avg Words/Unit: {summary['avg_words_per_unit']:.1f}")
print(f"  Avg Cohesion: {summary['avg_cohesion']:.2f}")

# Access individual units
for unit in semantic_units[:3]:
    print(f"\n{unit.id}: {unit.title}")
    print(f"  Words: {unit.word_count}")
    print(f"  Cohesion: {unit.similarity_score:.2f}")
    print(f"  Preview: {unit.text[:100]}...")
```

### Starting the Web Server

```bash
# Start FastAPI development server
python app/main.py

# Or using uvicorn directly
uvicorn app.main:app --reload
```

Access the API at:
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

### Configuration

Edit `.env` file (copy from `.env.example`):

```bash
# Required
OPENAI_API_KEY=your_key_here

# Optional (defaults provided)
APP_ENV=development
LOG_LEVEL=INFO
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.0
OPENAI_MAX_TOKENS=500
```

### Project Structure

```
rqsm-engine/
├── app/                      # Application code
│   ├── document/            # Module 1: Document processing
│   │   ├── loader.py        # Load TXT/PDF files
│   │   ├── heading_detector.py  # Detect headings
│   │   ├── segmenter.py     # Semantic segmentation
│   │   └── processor.py     # Main orchestrator
│   ├── config.py            # Settings
│   └── main.py              # FastAPI app
├── tests/                   # Test suite
│   └── unit/               # Unit tests
├── sample_docs/            # Sample documents
├── doc/                    # Documentation
└── logs/                   # Application logs
```

### Troubleshooting

#### Model Download Issues
If sentence-transformers model download times out:
1. Check internet connection
2. Try running test_basic.py first (no model needed)
3. Model will be cached after first successful download

#### Import Errors
Make sure you're in the project root directory and virtual environment is activated.

#### Test Failures
Run tests with verbose output:
```bash
pytest -v --tb=short
```

### Next Steps

1. **Add more sample documents** to `sample_docs/`
2. **Run full pipeline test**: `python test_pipeline.py` (requires model download)
3. **Explore API**: Start server and visit http://localhost:8000/docs
4. **Review planning docs** in `doc/` folder

### Useful Commands

```bash
# Install new package
pip install package_name

# Update requirements
pip freeze > requirements.txt

# Run specific test
pytest tests/unit/test_document_loader.py::TestDocumentLoader::test_load_text_file -v

# Check code style
black app/ --check

# Format code
black app/

# Type checking
mypy app/
```

### Getting Help

- Review planning documents in `doc/`
- Check [IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md) for current status
- See [README.md](README.md) for project overview

---

**Status**: Phase 1 Complete ✅  
**Next**: Phase 2 - Role Templates & Assignment
