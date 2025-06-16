#!/usr/bin/env python3
"""
Quick and dirty script to export conversations for review.
Run from the backend directory to use existing database config.
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Import our models directly since we're in backend now
from app.core.database import AsyncSessionLocal
from app.models.database import Conversation, Message, Visitor
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload


async def get_conversation_count():
    """Get total number of conversations"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count(Conversation.id)))
        return result.scalar()


async def get_conversations(limit: int):
    """Get conversations with their messages, ordered by most recent"""
    async with AsyncSessionLocal() as session:
        # Get conversations with messages and visitor info
        stmt = (
            select(Conversation)
            .options(
                selectinload(Conversation.messages),
                selectinload(Conversation.visitor)
            )
            .order_by(Conversation.started_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()


def format_conversation_to_md(conversation, index: int) -> str:
    """Format a conversation as markdown"""
    visitor_fingerprint = conversation.visitor.fingerprint_id if conversation.visitor else "unknown"
    
    md_content = f"""# Conversation {index + 1}

**Conversation ID:** {conversation.id}
**Visitor:** {visitor_fingerprint}
**Started:** {conversation.started_at.strftime('%Y-%m-%d %H:%M:%S')}
**Status:** {conversation.status}
**AI Model:** {conversation.ai_model_used or 'unknown'}
**Message Count:** {len(conversation.messages)}

---

"""

    # Sort messages by timestamp
    sorted_messages = sorted(conversation.messages, key=lambda m: m.timestamp)
    
    for msg in sorted_messages:
        sender_label = {
            'visitor': 'User',
            'ai': 'AI',
            'human_agent': 'Human Agent'
        }.get(msg.sender_type, msg.sender_type)
        
        timestamp = msg.timestamp.strftime('%H:%M:%S')
        md_content += f"**{sender_label}** ({timestamp}):\n{msg.content}\n\n"
    
    return md_content


async def main():
    print("🤖 Portfolio AI Conversation Export Tool")
    print("=" * 50)
    
    try:
        # Get total conversation count
        total_conversations = await get_conversation_count()
        print(f"Total conversations in database: {total_conversations}")
        
        if total_conversations == 0:
            print("No conversations found in the database.")
            return
        
        # Ask how many to export
        while True:
            try:
                limit = int(input(f"How many conversations would you like to export? (1-{total_conversations}): "))
                if 1 <= limit <= total_conversations:
                    break
                else:
                    print(f"Please enter a number between 1 and {total_conversations}")
            except ValueError:
                print("Please enter a valid number")
        
        print(f"\nFetching {limit} most recent conversations...")
        
        # Get conversations
        conversations = await get_conversations(limit)
        
        # Create exports directory - use /app/exports for persistent volume
        exports_dir = Path("/app/exports")
        exports_dir.mkdir(exist_ok=True)
        
        # Generate timestamp for this export batch
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print(f"Exporting {len(conversations)} conversations...")
        
        for i, conversation in enumerate(conversations):
            filename = f"conversation_{i+1}_{timestamp}.md"
            filepath = exports_dir / filename
            
            md_content = format_conversation_to_md(conversation, i)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            print(f"✅ Exported: {filename}")
        
        print(f"\n🎉 Export complete! Files saved to: {exports_dir}")
        print(f"📁 {len(conversations)} conversation files created")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    asyncio.run(main())