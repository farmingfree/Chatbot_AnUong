#!/usr/bin/env python3
"""
Check conversation history database status
"""
import asyncio
import sys
from sqlalchemy import text
from app.database import AsyncSessionLocal, engine

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


async def check_database():
    print("=" * 60)
    print("Checking Conversation History Database")
    print("=" * 60)

    try:
        # Check connection
        print("\n[1/4] Testing database connection...")
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("   [OK] Database connected")

        # Check tables exist
        print("\n[2/4] Checking tables...")
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='public'
                AND table_name IN ('conversations', 'messages')
            """))
            tables = [row[0] for row in result]

            if 'conversations' in tables:
                print("   ✅ conversations table exists")
            else:
                print("   ❌ conversations table NOT FOUND")
                print("      Run: python -m migrations.run_migration")
                return

            if 'messages' in tables:
                print("   ✅ messages table exists")
            else:
                print("   ❌ messages table NOT FOUND")
                return

        # Check data
        print("\n[3/4] Checking data...")
        async with AsyncSessionLocal() as db:
            # Count conversations
            result = await db.execute(text("SELECT COUNT(*) FROM conversations"))
            conv_count = result.scalar()
            print(f"   📊 Conversations: {conv_count}")

            # Count messages
            result = await db.execute(text("SELECT COUNT(*) FROM messages"))
            msg_count = result.scalar()
            print(f"   📊 Messages: {msg_count}")

            # Show recent conversations
            if conv_count > 0:
                print("\n   Recent conversations:")
                result = await db.execute(text("""
                    SELECT id, title, message_count, created_at
                    FROM conversations
                    ORDER BY created_at DESC
                    LIMIT 5
                """))
                for row in result:
                    print(f"   - {row[1][:50]} ({row[2]} messages)")

        # Check indexes
        print("\n[4/4] Checking indexes...")
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename IN ('conversations', 'messages')
            """))
            indexes = [row[0] for row in result]
            print(f"   📊 Found {len(indexes)} indexes")

            required_indexes = [
                'ix_conversations_user_id',
                'ix_conversations_created_at',
                'ix_messages_conversation_id',
                'ix_messages_created_at'
            ]

            for idx in required_indexes:
                if idx in indexes:
                    print(f"   ✅ {idx}")
                else:
                    print(f"   ⚠️  {idx} missing (optional)")

        print("\n" + "=" * 60)
        print("✅ Database check completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check DATABASE_URL in .env")
        print("3. Run migrations: python -m migrations.run_migration")


if __name__ == "__main__":
    asyncio.run(check_database())
