#!/usr/bin/env python3
"""
Force Re-ingest All Portfolio Content

This script wipes all existing content and re-ingests everything from scratch.

Usage:
    python scripts/reingest_all.py
"""

import asyncio
import sys
from pathlib import Path
from sqlalchemy import delete

# Add the backend directory to Python path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.core.database import AsyncSessionLocal
from app.models.database import KnowledgeSource, PortfolioContent


async def wipe_and_reingest():
    """Wipe all content and re-run the ingest script."""
    print("🗑️  Wiping all existing portfolio content...")

    async with AsyncSessionLocal() as session:
        # Delete all portfolio content
        await session.execute(delete(PortfolioContent))
        print("   ✅ Deleted all PortfolioContent")

        # Delete all knowledge sources
        await session.execute(delete(KnowledgeSource))
        print("   ✅ Deleted all KnowledgeSource records")

        await session.commit()

    print("🔄 Starting fresh ingestion...")

    # Import and run the original ingester (without force flag since we already wiped)
    from ingest_portfolio import PortfolioIngester

    ingester = PortfolioIngester(
        force_reingest=False
    )  # No force needed, everything is gone
    await ingester.ingest_all_content()

    print("✅ Complete re-ingestion finished!")


if __name__ == "__main__":
    asyncio.run(wipe_and_reingest())
