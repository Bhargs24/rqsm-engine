"""
Pytest Configuration and Fixtures
"""
import pytest
from pathlib import Path


@pytest.fixture
def sample_text_document():
    """Sample text document for testing"""
    return """INTRODUCTION

This is the introduction section of a test document.
It provides background information about the topic.

The introduction spans multiple paragraphs to test
segmentation capabilities of the system.

MAIN CONTENT

This section contains the main content of the document.
It discusses various aspects of the subject matter.

The content is organized into multiple semantic units
to enable role-based dialogue generation.

METHODS AND APPROACH

This section describes the methodology used in the research.
It outlines the experimental design and procedures.

Detailed steps are provided for reproducibility.
The approach follows best practices in the field.

CONCLUSION

This is the concluding section of the document.
It summarizes the key findings and insights.

Future work directions are also discussed here."""


@pytest.fixture
def sample_pdf_path():
    """Path to sample PDF document"""
    return Path("sample_docs/test_document.pdf")


@pytest.fixture
def sample_txt_path(tmp_path):
    """Create a temporary text file for testing"""
    filepath = tmp_path / "test_document.txt"
    filepath.write_text("""INTRODUCTION

This is a test document for unit testing.

BODY

Main content goes here.""", encoding='utf-8')
    return str(filepath)


@pytest.fixture
def temp_dir(tmp_path):
    """Temporary directory for test files"""
    return tmp_path
