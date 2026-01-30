# RQSM-Engine Tech Stack

## Overview
This document lists all technologies, libraries, and tools used in each phase of the RQSM-Engine project.

---

## Core Programming

| Component | Tool | Version | Purpose |
|-----------|------|---------|---------|
| Language | Python | 3.10+ | Main programming language |
| Package Manager | pip | Latest | Dependency management |
| Environment | venv | Built-in | Virtual environment isolation |

---

## Phase 1: Document Processing ✅ IMPLEMENTED

### Document Loading
| Library | Version | Purpose |
|---------|---------|---------|
| **pdfplumber** | 0.11.9 | Extract text from PDF files |
| **PyPDF2** | 3.0.1 | Backup PDF parsing |
| **pathlib** | Built-in | File path handling |

### Text Analysis
| Library | Version | Purpose |
|---------|---------|---------|
| **sentence-transformers** | 5.2.2 | Generate semantic embeddings for paragraphs |
| **torch** | 2.1.2+ | Backend for transformer models |
| **numpy** | 1.26.3+ | Numerical computations |
| **nltk** | 3.8.1 | Natural language processing utilities |

### Embedding Model
- **Model**: `all-MiniLM-L6-v2`
- **Source**: Hugging Face
- **Size**: ~90MB
- **Purpose**: Convert text to 384-dimensional vectors for similarity

---

## Phase 2: Roles & Assignment ⏳ NEXT

### LLM Integration
| Library | Version | Purpose |
|---------|---------|---------|
| **openai** | 1.10.0+ | OpenAI API client |
| **tiktoken** | 0.5.2 | Token counting for GPT models |

### LLM Configuration
- **Model**: `gpt-3.5-turbo`
- **Temperature**: `0.0` (deterministic)
- **Max Tokens**: `500`
- **Purpose**: Generate role-based dialogue responses

### Role Assignment
| Library | Purpose |
|---------|---------|
| **numpy** | Scoring calculations (α=0.4, β=0.3, γ=0.3) |
| **Custom algorithms** | Structural, lexical, topic scoring |

---

## Phase 3: State Machine & Orchestration ⏳ FUTURE

### Database
| Library | Version | Purpose |
|---------|---------|---------|
| **sqlalchemy** | 2.0.25 | ORM for database operations |
| **alembic** | 1.13.1 | Database migrations |
| **SQLite** | Built-in | Database (MVP) |
| PostgreSQL | Future | Production database (optional) |

### State Management
- Custom RQSM implementation
- Python dataclasses for state objects
- Turn-based state transitions

---

## Web Framework & API

| Component | Library | Version | Purpose |
|-----------|---------|---------|---------|
| Web Framework | **FastAPI** | 0.109.0+ | REST API server |
| ASGI Server | **uvicorn** | 0.27.0+ | Production web server |
| Data Validation | **pydantic** | 2.5.3+ | Request/response models |
| Settings | **pydantic-settings** | 2.1.0+ | Configuration management |
| File Upload | **python-multipart** | 0.0.6 | Handle file uploads |

---

## Testing & Quality

### Testing Framework
| Library | Version | Purpose |
|---------|---------|---------|
| **pytest** | 7.4.4+ | Test runner |
| **pytest-asyncio** | 0.23.3 | Async test support |
| **pytest-cov** | 4.1.0 | Code coverage |
| **pytest-mock** | 3.12.0 | Mocking utilities |
| **httpx** | 0.26.0 | API testing |

### Code Quality
| Tool | Version | Purpose |
|------|---------|---------|
| **black** | 24.1.1 | Code formatting |
| **flake8** | 7.0.0 | Linting |
| **mypy** | 1.8.0 | Type checking |
| **isort** | 5.13.2 | Import sorting |

---

## Utilities & Infrastructure

### Logging
| Library | Version | Purpose |
|---------|---------|---------|
| **loguru** | 0.7.2 | Structured logging |
| Built-in | `logging` | Fallback logger |

### Configuration
| Library | Version | Purpose |
|---------|---------|---------|
| **python-dotenv** | 1.0.0 | Load .env files |
| **pyyaml** | 6.0.1 | YAML config files |

### Development
| Tool | Purpose |
|------|---------|
| **ipython** | Interactive Python shell |
| **jupyter** | Notebooks for experimentation |

---

## Deployment (Future)

| Tool | Purpose | Status |
|------|---------|--------|
| Docker | Containerization | Not yet |
| Docker Compose | Multi-container orchestration | Not yet |
| Nginx | Reverse proxy | Not yet |
| PostgreSQL | Production database | Optional |

---

## Phase-by-Phase Breakdown

### ✅ Phase 1 (Weeks 1-3): Document Processing
**Status**: IMPLEMENTED
```
pdfplumber → Extract text from PDFs
sentence-transformers → Semantic embeddings
numpy → Similarity calculations
Custom algorithms → Heading detection, segmentation
```

### ⏳ Phase 2 (Weeks 4-6): Roles & Assignment
**Status**: NEXT
```
openai → LLM API calls (gpt-3.5-turbo, temp=0.0)
Custom scoring → Role-to-segment assignment
numpy → Score calculations
```

### ⏳ Phase 3 (Weeks 7-9): State Machine
**Status**: FUTURE
```
sqlalchemy → Session persistence
Custom RQSM → State transitions
Python dataclasses → State objects
```

### ⏳ Phase 4 (Weeks 10-12): Integration
**Status**: FUTURE
```
FastAPI → REST endpoints
pytest → Integration tests
All modules → End-to-end pipeline
```

---

## Installation Commands

### Core Dependencies
```bash
pip install fastapi uvicorn pydantic pydantic-settings
```

### Document Processing
```bash
pip install pdfplumber sentence-transformers torch numpy nltk
```

### LLM Integration
```bash
pip install openai tiktoken
```

### Database
```bash
pip install sqlalchemy alembic
```

### Utilities
```bash
pip install python-dotenv loguru pyyaml
```

### Testing
```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock httpx
```

### Development
```bash
pip install black flake8 mypy isort ipython jupyter
```

### Or Install Everything
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

---

## Key Technical Decisions

| Decision | Rationale |
|----------|-----------|
| **Python 3.10+** | Modern features, type hints, dataclasses |
| **FastAPI** | Fast, async, automatic API docs |
| **sentence-transformers** | State-of-art semantic embeddings |
| **OpenAI GPT-3.5** | Reliable, cost-effective LLM |
| **Temperature=0.0** | Deterministic responses |
| **SQLite (MVP)** | Simple, no server needed |
| **pytest** | Industry standard testing |
| **loguru** | Better than built-in logging |
| **pydantic** | Type-safe configuration |

---

## Hardware Requirements

### Minimum
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disk**: 5 GB (includes models)
- **GPU**: Not required (models run via API)

### Recommended
- **CPU**: 4+ cores
- **RAM**: 8+ GB
- **Disk**: 10+ GB SSD
- **Internet**: Stable (for API calls)

---

## External Services

| Service | Purpose | Cost |
|---------|---------|------|
| **OpenAI API** | LLM inference | ~$0.002/1K tokens |
| **Hugging Face** | Model downloads | Free |

---

## Model Downloads

| Model | Size | First Use | Purpose |
|-------|------|-----------|---------|
| `all-MiniLM-L6-v2` | ~90 MB | Auto-download | Sentence embeddings |

---

**Last Updated**: January 30, 2026  
**Project Phase**: Phase 1 Complete, Phase 2 Next
