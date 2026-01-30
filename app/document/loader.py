"""
Document Loader
Handles loading of text and PDF documents
"""
import pdfplumber
from pathlib import Path
from typing import Optional
from loguru import logger


class DocumentLoader:
    """Loads documents from various file formats"""
    
    SUPPORTED_EXTENSIONS = {'.txt', '.pdf'}
    
    def __init__(self):
        """Initialize document loader"""
        logger.info("DocumentLoader initialized")
    
    def load_text(self, filepath: str) -> str:
        """
        Load plain text document.
        
        Args:
            filepath: Path to .txt file
            
        Returns:
            Raw text content
            
        Raises:
            FileNotFoundError: If file doesn't exist
            UnicodeDecodeError: If encoding issues
        """
        logger.debug(f"Loading text file: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"Successfully loaded text file: {filepath} ({len(content)} chars)")
            return content
            
        except UnicodeDecodeError:
            # Fallback to latin-1 encoding
            logger.warning(f"UTF-8 decoding failed for {filepath}, trying latin-1")
            with open(filepath, 'r', encoding='latin-1') as f:
                content = f.read()
            return content
    
    def load_pdf(self, filepath: str) -> str:
        """
        Extract text from PDF document.
        
        Args:
            filepath: Path to .pdf file
            
        Returns:
            Extracted text content
            
        Raises:
            FileNotFoundError: If file doesn't exist
            Exception: If PDF extraction fails
        """
        logger.debug(f"Loading PDF file: {filepath}")
        
        text_parts = []
        
        with pdfplumber.open(filepath) as pdf:
            total_pages = len(pdf.pages)
            logger.info(f"PDF has {total_pages} pages")
            
            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()
                
                if page_text:
                    text_parts.append(page_text)
                    logger.debug(f"Extracted text from page {page_num}/{total_pages}")
                else:
                    logger.warning(f"No text extracted from page {page_num}")
        
        full_text = "\n\n".join(text_parts)
        logger.info(f"Successfully loaded PDF: {filepath} ({len(full_text)} chars)")
        
        return full_text
    
    def load_document(self, filepath: str) -> str:
        """
        Universal document loader (dispatches based on extension).
        
        Args:
            filepath: Path to document
            
        Returns:
            Extracted text
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If unsupported file type
        """
        path = Path(filepath)
        
        if not path.exists():
            logger.error(f"File not found: {filepath}")
            raise FileNotFoundError(f"File not found: {filepath}")
        
        extension = path.suffix.lower()
        
        if extension not in self.SUPPORTED_EXTENSIONS:
            logger.error(f"Unsupported file type: {extension}")
            raise ValueError(
                f"Unsupported file type: {extension}. "
                f"Supported types: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )
        
        if extension == '.txt':
            return self.load_text(filepath)
        elif extension == '.pdf':
            return self.load_pdf(filepath)
        
        raise ValueError(f"Unsupported file extension: {extension}")
    
    def validate_content(self, content: str, min_length: int = 100) -> bool:
        """
        Validate that extracted content is sufficient for processing.
        
        Args:
            content: Extracted text
            min_length: Minimum character count
            
        Returns:
            True if content is valid
        """
        if not content or len(content.strip()) < min_length:
            logger.warning(f"Content too short: {len(content)} chars (min: {min_length})")
            return False
        
        return True
