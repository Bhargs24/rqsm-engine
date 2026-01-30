"""
Unit Tests for Heading Detector
"""
import pytest

from app.document.heading_detector import HeadingDetector, Heading


class TestHeadingDetector:
    """Test suite for HeadingDetector"""
    
    def test_initialization(self):
        """Test HeadingDetector initialization"""
        detector = HeadingDetector()
        assert detector is not None
    
    def test_detect_all_caps_headings(self):
        """Test detection of ALL CAPS headings"""
        detector = HeadingDetector()
        text = """INTRODUCTION TO TESTING

This is some content under the heading.

METHODS AND PROCEDURES

More content here."""
        
        headings = detector.detect_headings(text)
        
        assert len(headings) == 2
        assert headings[0].text == "INTRODUCTION TO TESTING"
        assert headings[0].level == 1
        assert headings[1].text == "METHODS AND PROCEDURES"
        assert headings[1].level == 1
    
    def test_detect_numbered_headings(self):
        """Test detection of numbered headings"""
        detector = HeadingDetector()
        text = """1. Introduction

Some content here.

1.1 Background

More content.

2. Methods

Final section."""
        
        headings = detector.detect_headings(text)
        
        # Should detect at least 2 headings (1. and 2.)
        assert len(headings) >= 2
        
        # Find the numbered headings
        intro = next(h for h in headings if "Introduction" in h.text)
        assert intro.level == 1
        
        methods = next(h for h in headings if "Methods" in h.text)
        assert methods.level == 1
    
    def test_detect_underlined_headings(self):
        """Test detection of underlined headings"""
        detector = HeadingDetector()
        text = """Introduction
============

Some content here.

Methods
-------

More content."""
        
        headings = detector.detect_headings(text)
        
        assert len(headings) == 2
        assert headings[0].text == "Introduction"
        assert headings[0].level == 1
        assert headings[1].text == "Methods"
        assert headings[1].level == 2
    
    def test_no_headings(self):
        """Test document with no headings"""
        detector = HeadingDetector()
        text = """This is a simple document with no headings.
Just plain paragraphs of text throughout."""
        
        headings = detector.detect_headings(text)
        assert len(headings) == 0
    
    def test_split_by_headings(self):
        """Test splitting document into sections"""
        detector = HeadingDetector()
        text = """INTRODUCTION AND OVERVIEW

This is the introduction.

METHODS AND PROCEDURES

This is the methods section."""
        
        headings = detector.detect_headings(text)
        sections = detector.split_by_headings(text, headings)
        
        assert len(sections) == 2
        assert sections[0]['title'] == "INTRODUCTION AND OVERVIEW"
        assert "introduction" in sections[0]['text'].lower()
        assert sections[1]['title'] == "METHODS AND PROCEDURES"
        assert "methods" in sections[1]['text'].lower()
    
    def test_split_no_headings(self):
        """Test splitting document with no headings"""
        detector = HeadingDetector()
        text = "Just plain text without headings."
        
        headings = detector.detect_headings(text)
        sections = detector.split_by_headings(text, headings)
        
        assert len(sections) == 1
        assert sections[0]['title'] == "Document"
        assert sections[0]['section_type'] == "body"
    
    def test_classify_section_introduction(self):
        """Test section classification for introduction"""
        detector = HeadingDetector()
        
        assert detector._classify_section("Introduction") == "introduction"
        assert detector._classify_section("BACKGROUND") == "introduction"
        assert detector._classify_section("Overview") == "introduction"
    
    def test_classify_section_conclusion(self):
        """Test section classification for conclusion"""
        detector = HeadingDetector()
        
        assert detector._classify_section("Conclusion") == "conclusion"
        assert detector._classify_section("SUMMARY") == "conclusion"
        assert detector._classify_section("Final Remarks") == "conclusion"
    
    def test_classify_section_methodology(self):
        """Test section classification for methodology"""
        detector = HeadingDetector()
        
        assert detector._classify_section("Methods") == "methodology"
        assert detector._classify_section("APPROACH") == "methodology"
        assert detector._classify_section("Implementation") == "methodology"
    
    def test_classify_section_body(self):
        """Test section classification for body"""
        detector = HeadingDetector()
        
        assert detector._classify_section("Main Content") == "body"
        assert detector._classify_section("Discussion") == "body"
