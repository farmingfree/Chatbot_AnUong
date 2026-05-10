"""
Run database migration to create conversations and messages tables
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import engine


async def run_migration():
    """Run SQL migration script"""
    sql_file = Path(__file__).parent / "create_conversations.sql"

    if not sql_file.exists():
        print(f"Migration file not found: {sql_file}")
        return False

    sql_content = sql_file.read_text(encoding='utf-8')

    print("Running migration: create_conversations.sql")

    try:
        async with engine.begin() as conn:
            # Remove comments and split by semicolon
            lines = [line for line in sql_content.split('\n') if not line.strip().startswith('--')]
            clean_sql = '\n'.join(lines)

            statements = [s.strip() + ';' for s in clean_sql.split(';') if s.strip()]

            for i, stmt in enumerate(statements, 1):
                if stmt.strip() and stmt.strip() != ';':
                    print(f"  [{i}/{len(statements)}] Executing...")
                    await conn.execute(text(stmt))

        print("\nMigration completed successfully!")
        return True

    except Exception as e:
        print(f"\nMigration failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_migration())
    sys.exit(0 if success else 1)
