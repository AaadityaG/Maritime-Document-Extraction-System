"""
Database migration to add raw_ocr_text column to extractions table.

Run this once to update your existing database:
python migrate_add_ocr_column.py
"""

import sqlite3
from pathlib import Path

DATABASE_PATH = "smde.db"


def add_ocr_column():
    """Add raw_ocr_text column to extractions table"""
    
    db_path = Path(DATABASE_PATH)
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(extractions)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "raw_ocr_text" in columns:
            print("✅ Column 'raw_ocr_text' already exists")
            return True
        
        # Add the column
        print("📝 Adding 'raw_ocr_text' column to extractions table...")
        cursor.execute("""
            ALTER TABLE extractions 
            ADD COLUMN raw_ocr_text TEXT
        """)
        
        conn.commit()
        print("✅ Successfully added 'raw_ocr_text' column!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    print("🚀 Running database migration: Add OCR text column")
    success = add_ocr_column()
    
    if success:
        print("\n✅ Migration completed successfully!")
    else:
        print("\n❌ Migration failed!")
        exit(1)
