# RQSM-Engine

**Role Queue State Machine Educational Dialogue System**

## Overview

RQSM-Engine is a deterministic, multi-role conversational learning system that dynamically assigns pedagogical roles to document segments and orchestrates interruption-resilient educational dialogues.

## Key Features

- 🎯 **Deterministic Role Assignment**: Reproducible role-to-segment mapping
- 🔄 **State Machine Orchestration**: Predictable dialogue flow via RQSM
- 🛡️ **Interruption Resilience**: Dynamic role reallocation with stability guarantees
- 📚 **Document-Driven Learning**: Semantic segmentation of educational content
- 🤖 **5 AI Roles**: Explainer, Challenger, Summarizer, Example-Generator, Misconception-Spotter

## Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key

### Installation

```bash
# Clone repository
git clone <repository-url>
cd rqsm-engine

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your OpenAI API key
```

### Run Development Server

```bash
uvicorn app.main:app --reload
```

Visit: http://localhost:8000/docs for API documentation

## Project Structure

```
rqsm-engine/
├── app/                    # Application code
│   ├── document/          # Document processing (Module 1)
│   ├── roles/             # Role templates & assignment (Modules 2-3)
│   ├── state_machine/     # RQSM orchestration (Module 4)
│   ├── interruption/      # Interruption handling (Modules 5-6)
│   ├── session/           # Session continuity (Module 7)
│   ├── llm/               # LLM integration
│   └── api/               # FastAPI routes
├── tests/                 # Test suite
├── doc/                   # Documentation
└── sample_docs/          # Sample documents
```

## Documentation

- [Project Architecture](doc/01_PROJECT_ARCHITECTURE.md)
- [Implementation Roadmap](doc/02_IMPLEMENTATION_ROADMAP.md)
- [Module Specifications](doc/03_MODULE_SPECIFICATIONS.md)
- [Testing Strategy](doc/04_TESTING_STRATEGY.md)
- [API Design](doc/05_API_DESIGN.md)
- [Development Setup](doc/06_DEVELOPMENT_SETUP.md)

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test types
pytest -m unit
pytest -m integration
```

## MVP Scope (Academic Capstone)

This is a 40-50% implementation focusing on:
- Core document processing and role assignment
- Basic RQSM state machine
- Keyword-based interruption detection
- SQLite database (not production PostgreSQL)
- Essential API endpoints

## License

Academic Project - Not for Production Use

## Contact

Capstone Project - January 2026
