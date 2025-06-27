#!/usr/bin/env python3
"""Export all conversations from the database to markdown files - non-interactive version."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List
import hashlib

sys.path.append("/app")

from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from app.models.database import Conversation, Message, Visitor
from app.core.database import get_db


async def get_total_conversations(db):
    """Get total number of conversations"""
    result = await db.execute(select(Conversation).where(Conversation.status != "test"))
    conversations = result.scalars().all()
    return len(conversations)


async def get_conversations(limit: int, db):
    """Get the most recent conversations"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.status != "test")
        .options(selectinload(Conversation.messages), selectinload(Conversation.visitor))
        .order_by(desc(Conversation.created_at))
        .limit(limit)
    )
    return result.scalars().all()


async def export_to_file(conversation, db):
    """Export a single conversation to a markdown file"""
    # Create exports directory if it doesn't exist
    export_dir = Path("/app/exports")
    export_dir.mkdir(exist_ok=True)
    
    # Get visitor info with anonymized ID
    visitor = conversation.visitor
    if visitor and visitor.fingerprint_id:
        # Create a hash of the fingerprint for privacy
        visitor_hash = hashlib.sha256(visitor.fingerprint_id.encode()).hexdigest()[:8]
        visitor_id = f"visitor_{visitor_hash}"
    else:
        visitor_id = "visitor_unknown"
    
    # Create filename
    timestamp = conversation.created_at.strftime("%Y%m%d_%H%M%S")
    filename = f"conversation_{timestamp}_{visitor_id}.md"
    filepath = export_dir / filename
    
    # Build markdown content
    content = f"# Conversation Export\n\n"
    content += f"**Date**: {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
    content += f"**Visitor**: {visitor_id}\n"
    content += f"**Status**: {conversation.status}\n"
    content += f"**Message Count**: {len(conversation.messages)}\n\n"
    content += "---\n\n"
    
    # Add messages
    for message in sorted(conversation.messages, key=lambda m: m.created_at):
        sender = "**User**" if message.sender_type == "user" else "**AI Assistant**"
        timestamp = message.created_at.strftime("%H:%M:%S")
        content += f"### {sender} ({timestamp})\n\n"
        content += f"{message.content}\n\n"
    
    # Write file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"  ✓ Exported: {filename}")


async def export_all():
    """Export all conversations"""
    print("🤖 Portfolio AI Conversation Export Tool - ALL")
    print("=" * 50)
    
    async for db in get_db():
        total = await get_total_conversations(db)
        print(f"\nTotal conversations in database: {total}")
        print(f"Exporting all {total} conversations...\n")
        
        conversations = await get_conversations(total, db)
        
        for conv in conversations:
            await export_to_file(conv, db)
        
        print(f"\n✅ Successfully exported {total} conversations to /app/exports/")
        break


async def export_last_n(n: int):
    """Export last N conversations"""
    print(f"🤖 Portfolio AI Conversation Export Tool - Last {n}")
    print("=" * 50)
    
    async for db in get_db():
        total = await get_total_conversations(db)
        limit = min(n, total)  # Don't exceed total
        print(f"\nTotal conversations in database: {total}")
        print(f"Exporting last {limit} conversations...\n")
        
        conversations = await get_conversations(limit, db)
        
        for conv in conversations:
            await export_to_file(conv, db)
        
        print(f"\n✅ Successfully exported {limit} conversations to /app/exports/")
        break


if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "all":
            asyncio.run(export_all())
        else:
            try:
                n = int(sys.argv[1])
                asyncio.run(export_last_n(n))
            except ValueError:
                print("Usage: python export_conversations_all.py [all|number]")
                print("  all    - Export all conversations")
                print("  50     - Export last 50 conversations")
                sys.exit(1)
    else:
        # Default to all
        asyncio.run(export_all())