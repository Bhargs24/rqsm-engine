"""
Document Processor Engine
Main orchestrator for document processing pipeline
"""
from typing import List, Optional
from pathlib import Path
from loguru import logger

from app.document.loader import DocumentLoader
from app.document.heading_detector import HeadingDetector, Heading
from app.document.segmenter import SemanticSegmenter, SemanticUnit


class DocumentProcessor:
    """
    Main document processing engine.
    
    Orchestrates the three-stage pipeline:
    1. Document loading
    2. Heading detection
    3. Semantic segmentation
    """
    
    def __init__(
        self,
        embedding_model: str = 'all-MiniLM-L6-v2',
        similarity_threshold: float = 0.75
    ):
        """
        Initialize document processor.
        
        Args:
            embedding_model: SentenceTransformer model name
            similarity_threshold: Minimum similarity for grouping paragraphs
        """
        logger.info("Initializing DocumentProcessor")
        
        self.loader = DocumentLoader()
        self.heading_detector = HeadingDetector()
        self.segmenter = SemanticSegmenter(
            model_name=embedding_model,
            similarity_threshold=similarity_threshold
        )
        
        logger.info("DocumentProcessor initialized successfully")
    
    def process_document(
        self,
        filepath: str,
        validate_content: bool = True
    ) -> List[SemanticUnit]:
        """
        Process a document through the full pipeline.
        
        Args:
            filepath: Path to document file
            validate_content: Whether to validate content length
            
        Returns:
            List of semantic units
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If unsupported file type or invalid content
        """
        logger.info(f"Processing document: {filepath}")
        
        # Stage 1: Load document
        text = self.loader.load_document(filepath)
        
        if validate_content and not self.loader.validate_content(text):
            raise ValueError(f"Document content too short or empty: {filepath}")
        
        logger.info(f"Document loaded: {len(text)} characters")
        
        # Stage 2: Detect headings
        headings = self.heading_detector.detect_headings(text)
        logger.info(f"Detected {len(headings)} headings")
        
        # Stage 3: Split into sections
        sections = self.heading_detector.split_by_headings(text, headings)
        logger.info(f"Split into {len(sections)} sections")
        
        # Stage 4: Segment into semantic units
        semantic_units = self.segmenter.segment_document(text, sections)
        logger.info(f"Created {len(semantic_units)} semantic units")
        
        # Add document metadata
        for unit in semantic_units:
            unit.metadata['source_file'] = str(Path(filepath).name)
            unit.metadata['source_path'] = str(filepath)
        
        logger.info(f"Document processing complete: {filepath}")
        return semantic_units
    
    def get_document_summary(self, semantic_units: List[SemanticUnit]) -> dict:
        """
        Generate a summary of processed document.
        
        Args:
            semantic_units: List of semantic units
            
        Returns:
            Dictionary with document statistics
        """
        if not semantic_units:
            return {
                'total_units': 0,
                'total_words': 0,
                'avg_words_per_unit': 0,
                'sections': {}
            }
        
        total_words = sum(unit.word_count for unit in semantic_units)
        avg_cohesion = sum(unit.similarity_score for unit in semantic_units) / len(semantic_units)
        
        # Group by section
        sections = {}
        for unit in semantic_units:
            section_type = unit.document_section
            if section_type not in sections:
                sections[section_type] = {
                    'count': 0,
                    'words': 0,
                    'titles': []
                }
            
            sections[section_type]['count'] += 1
            sections[section_type]['words'] += unit.word_count
            if unit.title and unit.title not in sections[section_type]['titles']:
                sections[section_type]['titles'].append(unit.title)
        
        return {
            'total_units': len(semantic_units),
            'total_words': total_words,
            'avg_words_per_unit': total_words / len(semantic_units),
            'avg_cohesion': avg_cohesion,
            'sections': sections,
            'source_file': semantic_units[0].metadata.get('source_file', 'unknown')
        }
