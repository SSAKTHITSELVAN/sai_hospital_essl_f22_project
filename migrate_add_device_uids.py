#!/usr/bin/env python3
"""
Migration script to add device_1_uid and device_2_uid columns to users table
"""

from sqlalchemy import create_engine, text
from app.config import get_settings

settings = get_settings()

def migrate():
    engine = create_engine(settings.DATABASE_URL)

    with engine.connect() as conn:
        print("🔄 Starting migration: Adding device_1_uid and device_2_uid columns...")

        # Check if columns already exist
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='users' AND column_name IN ('device_1_uid', 'device_2_uid')
        """))
        existing_columns = [row[0] for row in result]

        if 'device_1_uid' in existing_columns and 'device_2_uid' in existing_columns:
            print("✅ Columns already exist. Migration not needed.")
            return

        # Add device_1_uid column if not exists
        if 'device_1_uid' not in existing_columns:
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN device_1_uid INTEGER
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_users_device_1_uid ON users(device_1_uid)
            """))
            print("✅ Added device_1_uid column")

        # Add device_2_uid column if not exists
        if 'device_2_uid' not in existing_columns:
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN device_2_uid INTEGER
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_users_device_2_uid ON users(device_2_uid)
            """))
            print("✅ Added device_2_uid column")

        # Populate device_1_uid from uid for existing users
        conn.execute(text("""
            UPDATE users
            SET device_1_uid = uid
            WHERE device_1_uid IS NULL
        """))
        print("✅ Populated device_1_uid from existing uid column")

        # Make name unique if not already
        try:
            conn.execute(text("""
                ALTER TABLE users
                ADD CONSTRAINT users_name_unique UNIQUE (name)
            """))
            print("✅ Added unique constraint on name column")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("✅ Unique constraint on name already exists")
            else:
                print(f"⚠️  Warning: Could not add unique constraint on name: {e}")

        conn.commit()
        print("\n✅ Migration completed successfully!")
        print("=" * 80)
        print("NEXT STEPS:")
        print("1. Restart your application")
        print("2. Run a device sync to populate device UIDs")
        print("=" * 80)

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
