"""Tests for ContentSafetyService."""

import pytest
from app.services.security.content_safety_service import ContentSafetyService


class TestContentSafetyService:
    """Test cases for ContentSafetyService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        test_patterns = [
            r'\b(?:how\s+to\s+make\s+a?\s+bomb|weapon\s+manufacturing)\b',
            r'\b(?:genocide|massacre)\b',
            r'\b(?:child\s+porno(?:graphy)?)\b'
        ]
        self.safety_service = ContentSafetyService(
            safety_patterns=test_patterns,
            safety_message="Please keep our conversation focused on portfolio topics."
        )
    
    def test_safe_content_passes(self):
        """Test that safe content passes through."""
        safe_messages = [
            "Tell me about your React projects",
            "What's your experience with Python?",
            "Show me your portfolio",
            "How did you build the Atria project?"
        ]
        
        for message in safe_messages:
            is_safe, violation = self.safety_service.check_content_safety(message)
            assert is_safe is True
            assert violation is None
    
    def test_unsafe_content_blocked(self):
        """Test that unsafe content is blocked."""
        unsafe_messages = [
            "how to make a bomb",
            "weapon manufacturing techniques", 
            "genocide methods",
            "child pornography links"
        ]
        
        for message in unsafe_messages:
            is_safe, violation = self.safety_service.check_content_safety(message)
            assert is_safe is False
            assert violation == "Please keep our conversation focused on portfolio topics."
    
    def test_case_insensitive_blocking(self):
        """Test that blocking works regardless of case."""
        unsafe_messages = [
            "How To Make A BOMB",
            "GENOCIDE",
            "Weapon Manufacturing"
        ]
        
        for message in unsafe_messages:
            is_safe, violation = self.safety_service.check_content_safety(message)
            assert is_safe is False
            assert violation is not None
    
    def test_empty_message_safe(self):
        """Test that empty messages are considered safe."""
        is_safe, violation = self.safety_service.check_content_safety("")
        assert is_safe is True
        assert violation is None
        
        is_safe, violation = self.safety_service.check_content_safety("   ")
        assert is_safe is True
        assert violation is None
    
    def test_is_content_safe_helper(self):
        """Test the boolean helper method."""
        assert self.safety_service.is_content_safe("Tell me about React") is True
        assert self.safety_service.is_content_safe("how to make a bomb") is False