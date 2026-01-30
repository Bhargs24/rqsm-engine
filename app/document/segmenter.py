"""
Semantic Segmenter
Groups paragraphs into coherent semantic units using embeddings
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import numpy as np
from loguru import logger

from app.document.heading_detector import Heading


@dataclass
class SemanticUnit:
    """Represents a semantic unit (segment) of a document"""
    id: str                          # e.g., "S0_0", "S1_1"
    title: Optional[str]             # Section heading if available
    text: str                        # Main content
    document_section: str            # e.g., "introduction", "body", "conclusion"
    position: int                    # Order in document (0-indexed)
    similarity_score: float          # Cohesion score (0.0-1.0)
    word_count: int                  # Number of words
    metadata: Dict[str, Any]         # Additional context


class SemanticSegmenter:
    """Segments documents into semantic units"""
    
    def __init__(
        self,
        model_name: str = 'all-MiniLM-L6-v2',
        similarity_threshold: float = 0.75,
        min_group_size: int = 2,
        max_group_size: int = 5
    ):
        """
        Initialize semantic segmenter.
        
        Args:
            model_name: SentenceTransformer model name
            similarity_threshold: Minimum similarity for grouping paragraphs
            min_group_size: Minimum paragraphs per group
            max_group_size: Maximum paragraphs per group
        """
        logger.info(f"Initializing SemanticSegmenter with model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.similarity_threshold = similarity_threshold
        self.min_group_size = min_group_size
        self.max_group_size = max_group_size
        logger.info("SemanticSegmenter initialized")
    
    def segment_document(
        self,
        text: str,
        sections: List[Dict[str, Any]]
    ) -> List[SemanticUnit]:
        """
        Segment document into semantic units.
        
        Algorithm:
        1. For each section (from headings)
        2. Extract paragraphs
        3. Compute embeddings
        4. Group paragraphs by semantic similarity
        5. Create semantic units with metadata
        
        Args:
            text: Full document text
            sections: Document sections from heading detection
            
        Returns:
            List of semantic units
        """
        logger.debug("Starting document segmentation")
        units = []
        
        for section_id, section in enumerate(sections):
            logger.debug(f"Processing section {section_id}: {section.get('title', 'Untitled')}")
            
            # Extract paragraphs
            paragraphs = self._extract_paragraphs(section['text'])
            
            if not paragraphs:
                logger.warning(f"No paragraphs found in section {section_id}")
                continue
            
            logger.debug(f"Found {len(paragraphs)} paragraphs in section {section_id}")
            
            # Compute embeddings
            embeddings = self.model.encode(paragraphs, convert_to_numpy=True)
            
            # Group by similarity
            groups = self._group_by_similarity(paragraphs, embeddings)
            
            logger.debug(f"Created {len(groups)} groups in section {section_id}")
            
            # Create semantic units
            for group_id, group in enumerate(groups):
                # Get embeddings for this group
                group_indices = [paragraphs.index(p) for p in group]
                group_embeddings = embeddings[group_indices]
                
                unit = SemanticUnit(
                    id=f"S{section_id}_{group_id}",
                    title=section.get('title'),
                    text='\n\n'.join(group),
                    document_section=section.get('section_type', 'body'),
                    position=len(units),
                    similarity_score=self._compute_cohesion(group_embeddings),
                    word_count=sum(len(p.split()) for p in group),
                    metadata={
                        'heading_level': section.get('level', 0),
                        'paragraph_count': len(group),
                        'section_id': section_id,
                        'group_id': group_id
                    }
                )
                units.append(unit)
                
                logger.debug(
                    f"Created unit {unit.id}: {unit.word_count} words, "
                    f"cohesion={unit.similarity_score:.2f}"
                )
        
        logger.info(f"Document segmented into {len(units)} semantic units")
        return units
    
    def _extract_paragraphs(self, text: str) -> List[str]:
        """
        Extract non-empty paragraphs from text.
        
        Args:
            text: Section text
            
        Returns:
            List of paragraph strings
        """
        # Split by double newlines (paragraph separator)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # Filter out very short paragraphs (< 20 chars)
        paragraphs = [p for p in paragraphs if len(p) >= 20]
        
        return paragraphs
    
    def _group_by_similarity(
        self,
        paragraphs: List[str],
        embeddings: np.ndarray
    ) -> List[List[str]]:
        """
        Group paragraphs by semantic similarity.
        
        Algorithm:
        1. Start with first paragraph as seed
        2. Add subsequent paragraphs if similarity > threshold
        3. When similarity drops or max size reached, start new group
        4. Ensure minimum group size
        
        Args:
            paragraphs: List of paragraph strings
            embeddings: Paragraph embeddings (numpy array)
            
        Returns:
            List of paragraph groups
        """
        if len(paragraphs) == 0:
            return []
        
        if len(paragraphs) == 1:
            return [paragraphs]
        
        groups = []
        current_group = [paragraphs[0]]
        current_indices = [0]
        
        for i in range(1, len(paragraphs)):
            # Compute similarity with current group
            group_embeddings = embeddings[current_indices]
            group_centroid = np.mean(group_embeddings, axis=0)
            
            similarity = self._cosine_similarity(
                embeddings[i],
                group_centroid
            )
            
            # Check if we should add to current group
            can_add = (
                similarity >= self.similarity_threshold and
                len(current_group) < self.max_group_size
            )
            
            if can_add:
                current_group.append(paragraphs[i])
                current_indices.append(i)
            else:
                # Finalize current group
                groups.append(current_group)
                current_group = [paragraphs[i]]
                current_indices = [i]
        
        # Add final group
        if current_group:
            groups.append(current_group)
        
        # Post-process: merge groups that are too small
        groups = self._merge_small_groups(groups)
        
        return groups
    
    def _merge_small_groups(
        self,
        groups: List[List[str]]
    ) -> List[List[str]]:
        """
        Merge groups that are smaller than min_group_size.
        
        Args:
            groups: List of paragraph groups
            
        Returns:
            Merged groups
        """
        if len(groups) <= 1:
            return groups
        
        merged = []
        i = 0
        
        while i < len(groups):
            current_group = groups[i]
            
            # If group is too small and not the last group, merge with next
            if len(current_group) < self.min_group_size and i < len(groups) - 1:
                current_group.extend(groups[i + 1])
                i += 2
            else:
                i += 1
            
            merged.append(current_group)
        
        return merged
    
    def _compute_cohesion(self, embeddings: np.ndarray) -> float:
        """
        Compute cohesion score for a group of embeddings.
        
        Score is based on average pairwise cosine similarity.
        
        Args:
            embeddings: Group embeddings (numpy array)
            
        Returns:
            Cohesion score (0.0-1.0)
        """
        if len(embeddings) == 1:
            return 1.0
        
        # Compute pairwise similarities
        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = self._cosine_similarity(embeddings[i], embeddings[j])
                similarities.append(sim)
        
        cohesion = float(np.mean(similarities))
        return cohesion
    
    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity (0.0-1.0)
        """
        dot_product = np.dot(vec1, vec2)
        norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        
        if norm_product == 0:
            return 0.0
        
        return float(dot_product / norm_product)
