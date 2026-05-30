#!/usr/bin/env python3
"""
Migration script to add device_1_uid and device_2_uid columns to users table
Run this with: python migrate_add_device_uids.py
"""

import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from sqlalchemy import create_engine, text
    from app.config import get_settings

    settings = get_settings()

    def migrate():
        print("=" * 80)
        print("🔄 DATABASE MIGRATION: Adding device UID columns")
        print("=" * 80)

        engine = create_engine(settings.DATABASE_URL)

        with engine.connect() as conn:
            print("\n📊 Checking existing columns...")

            # Check if columns already exist
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='users' AND column_name IN ('device_1_uid', 'device_2_uid')
            """))
            existing_columns = [row[0] for row in result]

            if 'device_1_uid' in existing_columns and 'device_2_uid' in existing_columns:
                print("✅ Columns already exist. Migration not needed.")
                print("\nColumns found:")
                print("  - device_1_uid ✓")
                print("  - device_2_uid ✓")
                return

            # Add device_1_uid column if not exists
            if 'device_1_uid' not in existing_columns:
                print("\n📝 Adding device_1_uid column...")
                conn.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN device_1_uid INTEGER
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_users_device_1_uid ON users(device_1_uid)
                """))
                conn.commit()
                print("✅ Added device_1_uid column with index")

            # Add device_2_uid column if not exists
            if 'device_2_uid' not in existing_columns:
                print("\n📝 Adding device_2_uid column...")
                conn.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN device_2_uid INTEGER
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_users_device_2_uid ON users(device_2_uid)
                """))
                conn.commit()
                print("✅ Added device_2_uid column with index")

            # Populate device_1_uid from uid for existing users
            print("\n📝 Populating device_1_uid from existing uid column...")
            result = conn.execute(text("""
                UPDATE users
                SET device_1_uid = uid
                WHERE device_1_uid IS NULL
            """))
            conn.commit()
            print(f"✅ Populated device_1_uid for {result.rowcount} users")

            # Make name unique if not already
            print("\n📝 Adding unique constraint on name column...")
            try:
                conn.execute(text("""
                    ALTER TABLE users
                    ADD CONSTRAINT users_name_unique UNIQUE (name)
                """))
                conn.commit()
                print("✅ Added unique constraint on name column")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print("✅ Unique constraint on name already exists")
                else:
                    print(f"⚠️  Warning: Could not add unique constraint on name: {e}")

            # Show summary
            print("\n" + "=" * 80)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 80)

            # Show current data stats
            result = conn.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(device_1_uid) as dev1,
                    COUNT(device_2_uid) as dev2
                FROM users
            """))
            row = result.fetchone()
            print(f"\n📊 Current Users Data:")
            print(f"  Total users: {row[0]}")
            print(f"  With device_1_uid: {row[1]}")
            print(f"  With device_2_uid: {row[2]}")

            print("\n" + "=" * 80)
            print("NEXT STEPS:")
            print("1. Restart your backend server (stop and start run.py)")
            print("2. Run a device sync to populate device_2_uid")
            print("3. Check the frontend attendance page")
            print("=" * 80 + "\n")

    if __name__ == "__main__":
        try:
            migrate()
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

except ImportError as e:
    print("\n" + "=" * 80)
    print("❌ ERROR: Required modules not found")
    print("=" * 80)
    print(f"\nError: {e}")
    print("\n📝 ALTERNATIVE: Use SQL script directly")
    print("=" * 80)
    print("\nYou can run the migration manually using the SQL file:")
    print("\n1. Open pgAdmin or psql")
    print("2. Connect to your database")
    print("3. Run the SQL file: migrate_device_uids.sql")
    print("\nOR")
    print("\nRun this in psql:")
    print(f"  psql -U your_username -d your_database -f migrate_device_uids.sql")
    print("\n" + "=" * 80)
    sys.exit(1)
