#!/usr/bin/env python3
"""
Database viewing utility for the Portfolio AI Assistant.

This script provides easy access to view the database contents with various
predefined queries and the ability to run custom SQL queries.
"""

import sys
import os
import asyncio
import argparse
from datetime import datetime
from typing import Dict, Any, List

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.models.database import (
    Visitor, Conversation, Message, PortfolioContent, 
    KnowledgeSource, ConversationQuote, HumanAgent
)


class DatabaseViewer:
    """Database viewing utility class."""
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = AsyncSessionLocal()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict]:
        """Execute a raw SQL query and return results."""
        result = await self.session.execute(text(query), params or {})
        columns = result.keys()
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    
    async def table_counts(self) -> Dict[str, int]:
        """Get record counts for all tables."""
        queries = {
            'visitors': "SELECT COUNT(*) as count FROM visitors",
            'conversations': "SELECT COUNT(*) as count FROM conversations", 
            'messages': "SELECT COUNT(*) as count FROM messages",
            'portfolio_content': "SELECT COUNT(*) as count FROM portfolio_content",
            'knowledge_sources': "SELECT COUNT(*) as count FROM knowledge_sources",
            'conversation_quotes': "SELECT COUNT(*) as count FROM conversation_quotes",
            'human_agents': "SELECT COUNT(*) as count FROM human_agents"
        }
        
        counts = {}
        for table, query in queries.items():
            result = await self.execute_query(query)
            counts[table] = result[0]['count']
        
        return counts
    
    async def recent_activity(self, limit: int = 10) -> List[Dict]:
        """Get recent visitor activity."""
        query = """
        SELECT 
            v.fingerprint_id,
            v.first_seen_at,
            v.last_seen_at,
            COUNT(DISTINCT c.id) as conversation_count,
            COUNT(m.id) as message_count
        FROM visitors v 
        LEFT JOIN conversations c ON v.id = c.visitor_id 
        LEFT JOIN messages m ON c.id = m.conversation_id 
        GROUP BY v.id, v.fingerprint_id, v.first_seen_at, v.last_seen_at 
        ORDER BY v.last_seen_at DESC 
        LIMIT :limit
        """
        return await self.execute_query(query, {'limit': limit})
    
    async def conversation_details(self, visitor_fingerprint: str = None, limit: int = 5) -> List[Dict]:
        """Get conversation details, optionally filtered by visitor."""
        if visitor_fingerprint:
            query = """
            SELECT 
                c.id as conversation_id,
                v.fingerprint_id,
                c.started_at,
                c.last_message_at,
                c.status,
                c.ai_model_used,
                COUNT(m.id) as message_count
            FROM conversations c
            JOIN visitors v ON c.visitor_id = v.id
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE v.fingerprint_id = :fingerprint
            GROUP BY c.id, v.fingerprint_id, c.started_at, c.last_message_at, c.status, c.ai_model_used
            ORDER BY c.started_at DESC
            LIMIT :limit
            """
            params = {'fingerprint': visitor_fingerprint, 'limit': limit}
        else:
            query = """
            SELECT 
                c.id as conversation_id,
                v.fingerprint_id,
                c.started_at,
                c.last_message_at,
                c.status,
                c.ai_model_used,
                COUNT(m.id) as message_count
            FROM conversations c
            JOIN visitors v ON c.visitor_id = v.id
            LEFT JOIN messages m ON c.id = m.conversation_id
            GROUP BY c.id, v.fingerprint_id, c.started_at, c.last_message_at, c.status, c.ai_model_used
            ORDER BY c.started_at DESC
            LIMIT :limit
            """
            params = {'limit': limit}
        
        return await self.execute_query(query, params)
    
    async def conversation_messages(self, conversation_id: str) -> List[Dict]:
        """Get all messages for a specific conversation."""
        query = """
        SELECT 
            m.id,
            m.sender_type,
            m.content,
            m.timestamp,
            m.message_metadata
        FROM messages m
        WHERE m.conversation_id = :conv_id
        ORDER BY m.timestamp ASC
        """
        return await self.execute_query(query, {'conv_id': conversation_id})
    
    async def portfolio_content_summary(self) -> List[Dict]:
        """Get portfolio content summary by type and source."""
        query = """
        SELECT 
            pc.content_type,
            ks.source_name,
            COUNT(*) as chunk_count,
            AVG(LENGTH(pc.content_chunk)) as avg_chunk_length
        FROM portfolio_content pc
        JOIN knowledge_sources ks ON pc.knowledge_source_id = ks.id
        GROUP BY pc.content_type, ks.source_name
        ORDER BY pc.content_type, ks.source_name
        """
        return await self.execute_query(query)
    
    async def search_portfolio_content(self, search_term: str, limit: int = 10) -> List[Dict]:
        """Search portfolio content by text."""
        query = """
        SELECT 
            pc.content_type,
            pc.title,
            ks.source_name,
            pc.chunk_index,
            SUBSTRING(pc.content_chunk, 1, 200) as content_preview
        FROM portfolio_content pc
        JOIN knowledge_sources ks ON pc.knowledge_source_id = ks.id
        WHERE pc.content_chunk ILIKE :search_term
        ORDER BY pc.content_type, ks.source_name, pc.chunk_index
        LIMIT :limit
        """
        return await self.execute_query(query, {'search_term': f'%{search_term}%', 'limit': limit})


def format_datetime(dt_str: str) -> str:
    """Format datetime string for display."""
    if not dt_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return dt_str


def print_table(data: List[Dict], title: str = None):
    """Print data in a formatted table."""
    if not data:
        print("No data found.")
        return
    
    if title:
        print(f"\n=== {title} ===")
    
    # Get column names
    columns = list(data[0].keys())
    
    # Calculate column widths
    widths = {}
    for col in columns:
        max_width = len(col)
        for row in data:
            value = str(row[col]) if row[col] is not None else "NULL"
            max_width = max(max_width, len(value))
        widths[col] = min(max_width, 50)  # Cap at 50 chars
    
    # Print header
    header = " | ".join(col.ljust(widths[col]) for col in columns)
    print(header)
    print("-" * len(header))
    
    # Print rows
    for row in data:
        formatted_row = []
        for col in columns:
            value = str(row[col]) if row[col] is not None else "NULL"
            if len(value) > widths[col]:
                value = value[:widths[col]-3] + "..."
            formatted_row.append(value.ljust(widths[col]))
        print(" | ".join(formatted_row))


async def main():
    """Main function to handle command line arguments and execute queries."""
    parser = argparse.ArgumentParser(description='View Portfolio AI Assistant Database')
    parser.add_argument('--counts', action='store_true', help='Show table record counts')
    parser.add_argument('--activity', type=int, default=10, help='Show recent visitor activity (default: 10)')
    parser.add_argument('--conversations', type=int, default=5, help='Show recent conversations (default: 5)')
    parser.add_argument('--visitor', type=str, help='Show conversations for specific visitor fingerprint')
    parser.add_argument('--messages', type=str, help='Show messages for specific conversation ID')
    parser.add_argument('--portfolio', action='store_true', help='Show portfolio content summary')
    parser.add_argument('--search', type=str, help='Search portfolio content')
    parser.add_argument('--sql', type=str, help='Execute custom SQL query')
    
    args = parser.parse_args()
    
    # If no specific action, show overview
    if not any([args.counts, args.conversations, args.visitor, args.messages, 
                args.portfolio, args.search, args.sql]):
        args.counts = True
        args.activity = 10
        args.conversations = 5
        args.portfolio = True
    
    async with DatabaseViewer() as db:
        if args.counts:
            counts = await db.table_counts()
            print("\n=== Table Record Counts ===")
            for table, count in counts.items():
                print(f"{table}: {count:,}")
        
        if args.activity:
            activity = await db.recent_activity(args.activity)
            print_table(activity, f"Recent Visitor Activity (Last {args.activity})")
        
        if args.conversations or args.visitor:
            conversations = await db.conversation_details(args.visitor, args.conversations)
            title = f"Conversations for {args.visitor}" if args.visitor else f"Recent Conversations (Last {args.conversations})"
            print_table(conversations, title)
        
        if args.messages:
            messages = await db.conversation_messages(args.messages)
            print_table(messages, f"Messages for Conversation {args.messages}")
        
        if args.portfolio:
            portfolio = await db.portfolio_content_summary()
            print_table(portfolio, "Portfolio Content Summary")
        
        if args.search:
            search_results = await db.search_portfolio_content(args.search)
            print_table(search_results, f"Search Results for '{args.search}'")
        
        if args.sql:
            try:
                results = await db.execute_query(args.sql)
                print_table(results, "Custom Query Results")
            except Exception as e:
                print(f"Error executing query: {e}")


if __name__ == "__main__":
    asyncio.run(main())