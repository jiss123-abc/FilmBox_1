import sqlite3
import json
import os
from pathlib import Path

DB_PATH = "backend/filmbox.db"
SEED_FILE = "backend/scripts/real_movies_seed.json"


def seed_database():
    """
    Seed the FilmBox database with curated real movie data.
    
    - Transaction-safe: all-or-nothing with ROLLBACK on error.
    - Creates unique constraint on (title, release_year).
    - Clears existing data before inserting.
    """
    if not os.path.exists(SEED_FILE):
        print(f"❌ Seed file not found: {SEED_FILE}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Step 0: Ensure unique constraint exists
    try:
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_title_year
            ON movies(title, release_year);
        """)
        conn.commit()
        print("🔒 Unique constraint on (title, release_year) ensured.")
    except sqlite3.OperationalError as e:
        print(f"⚠ Could not create unique index: {e}")

    # Load seed data
    with open(SEED_FILE, "r", encoding="utf-8") as f:
        movies = json.load(f)

    print(f"📦 Loaded {len(movies)} movies from seed file.")

    try:
        print("🔄 Starting transaction...")
        conn.execute("BEGIN")

        # Clear existing data (order matters for FK constraints)
        cursor.execute("DELETE FROM emotional_archetype_tags")
        cursor.execute("DELETE FROM movie_keywords")
        cursor.execute("DELETE FROM movie_genres")
        cursor.execute("DELETE FROM keywords")
        cursor.execute("DELETE FROM genres")
        cursor.execute("DELETE FROM movies")
        print("🗑  Cleared all existing data.")

        # Insert movies and archetype tags
        inserted = 0
        tags_inserted = 0

        for movie in movies:
            cursor.execute(
                """INSERT INTO movies (title, release_year)
                   VALUES (?, ?)""",
                (movie["title"], movie["year"])
            )
            movie_id = cursor.lastrowid

            for archetype, weight in movie.get("archetypes", {}).items():
                cursor.execute(
                    """INSERT INTO emotional_archetype_tags
                       (movie_id, archetype, weight)
                       VALUES (?, ?, ?)""",
                    (movie_id, archetype, weight)
                )
                tags_inserted += 1

            inserted += 1

        conn.commit()
        print(f"✅ Successfully seeded {inserted} movies with {tags_inserted} archetype tags.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error occurred. Transaction rolled back.")
        print(f"   Detail: {e}")
        return

    # Post-seeding validation
    print("\n📊 --- Post-Seeding Validation ---")
    cursor.execute("SELECT COUNT(*) FROM movies")
    db_movies = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM emotional_archetype_tags")
    db_tags = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT movie_id) FROM emotional_archetype_tags")
    db_mapped = cursor.fetchone()[0]

    cursor.execute("""
        SELECT archetype, COUNT(*) as cnt, ROUND(AVG(weight), 2) as avg_w
        FROM emotional_archetype_tags
        GROUP BY archetype
        ORDER BY cnt DESC
    """)
    distribution = cursor.fetchall()

    print(f"  Movies inserted: {db_movies}")
    print(f"  Archetype tags:  {db_tags}")
    print(f"  Movies with tags: {db_mapped}")
    print(f"\n  Archetype Distribution:")
    for arch, cnt, avg_w in distribution:
        print(f"    {arch:15s} → {cnt:3d} movies (avg weight: {avg_w})")

    if db_movies != len(movies):
        print(f"\n⚠ WARNING: Expected {len(movies)} movies, got {db_movies}")
    else:
        print(f"\n✅ All {db_movies} movies seeded correctly.")

    conn.close()


if __name__ == "__main__":
    seed_database()
