# backend/scripts/optimize_db.py

import sqlite3
import os

DB_PATH = "backend/filmbox.db"

def optimize_db():
    print(f"🚀 Hardening Database: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print("❌ Error: Database file not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Indexing for scoring performance
    print("- Adding indexes for performance...")
    try:
        # User spec indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_archetype ON emotional_archetype_tags(archetype);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_movie_id ON emotional_archetype_tags(movie_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_release_year ON movies(release_year);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vote_count ON movies(vote_count);")
        
        # 2. Vacuum for cleanup
        print("- Vacuuming database...")
        cursor.execute("VACUUM;")
        
        conn.commit()
        print("✅ Database optimization complete.")
    except Exception as e:
        print(f"❌ Error during optimization: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    optimize_db()
