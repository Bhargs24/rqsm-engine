# Development Environment Setup Guide

## Document-Segment Driven Role-Oriented Conversational Study System (RQSM-Engine)

**Version:** 1.0  
**Date:** January 29, 2026  
**Purpose:** Complete guide for setting up development environment

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [System Requirements](#system-requirements)
3. [Installation Steps](#installation-steps)
4. [Project Structure](#project-structure)
5. [Configuration](#configuration)
6. [Running the Application](#running-the-application)
7. [Development Tools](#development-tools)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

1. **Python 3.10+**
   - Download: https://www.python.org/downloads/
   - Verify: `python --version`

2. **Git**
   - Download: https://git-scm.com/downloads
   - Verify: `git --version`

3. **pip (Python package manager)**
   - Usually included with Python
   - Verify: `pip --version`

4. **Virtual Environment Tool**
   - venv (built-in with Python 3.3+)
   - Alternative: conda, virtualenv

### Optional Tools

1. **Docker** (for containerized deployment)
2. **VS Code** or **PyCharm** (recommended IDEs)
3. **Postman** or **cURL** (for API testing)
4. **PostgreSQL** (for production database)

### API Keys

1. **OpenAI API Key**
   - Sign up: https://platform.openai.com/
   - Get API key from account settings
   - Store securely (never commit to git!)

---

## System Requirements

### Minimum Hardware

- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disk**: 5 GB free space
- **OS**: Windows 10+, macOS 10.14+, or Linux (Ubuntu 20.04+)

### Recommended Hardware

- **CPU**: 4+ cores
- **RAM**: 8+ GB
- **Disk**: 10+ GB SSD
- **GPU**: Not required (LLM runs via API)

### Network Requirements

- Stable internet connection (for LLM API calls)
- Outbound HTTPS access (port 443)

---

## Installation Steps

### Step 1: Clone Repository

```bash
# Create workspace directory
mkdir -p ~/projects
cd ~/projects

# Clone repository
git clone https://github.com/your-org/rqsm-engine.git
cd rqsm-engine
```

### Step 2: Create Virtual Environment

**Using venv (built-in)**:

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

**Using conda**:

```bash
conda create -n rqsm-engine python=3.10
conda activate rqsm-engine
```

**Verify activation**:
```bash
# Should show path to virtual environment
which python  # macOS/Linux
where python  # Windows
```

### Step 3: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install production dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### Step 4: Install Package in Development Mode

```bash
# Install package in editable mode
pip install -e .
```

### Step 5: Verify Installation

```bash
# Check installed packages
pip list

# Verify key packages
pip show fastapi
pip show sentence-transformers
pip show openai
```

---

## Project Structure

### Create Directory Structure

```bash
# From project root
mkdir -p app/{document,roles,state_machine,interruption,llm,session,api}
mkdir -p tests/{unit,integration,validation,performance,fixtures}
mkdir -p doc
mkdir -p sample_docs
mkdir -p logs
mkdir -p data
```

### Final Structure

```
rqsm-engine/
│
├── app/                          # Application code
│   ├── __init__.py
│   ├── main.py                   # FastAPI entry point
│   ├── config.py                 # Configuration
│   │
│   ├── document/                 # Module 1: Document Processing
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   ├── heading_detector.py
│   │   └── segmenter.py
│   │
│   ├── roles/                    # Module 2-3: Roles & Assignment
│   │   ├── __init__.py
│   │   ├── role_templates.py
│   │   └── role_assignment.py
│   │
│   ├── state_machine/            # Module 4: RQSM
│   │   ├── __init__.py
│   │   ├── role_queue.py
│   │   └── rqsm.py
│   │
│   ├── interruption/             # Module 5-6: Interruption Handling
│   │   ├── __init__.py
│   │   ├── intent_classifier.py
│   │   └── reallocator.py
│   │
│   ├── llm/                      # LLM Integration
│   │   ├── __init__.py
│   │   └── client.py
│   │
│   ├── session/                  # Module 7: Session Management
│   │   ├── __init__.py
│   │   └── session_manager.py
│   │
│   └── api/                      # API Layer
│       ├── __init__.py
│       ├── routes.py
│       └── models.py
│
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── unit/
│   ├── integration/
│   ├── validation/
│   ├── performance/
│   └── fixtures/                 # Test documents
│
├── doc/                          # Documentation
│   ├── 01_PROJECT_ARCHITECTURE.md
│   ├── 02_IMPLEMENTATION_ROADMAP.md
│   ├── 03_MODULE_SPECIFICATIONS.md
│   ├── 04_TESTING_STRATEGY.md
│   ├── 05_API_DESIGN.md
│   └── 06_DEVELOPMENT_SETUP.md
│
├── sample_docs/                  # Sample documents for testing
├── logs/                         # Application logs
├── data/                         # Database files (SQLite)
│
├── .env                          # Environment variables (not in git)
├── .env.example                  # Template for .env
├── .gitignore
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development dependencies
├── setup.py                      # Package setup
├── pytest.ini                    # Pytest configuration
├── README.md                     # Project overview
└── Starthere.md                  # Project specification
```

---

## Configuration

### Step 1: Create Environment File

```bash
# Copy template
cp .env.example .env

# Edit with your values
nano .env  # or use your preferred editor
```

### Step 2: Configure Environment Variables

**`.env` file**:

```bash
# Application Settings
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO

# API Settings
API_HOST=0.0.0.0
API_PORT=8000

# LLM Configuration
OPENAI_API_KEY=sk-your-api-key-here
LLM_MODEL=gpt-3.5-turbo
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=500

# Document Processing
SIMILARITY_THRESHOLD=0.75
MIN_UNIT_WORDS=50
MAX_UNIT_WORDS=500
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Role Assignment
STRUCTURAL_WEIGHT=0.4
LEXICAL_WEIGHT=0.3
TOPIC_WEIGHT=0.3

# RQSM Configuration
BOUNDED_DELAY=3
HYSTERESIS_WINDOW=7

# Interruption Handling
CONFIDENCE_THRESHOLD=0.7
ALIGNMENT_WEIGHT=5.0
PENALTY_WEIGHT=2.0

# Session Management
CONTEXT_WINDOW=10

# Database (SQLite for MVP)
DATABASE_URL=sqlite:///./data/rqsm.db

# File Upload
MAX_UPLOAD_SIZE_MB=10
ALLOWED_EXTENSIONS=pdf,txt

# Logging
LOG_FILE=logs/rqsm.log
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5
```

### Step 3: Create Configuration Module

**`app/config.py`**:

```python
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # Application
    APP_ENV = os.getenv('APP_ENV', 'development')
    DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # API
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', 8000))
    
    # LLM
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-3.5-turbo')
    LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', 0.0))
    LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', 500))
    
    # Document Processing
    SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', 0.75))
    MIN_UNIT_WORDS = int(os.getenv('MIN_UNIT_WORDS', 50))
    MAX_UNIT_WORDS = int(os.getenv('MAX_UNIT_WORDS', 500))
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    
    # RQSM
    BOUNDED_DELAY = int(os.getenv('BOUNDED_DELAY', 3))
    HYSTERESIS_WINDOW = int(os.getenv('HYSTERESIS_WINDOW', 7))
    
    # Interruption
    CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', 0.7))
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / 'data'
    LOGS_DIR = BASE_DIR / 'logs'
    SAMPLE_DOCS_DIR = BASE_DIR / 'sample_docs'
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{DATA_DIR}/rqsm.db')
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in environment")
        
        # Create necessary directories
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.LOGS_DIR.mkdir(exist_ok=True)
        cls.SAMPLE_DOCS_DIR.mkdir(exist_ok=True)

# Validate on import
Config.validate()
```

---

## Running the Application

### Development Mode

#### Option 1: Using uvicorn directly

```bash
# From project root
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Option 2: Using Python

```bash
python -m app.main
```

#### Option 3: Using script

**`run_dev.sh` (Linux/macOS)**:
```bash
#!/bin/bash
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**`run_dev.bat` (Windows)**:
```batch
@echo off
call venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Access Application

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health**: http://localhost:8000/api/v1/health

### Production Mode

```bash
# Using gunicorn (Linux/macOS)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# Using uvicorn (Windows)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Development Tools

### Code Quality Tools

#### 1. Black (Code Formatter)

```bash
# Install
pip install black

# Format entire project
black .

# Check without modifying
black --check .

# Format specific files
black app/document/loader.py
```

**Configuration** (`pyproject.toml`):
```toml
[tool.black]
line-length = 100
target-version = ['py310']
include = '\.pyi?$'
exclude = '''
/(
    \.git
  | \.venv
  | build
  | dist
)/
'''
```

#### 2. MyPy (Type Checker)

```bash
# Install
pip install mypy

# Check types
mypy app/

# Check specific module
mypy app/roles/role_templates.py
```

**Configuration** (`mypy.ini`):
```ini
[mypy]
python_version = 3.10
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
```

#### 3. Flake8 (Linter)

```bash
# Install
pip install flake8

# Lint project
flake8 app/

# With specific rules
flake8 --max-line-length=100 --ignore=E203,W503 app/
```

**Configuration** (`.flake8`):
```ini
[flake8]
max-line-length = 100
exclude = .git,__pycache__,venv,build,dist
ignore = E203,W503
```

#### 4. isort (Import Sorter)

```bash
# Install
pip install isort

# Sort imports
isort .

# Check without modifying
isort --check-only .
```

**Configuration** (`pyproject.toml`):
```toml
[tool.isort]
profile = "black"
line_length = 100
```

### Testing Tools

#### Run Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/unit/test_rqsm.py

# Specific test function
pytest tests/unit/test_rqsm.py::test_initialization

# With coverage
pytest --cov=app --cov-report=html

# With verbose output
pytest -v

# Stop on first failure
pytest -x

# Run only fast tests (exclude slow ones)
pytest -m "not slow"
```

#### Test Configuration

**`pytest.ini`**:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    validation: marks tests as validation tests
addopts = 
    --verbose
    --strict-markers
    --tb=short
```

#### Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html

# Open report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Database Tools

#### SQLite Management

```bash
# Open database
sqlite3 data/rqsm.db

# Common commands
.tables              # List tables
.schema sessions     # Show table schema
SELECT * FROM sessions;  # Query data
.quit                # Exit
```

#### Database Migrations (Future)

```bash
# Using Alembic
pip install alembic

# Initialize
alembic init migrations

# Create migration
alembic revision --autogenerate -m "Initial tables"

# Apply migration
alembic upgrade head
```

### Git Workflow

#### Initial Setup

```bash
# Configure git
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Set up .gitignore
cat > .gitignore << EOL
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
*.egg-info/
dist/
build/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Environment
.env

# Data
data/*.db
logs/*.log

# Testing
.pytest_cache/
.coverage
htmlcov/

# OS
.DS_Store
Thumbs.db
EOL
```

#### Common Commands

```bash
# Create feature branch
git checkout -b feature/document-processing

# Stage changes
git add app/document/

# Commit
git commit -m "Implement document loader"

# Push to remote
git push origin feature/document-processing

# Update from main
git checkout main
git pull origin main
git checkout feature/document-processing
git rebase main
```

### VS Code Configuration

**`.vscode/settings.json`**:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.rulers": [100],
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    ".pytest_cache": true
  },
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.testing.pytestArgs": ["tests"]
}
```

**`.vscode/launch.json`**:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": true
    },
    {
      "name": "Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["-v"],
      "console": "integratedTerminal",
      "justMyCode": true
    }
  ]
}
```

---

## Troubleshooting

### Common Issues

#### 1. Import Errors

**Problem**: `ModuleNotFoundError: No module named 'app'`

**Solution**:
```bash
# Install package in development mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}"  # Linux/macOS
set PYTHONPATH=%PYTHONPATH%;%CD%  # Windows
```

#### 2. OpenAI API Key Error

**Problem**: `openai.error.AuthenticationError: No API key provided`

**Solution**:
```bash
# Check .env file exists
ls -la .env

# Verify key is set
cat .env | grep OPENAI_API_KEY

# Set manually
export OPENAI_API_KEY=sk-your-key-here
```

#### 3. Port Already in Use

**Problem**: `OSError: [Errno 98] Address already in use`

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# Or use different port
uvicorn app.main:app --port 8001
```

#### 4. Database Locked

**Problem**: `sqlite3.OperationalError: database is locked`

**Solution**:
```bash
# Close other connections
# Or delete database and recreate
rm data/rqsm.db
# Restart application
```

#### 5. Sentence Transformers Download

**Problem**: First run downloads embedding model (can be slow)

**Solution**:
```bash
# Pre-download model
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

#### 6. Memory Issues

**Problem**: `MemoryError` during document processing

**Solution**:
```bash
# Reduce batch size
# Or process documents in chunks
# Or increase system RAM
```

### Debug Mode

**Enable debug logging**:

```python
# In app/main.py
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

**Or via environment**:
```bash
export LOG_LEVEL=DEBUG
```

### Get Help

1. **Check logs**: `tail -f logs/rqsm.log`
2. **Run tests**: `pytest -v`
3. **Check API health**: `curl http://localhost:8000/api/v1/health`
4. **Review documentation**: `doc/` folder
5. **GitHub Issues**: Create issue with error details

---

## Next Steps

### After Setup

1. **Verify Installation**
   ```bash
   python -c "import app; print('Success!')"
   ```

2. **Run Tests**
   ```bash
   pytest tests/ -v
   ```

3. **Start Development**
   - Review [Implementation Roadmap](02_IMPLEMENTATION_ROADMAP.md)
   - Check [Module Specifications](03_MODULE_SPECIFICATIONS.md)
   - Follow development phases

4. **Create Sample Document**
   ```bash
   # Add test document
   cp your_document.pdf sample_docs/
   ```

5. **Test API**
   ```bash
   # Start server
   uvicorn app.main:app --reload
   
   # In another terminal
   curl http://localhost:8000/api/v1/health
   ```

### Development Workflow

1. **Create feature branch**
2. **Write tests first** (TDD)
3. **Implement feature**
4. **Run tests**: `pytest`
5. **Format code**: `black .`
6. **Check types**: `mypy app/`
7. **Lint**: `flake8 app/`
8. **Commit and push**

### Useful Commands Reference

```bash
# Activate environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate  # Windows

# Run application
uvicorn app.main:app --reload

# Run tests
pytest

# Format code
black .

# Check types
mypy app/

# Lint code
flake8 app/

# Generate coverage
pytest --cov=app --cov-report=html

# View logs
tail -f logs/rqsm.log

# Deactivate environment
deactivate
```

---

## Appendix

### requirements.txt

```txt
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# LLM Integration
openai==1.3.5

# Document Processing
pdfplumber==0.10.3
sentence-transformers==2.2.2

# Data & ML
numpy==1.24.3
pandas==2.1.3
scikit-learn==1.3.2

# Database
sqlalchemy==2.0.23
databases==0.8.0

# Configuration
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Utilities
python-dateutil==2.8.2
```

### requirements-dev.txt

```txt
# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0
pytest-benchmark==4.0.0

# Code Quality
black==23.11.0
flake8==6.1.0
mypy==1.7.1
isort==5.12.0

# Documentation
mkdocs==1.5.3
mkdocs-material==9.5.2

# Development
ipython==8.18.1
ipdb==0.13.13
```

### setup.py

```python
from setuptools import setup, find_packages

setup(
    name='rqsm-engine',
    version='1.0.0',
    description='Role Queue State Machine Educational Dialogue System',
    author='Your Name',
    author_email='your.email@example.com',
    packages=find_packages(),
    install_requires=[
        'fastapi>=0.104.1',
        'uvicorn[standard]>=0.24.0',
        'openai>=1.3.5',
        'pdfplumber>=0.10.3',
        'sentence-transformers>=2.2.2',
        'python-dotenv>=1.0.0',
        'pydantic>=2.5.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.4.3',
            'pytest-cov>=4.1.0',
            'black>=23.11.0',
            'mypy>=1.7.1',
            'flake8>=6.1.0',
        ]
    },
    python_requires='>=3.10',
)
```

---

## Conclusion

You now have a complete development environment for the RQSM-Engine project. Key points:

1. ✅ **Python 3.10+** with virtual environment
2. ✅ **All dependencies** installed
3. ✅ **Project structure** created
4. ✅ **Configuration** set up
5. ✅ **Development tools** configured
6. ✅ **Testing framework** ready

**Next**: Start implementing modules following the [Implementation Roadmap](02_IMPLEMENTATION_ROADMAP.md)!
