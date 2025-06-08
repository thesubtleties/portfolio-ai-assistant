#!/usr/bin/env python3
"""
Load quotes from JSON file into database.

Usage:
    python scripts/load_quotes.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the backend directory to Python path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.core.database import AsyncSessionLocal
from app.models.database import ConversationQuote
from sqlalchemy import select, text


async def load_quotes():
    """Load quotes from noir-quotes.json into database."""
    
    # Load quotes from JSON file
    quotes_file = Path(__file__).parent.parent / "noir-quotes.json"
    
    if not quotes_file.exists():
        print(f"❌ Quotes file not found: {quotes_file}")
        return
    
    try:
        with open(quotes_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            quotes = data.get('noir_quotes', [])
    except Exception as e:
        print(f"❌ Error reading quotes file: {e}")
        return
    
    if not quotes:
        print("❌ No quotes found in file")
        return
    
    print(f"📚 Found {len(quotes)} quotes to load")
    
    # Insert quotes into database
    async with AsyncSessionLocal() as session:
        inserted_count = 0
        
        for quote_text in quotes:
            # Check if quote already exists
            stmt = select(ConversationQuote).where(ConversationQuote.quote_text == quote_text)
            result = await session.execute(stmt)
            existing_quote = result.scalar_one_or_none()
            
            if existing_quote:
                print(f"⏭️  Skipping duplicate quote: {quote_text[:50]}...")
                continue
            
            # Insert new quote
            quote = ConversationQuote(
                quote_text=quote_text,
                category="noir"
            )
            session.add(quote)
            inserted_count += 1
            
            print(f"✅ Added: {quote_text[:50]}...")
        
        await session.commit()
        
    print(f"\n🎉 Successfully loaded {inserted_count} quotes into database!")
    print(f"📊 Skipped {len(quotes) - inserted_count} duplicates")


if __name__ == "__main__":
    asyncio.run(load_quotes())