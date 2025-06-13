#!/usr/bin/env python3
"""
Test the new weighted query classification system.
"""

import sys
from pathlib import Path

# Add the backend directory to Python path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.services.portfolio_agent_service import PortfolioAgentService
from app.core.database import AsyncSessionLocal


class ClassificationTester:
    """Test the weighted classification system."""
    
    def __init__(self):
        # Create a mock service to test classification
        self.service = PortfolioAgentService.__new__(PortfolioAgentService)
    
    def test_classification_scenarios(self):
        """Test various query scenarios."""
        print("🧠 Testing Weighted Query Classification")
        print("=" * 60)
        print()
        
        test_queries = [
            {
                "query": "What databases does Steven work with?",
                "expected": "specific_content", 
                "reason": "Database = specific tech term"
            },
            {
                "query": "What's the URL for Atria?",
                "expected": "specific_content",
                "reason": "Project name + URL = high specific score"
            },
            {
                "query": "Tell me about Atria's tech stack",
                "expected": "specific_content", 
                "reason": "Project name beats tech terms"
            },
            {
                "query": "What FastAPI architecture patterns does Steven use?",
                "expected": "technical_conceptual",
                "reason": "Architecture + patterns = conceptual"
            },
            {
                "query": "Tell me about all of Steven's projects",
                "expected": "broad_overview",
                "reason": "Broad overview phrase"
            },
            {
                "query": "What's Steven's background?",
                "expected": "personal_background",
                "reason": "Personal terms"
            },
            {
                "query": "Show me React components",
                "expected": "technical_conceptual",
                "reason": "React + components = technical concept"
            },
            {
                "query": "Atria React components",
                "expected": "specific_content",
                "reason": "Project name outweighs tech terms"
            }
        ]
        
        for i, test in enumerate(test_queries, 1):
            result = self.service._classify_query(test["query"])
            status = "✅" if result == test["expected"] else "❌"
            
            print(f"{status} Test {i}: {test['query']}")
            print(f"   Expected: {test['expected']}")
            print(f"   Got: {result}")
            print(f"   Reason: {test['reason']}")
            print()
    
    def test_scoring_details(self):
        """Show detailed scoring for complex queries."""
        print("🔢 Detailed Scoring Analysis")
        print("=" * 40)
        print()
        
        # Test a complex query
        query = "What's Atria's database stack?"
        print(f"Query: '{query}'")
        print()
        
        # Manually calculate scores to show the logic
        query_lower = query.lower()
        
        # Project names
        project_names = ["atria", "spookyspot", "taskflow", "hills house", "hillshouse", "styleatc", "linkedin", "portfolio"]
        project_matches = sum(1 for name in project_names if name in query_lower)
        print(f"Project matches: {project_matches} * 4 = {project_matches * 4} points to specific_content")
        
        # Tech terms
        specific_terms = ["database", "stack", "technologies", "tools"]
        specific_matches = sum(1 for term in specific_terms if term in query_lower)
        print(f"Specific tech matches: {specific_matches} * 2 = {specific_matches * 2} points to specific_content")
        print(f"Specific tech matches: {specific_matches} * 1 = {specific_matches * 1} points to technical_conceptual")
        
        print()
        print(f"Total specific_content score: {project_matches * 4 + specific_matches * 2}")
        print(f"Total technical_conceptual score: {specific_matches * 1}")
        print()
        
        result = self.service._classify_query(query)
        print(f"Final classification: {result}")
        print()


def main():
    """Main entry point."""
    print("🤖 Portfolio AI Assistant - Classification Testing")
    print()
    
    tester = ClassificationTester()
    tester.test_classification_scenarios()
    tester.test_scoring_details()


if __name__ == "__main__":
    main()