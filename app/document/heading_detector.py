"""
Heading Detector
Identifies section headings in documents to guide segmentation
"""
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from loguru import logger


@dataclass
class Heading:
    """Represents a document heading"""
    text: str
    level: int          # 1 = top-level, 2 = subsection, etc.
    position: int       # Character position in document
    line_number: int    # Line number in document


class HeadingDetector:
    """Detects headings in plain text documents"""
    
    def __init__(self):
        """Initialize heading detector"""
        logger.info("HeadingDetector initialized")
    
    def detect_headings(self, text: str) -> List[Heading]:
        """
        Detect document headings using regex patterns.
        
        Patterns:
        1. ALL CAPS LINES (e.g., "INTRODUCTION")
        2. Numbered headings (e.g., "1. Overview", "1.1 Details")
        3. Lines followed by underlines (===, ---)
        4. Short lines with title case at start of paragraphs
        
        Args:
            text: Full document text
            
        Returns:
            List of detected headings with metadata
        """
        logger.debug("Detecting headings in document")
        
        headings = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            if not line_stripped:
                continue
            
            # Pattern 1: ALL CAPS (at least 3 words, max 10 words)
            words = line_stripped.split()
            if (line_stripped.isupper() and 
                3 <= len(words) <= 10 and
                not any(char.isdigit() for char in line_stripped[:3])):
                
                headings.append(Heading(
                    text=line_stripped,
                    level=1,
                    position=sum(len(l) + 1 for l in lines[:i]),
                    line_number=i
                ))
                logger.debug(f"Found ALL CAPS heading at line {i}: {line_stripped}")
                continue
            
            # Pattern 2: Numbered headings (e.g., "1.", "1.1", "1.1.1")
            numbered_match = re.match(r'^((?:\d+\.)+)\s+(.+)$', line_stripped)
            if numbered_match:
                level = numbered_match.group(1).count('.')
                heading_text = numbered_match.group(2)
                
                headings.append(Heading(
                    text=heading_text,
                    level=level,
                    position=sum(len(l) + 1 for l in lines[:i]),
                    line_number=i
                ))
                logger.debug(f"Found numbered heading at line {i}: {heading_text} (level {level})")
                continue
            
            # Pattern 3: Underlined headings
            if i > 0 and re.match(r'^[=\-]{3,}$', line_stripped):
                prev_line = lines[i-1].strip()
                if prev_line and len(prev_line.split()) <= 10:
                    level = 1 if '=' in line_stripped else 2
                    
                    headings.append(Heading(
                        text=prev_line,
                        level=level,
                        position=sum(len(l) + 1 for l in lines[:i-1]),
                        line_number=i-1
                    ))
                    logger.debug(f"Found underlined heading at line {i-1}: {prev_line} (level {level})")
                    continue
        
        logger.info(f"Detected {len(headings)} headings")
        return headings
    
    def build_hierarchy(self, headings: List[Heading]) -> Dict[str, Any]:
        """
        Build hierarchical document structure from headings.
        
        Args:
            headings: List of detected headings
            
        Returns:
            Nested dict representing document structure
        """
        if not headings:
            return {}
        
        hierarchy = {
            'title': 'Document',
            'level': 0,
            'children': []
        }
        
        stack = [hierarchy]
        
        for heading in headings:
            node = {
                'title': heading.text,
                'level': heading.level,
                'line_number': heading.line_number,
                'position': heading.position,
                'children': []
            }
            
            # Find correct parent level
            while len(stack) > 1 and stack[-1]['level'] >= heading.level:
                stack.pop()
            
            stack[-1]['children'].append(node)
            stack.append(node)
        
        logger.debug(f"Built document hierarchy with {len(headings)} nodes")
        return hierarchy
    
    def split_by_headings(
        self,
        text: str,
        headings: List[Heading]
    ) -> List[Dict[str, Any]]:
        """
        Split document into sections based on headings.
        
        Args:
            text: Full document text
            headings: List of detected headings
            
        Returns:
            List of sections with metadata
        """
        if not headings:
            # No headings found, treat entire document as one section
            return [{
                'title': 'Document',
                'text': text,
                'level': 0,
                'section_type': 'body',
                'start_pos': 0,
                'end_pos': len(text)
            }]
        
        sections = []
        lines = text.split('\n')
        
        for i, heading in enumerate(headings):
            # Determine section boundaries
            start_line = heading.line_number + 1  # Start after heading
            
            if i + 1 < len(headings):
                end_line = headings[i + 1].line_number
            else:
                end_line = len(lines)
            
            # Extract section text
            section_lines = lines[start_line:end_line]
            section_text = '\n'.join(section_lines).strip()
            
            if section_text:  # Only add non-empty sections
                sections.append({
                    'title': heading.text,
                    'text': section_text,
                    'level': heading.level,
                    'section_type': self._classify_section(heading.text),
                    'start_pos': heading.position,
                    'end_pos': sum(len(l) + 1 for l in lines[:end_line])
                })
        
        logger.info(f"Split document into {len(sections)} sections")
        return sections
    
    @staticmethod
    def _classify_section(heading_text: str) -> str:
        """
        Classify section type based on heading text.
        
        Args:
            heading_text: Heading text
            
        Returns:
            Section type: 'introduction', 'conclusion', 'methodology', or 'body'
        """
        heading_lower = heading_text.lower()
        
        # Introduction keywords
        if any(kw in heading_lower for kw in [
            'introduction', 'overview', 'background', 'preface', 'abstract'
        ]):
            return 'introduction'
        
        # Conclusion keywords
        if any(kw in heading_lower for kw in [
            'conclusion', 'summary', 'final', 'closing', 'recap'
        ]):
            return 'conclusion'
        
        # Methodology keywords
        if any(kw in heading_lower for kw in [
            'method', 'approach', 'implementation', 'procedure', 'experiment'
        ]):
            return 'methodology'
        
        # Default to body
        return 'body'
