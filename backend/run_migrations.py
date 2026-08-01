"""
Database Migration Runner for Supabase

Applies SQL migration files in order to a Supabase database.
Run this script to set up the database schema.

Usage:
    python run_migrations.py
    python run_migrations.py --dry-run
    python run_migrations.py --migration 001
"""
import argparse
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from supabase import create_client
from app.core.config import settings


def get_migration_files() -> list[Path]:
    """Get all migration files in order."""
    migrations_dir = Path(__file__).parent / "migrations"
    if not migrations_dir.exists():
        return []

    files = sorted(migrations_dir.glob("*.sql"))
    return files


def read_migration(file_path: Path) -> str:
    """Read migration SQL file."""
    return file_path.read_text()


def apply_migration(client, sql: str, dry_run: bool = False) -> bool:
    """Apply a single migration."""
    if dry_run:
        print(f"[DRY RUN] Would execute:")
        print(sql[:500] + ("..." if len(sql) > 500 else ""))
        return True

    try:
        # Execute raw SQL via PostgREST
        # Supabase doesn't have a direct raw SQL endpoint via the Python client
        # We need to use the RPC function or direct Postgres connection
        # For now, we'll use the REST API with a raw query
        import httpx

        url = f"{settings.SUPABASE_URL}/rest/v1/rpc/exec_sql"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json",
        }

        # Note: exec_sql RPC may not exist by default in Supabase
        # Alternative: Use the SQL Editor or psql directly
        print("Note: Direct SQL execution via Supabase Python client is limited.")
        print("Please run migrations via:")
        print(f"  1. Supabase Dashboard > SQL Editor")
        print(f"  2. Or: psql postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres")
        return False

    except Exception as e:
        print(f"Error applying migration: {e}")
        return False


def print_migration_instructions():
    """Print instructions for running migrations."""
    migrations = get_migration_files()

    print("=" * 60)
    print("SUPABASE MIGRATION INSTRUCTIONS")
    print("=" * 60)
    print()
    print("Option 1: Supabase Dashboard (Recommended)")
    print("  1. Go to https://supabase.com/dashboard/project/_/sql")
    print("  2. Copy and paste each migration file content")
    print("  3. Run in order:")
    for m in migrations:
        print(f"     - {m.name}")
    print()

    print("Option 2: psql command line")
    print("  psql \"postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres\" -f backend/migrations/001_initial_schema.sql")
    print("  psql \"postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres\" -f backend/migrations/002_rls_policies.sql")
    print()

    print("Option 3: Supabase CLI")
    print("  supabase db push --file backend/migrations/001_initial_schema.sql")
    print("  supabase db push --file backend/migrations/002_rls_policies.sql")
    print()

    print("Migration files:")
    for m in migrations:
        content = read_migration(m)
        lines = content.strip().split('\n')
        print(f"  {m.name} ({len(lines)} lines)")
    print()


def main():
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be executed")
    parser.add_argument("--migration", help="Run specific migration by number (e.g., 001)")
    args = parser.parse_args()

    # Check if Supabase is configured
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        sys.exit(1)

    migrations = get_migration_files()

    if not migrations:
        print("No migration files found in backend/migrations/")
        sys.exit(1)

    if args.migration:
        # Filter to specific migration
        migrations = [m for m in migrations if args.migration in m.name]
        if not migrations:
            print(f"No migration found matching '{args.migration}'")
            sys.exit(1)

    print_migration_instructions()

    if args.dry_run:
        print("DRY RUN - No changes made")
        for m in migrations:
            print(f"\n--- {m.name} ---")
            print(read_migration(m)[:1000])
        return

    print("\nAutomated migration via Python client is not fully supported.")
    print("Please use one of the manual methods above.")
    print("After running migrations, test with: python -m pytest backend/tests/test_db.py -v")


if __name__ == "__main__":
    main()