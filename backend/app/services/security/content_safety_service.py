"""Content safety service to prevent API violations."""

import re
from typing import Optional


class ContentSafetyService:
    """Service for filtering content that could violate AI provider terms."""

    def __init__(self, safety_patterns: list[str], safety_message: str):
        """
        Initialize the content safety service.

        Args:
            safety_patterns: List of regex patterns to check against
            safety_message: Message to return when content is blocked
        """
        self.safety_patterns = safety_patterns
        self.safety_message = safety_message

        # Compile regex patterns for better performance
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in safety_patterns
        ]

    def check_content_safety(self, message: str) -> tuple[bool, Optional[str]]:
        """
        Check if message contains content that could violate API terms.

        Args:
            message: The message content to check

        Returns:
            tuple[bool, Optional[str]]: (is_safe, violation_reason)
                - is_safe: True if content is safe, False if blocked
                - violation_reason: None if safe, safety message if blocked
        """
        if not message or not message.strip():
            return True, None

        for pattern in self.compiled_patterns:
            if pattern.search(message):
                print(
                    f"🚨 [SAFETY] Content filter triggered for message: {message[:100]}..."
                )
                return False, self.safety_message

        return True, None

    def is_content_safe(self, message: str) -> bool:
        """
        Simple boolean check if content is safe.

        Args:
            message: The message content to check

        Returns:
            bool: True if content is safe, False if blocked
        """
        is_safe, _ = self.check_content_safety(message)
        return is_safe
