"""Content safety tool following Atomic Agents BaseTool pattern."""

from typing import List, Optional
from pydantic import Field
from atomic_agents.lib.base.base_tool import BaseTool, BaseToolConfig
from atomic_agents.lib.base.base_io_schema import BaseIOSchema

from app.services.security.content_safety_service import ContentSafetyService


class ContentSafetyToolConfig(BaseToolConfig):
    """Configuration for the content safety tool."""
    
    safety_patterns: List[str] = Field(
        default_factory=list,
        description="List of regex patterns to check for unsafe content"
    )
    
    safety_message: str = Field(
        default="Please keep our conversation focused on portfolio topics.",
        description="Message to return when unsafe content is detected"
    )


class ContentSafetyInputSchema(BaseIOSchema):
    """
    Input schema for content safety checking.
    """
    
    message: str = Field(
        ...,
        description="The message content to check for safety violations"
    )


class ContentSafetyOutputSchema(BaseIOSchema):
    """
    Output schema for content safety check results.
    """
    
    is_safe: bool = Field(
        ...,
        description="Whether the content is considered safe"
    )
    
    violation_message: Optional[str] = Field(
        default=None,
        description="Message explaining the violation if content is unsafe"
    )
    
    patterns_matched: List[str] = Field(
        default_factory=list,
        description="List of safety patterns that were matched (for debugging)"
    )


class ContentSafetyTool(BaseTool):
    """
    Tool for checking content safety to prevent API violations.
    
    This tool integrates content safety filtering into the Atomic Agents
    framework, providing structured safety checking with configurable
    patterns and responses.
    """
    
    input_schema = ContentSafetyInputSchema
    output_schema = ContentSafetyOutputSchema
    
    def __init__(self, config: ContentSafetyToolConfig = ContentSafetyToolConfig()):
        """Initialize the content safety tool."""
        super().__init__(config)
        self.safety_service = ContentSafetyService(
            safety_patterns=config.safety_patterns,
            safety_message=config.safety_message
        )
        self.config = config
    
    def run(self, params: ContentSafetyInputSchema) -> ContentSafetyOutputSchema:
        """
        Check content for safety violations.
        
        Args:
            params: Content to check for safety
            
        Returns:
            Safety check results with violation details if unsafe
        """
        is_safe, violation_message = self.safety_service.check_content_safety(
            params.message
        )
        
        # For debugging, we could track which patterns matched
        # This would require modifying the ContentSafetyService
        patterns_matched = []
        if not is_safe:
            # In a more advanced implementation, we could return
            # which specific patterns were triggered
            patterns_matched = ["content_safety_violation"]
        
        return ContentSafetyOutputSchema(
            is_safe=is_safe,
            violation_message=violation_message,
            patterns_matched=patterns_matched
        )
    
    def get_tool_description(self) -> str:
        """Get a description of what this tool does."""
        return (
            "Check message content for safety violations that could lead to "
            "API provider bans. Uses configurable regex patterns to detect "
            "harmful content and returns appropriate safety messages."
        )