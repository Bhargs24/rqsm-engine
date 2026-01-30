"""
Unit Tests for Document Loader
"""
import pytest
from pathlib import Path

from app.document.loader import DocumentLoader


class TestDocumentLoader:
    """Test suite for DocumentLoader"""
    
    def test_initialization(self):
        """Test DocumentLoader initialization"""
        loader = DocumentLoader()
        assert loader is not None
        assert loader.SUPPORTED_EXTENSIONS == {'.txt', '.pdf'}
    
    def test_load_text_file(self, sample_txt_path):
        """Test loading a text file"""
        loader = DocumentLoader()
        content = loader.load_text(sample_txt_path)
        
        assert content is not None
        assert len(content) > 0
        assert "INTRODUCTION" in content
        assert "BODY" in content
    
    def test_load_document_txt(self, sample_txt_path):
        """Test universal loader with .txt file"""
        loader = DocumentLoader()
        content = loader.load_document(sample_txt_path)
        
        assert content is not None
        assert len(content) > 0
    
    def test_file_not_found(self):
        """Test handling of non-existent file"""
        loader = DocumentLoader()
        
        with pytest.raises(FileNotFoundError):
            loader.load_document("nonexistent_file.txt")
    
    def test_unsupported_file_type(self, temp_dir):
        """Test handling of unsupported file type"""
        loader = DocumentLoader()
        
        # Create an unsupported file
        filepath = temp_dir / "test.docx"
        filepath.write_text("test content")
        
        with pytest.raises(ValueError, match="Unsupported file type"):
            loader.load_document(str(filepath))
    
    def test_validate_content_valid(self):
        """Test content validation with valid content"""
        loader = DocumentLoader()
        content = "This is a valid document with sufficient length for processing."
        
        assert loader.validate_content(content, min_length=10) is True
    
    def test_validate_content_too_short(self):
        """Test content validation with insufficient content"""
        loader = DocumentLoader()
        content = "Short"
        
        assert loader.validate_content(content, min_length=100) is False
    
    def test_validate_content_empty(self):
        """Test content validation with empty content"""
        loader = DocumentLoader()
        
        assert loader.validate_content("", min_length=10) is False
        assert loader.validate_content("   ", min_length=10) is False
