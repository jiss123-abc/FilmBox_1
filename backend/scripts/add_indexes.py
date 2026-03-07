"""
FILMBOX — Database Index Optimizer (Phase 9)

Adds missing performance indexes to the existing database
to support the 300k scale.
"""

import sqlite3
import os

from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

DB_PATH = os.getenv("DB_PATH", "backend/filmbox.db")


def add_indexes():
    print(f"Adding performance indexes to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    queries = [
        "CREATE INDEX IF NOT EXISTS idx_movies_year ON movies(release_year);",
        "CREATE INDEX IF NOT EXISTS idx_movie_genres_id ON movie_genres(genre_id);",
        "CREATE INDEX IF NOT EXISTS idx_movie_keywords_id ON movie_keywords(keyword_id);"
    ]

    for q in queries:
        try:
            cursor.execute(q)
            print(f"✅ Executed: {q}")
        except Exception as e:
            print(f"❌ Error executing {q}: {e}")

    conn.commit()
    conn.close()
    print("Optimization complete.")


if __name__ == "__main__":
    add_indexes()
