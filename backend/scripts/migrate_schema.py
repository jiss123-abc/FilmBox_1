"""
FILMBOX — Database Migration Script

Migrates the existing filmbox.db to the new relational schema.
Adds new tables and columns without data loss.

Usage:
    python -m backend.scripts.migrate_schema
"""

import sqlite3
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

DB_PATH = os.getenv("DB_PATH", "backend/filmbox.db")


def migrate():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    print("🔧 FILMBOX Schema Migration")
    print("=" * 50)

    # ─── 1. Create new lookup tables ───

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS languages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            iso_code TEXT UNIQUE NOT NULL
        )
    """)
    print("  ✅ Table: languages")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS certifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rating TEXT UNIQUE NOT NULL,
            description TEXT
        )
    """)
    print("  ✅ Table: certifications")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tmdb_id INTEGER UNIQUE,
            name TEXT NOT NULL,
            profile_path TEXT
        )
    """)
    print("  ✅ Table: people")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movie_credits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER NOT NULL,
            person_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('actor', 'director')),
            character_name TEXT,
            cast_order INTEGER,
            FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
            FOREIGN KEY (person_id) REFERENCES people(id)
        )
    """)
    print("  ✅ Table: movie_credits")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS countries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            iso_code TEXT UNIQUE NOT NULL,
            continent TEXT
        )
    """)
    print("  ✅ Table: countries")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movie_countries (
            movie_id INTEGER NOT NULL,
            country_id INTEGER NOT NULL,
            PRIMARY KEY (movie_id, country_id),
            FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
            FOREIGN KEY (country_id) REFERENCES countries(id)
        )
    """)
    print("  ✅ Table: movie_countries")

    # ─── 2. Ensure genres/keywords/movie_genres/movie_keywords exist ───

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS genres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movie_genres (
            movie_id INTEGER NOT NULL,
            genre_id INTEGER NOT NULL,
            PRIMARY KEY (movie_id, genre_id),
            FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
            FOREIGN KEY (genre_id) REFERENCES genres(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movie_keywords (
            movie_id INTEGER NOT NULL,
            keyword_id INTEGER NOT NULL,
            PRIMARY KEY (movie_id, keyword_id),
            FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
            FOREIGN KEY (keyword_id) REFERENCES keywords(id)
        )
    """)

    # ─── 3. Add new columns to movies (safe — ignores if already exists) ───

    new_cols = [
        ("language_id", "INTEGER"),
        ("certification_id", "INTEGER"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ]

    for col, col_type in new_cols:
        try:
            cursor.execute(f"ALTER TABLE movies ADD COLUMN {col} {col_type}")
            print(f"  ✅ Column: movies.{col}")
        except sqlite3.OperationalError:
            print(f"  ⏭  Column already exists: movies.{col}")

    # Ensure tmdb_id column exists and has UNIQUE constraint
    try:
        cursor.execute("ALTER TABLE movies ADD COLUMN tmdb_id INTEGER")
        print("  ✅ Column: movies.tmdb_id")
    except sqlite3.OperationalError:
        pass

    # Create unique index on tmdb_id if it doesn't exist
    try:
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_movies_tmdb_unique ON movies(tmdb_id)")
        print("  ✅ Index: idx_movies_tmdb_unique")
    except sqlite3.OperationalError as e:
        print(f"  ⏭  tmdb_id unique index: {e}")

    # ─── 4. Create performance indexes ───

    indexes = [
        ("idx_movies_popularity", "movies(popularity)"),
        ("idx_movies_vote", "movies(vote_average)"),
        ("idx_movies_language", "movies(language_id)"),
        ("idx_movies_certification", "movies(certification_id)"),
        ("idx_archetype_movie", "emotional_archetype_tags(movie_id)"),
        ("idx_archetype_name", "emotional_archetype_tags(archetype)"),
        ("idx_credits_movie", "movie_credits(movie_id)"),
        ("idx_credits_person", "movie_credits(person_id)"),
        ("idx_credits_role", "movie_credits(role)"),
        ("idx_people_tmdb", "people(tmdb_id)"),
        ("idx_session", "user_interactions(session_id)"),
        ("idx_interaction_date", "user_interactions(created_at)"),
    ]

    for idx_name, idx_target in indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_target}")
        except sqlite3.OperationalError:
            pass

    print("  ✅ Performance indexes created")

    # ─── 5. Pre-seed certifications (MPAA ratings) ───

    mpaa_ratings = [
        ("G", "General Audiences — All ages admitted"),
        ("PG", "Parental Guidance Suggested"),
        ("PG-13", "Parents Strongly Cautioned — Some material may be inappropriate for children under 13"),
        ("R", "Restricted — Under 17 requires accompanying parent or adult guardian"),
        ("NC-17", "Adults Only — No one 17 and under admitted"),
        ("NR", "Not Rated"),
    ]

    for rating, desc in mpaa_ratings:
        cursor.execute(
            "INSERT OR IGNORE INTO certifications (rating, description) VALUES (?, ?)",
            (rating, desc)
        )

    print("  ✅ Pre-seeded MPAA certifications")

    # ─── 6. Pre-seed common languages ───

    common_languages = [
        ("English", "en"),
        ("Spanish", "es"),
        ("French", "fr"),
        ("German", "de"),
        ("Italian", "it"),
        ("Portuguese", "pt"),
        ("Japanese", "ja"),
        ("Korean", "ko"),
        ("Chinese", "zh"),
        ("Hindi", "hi"),
        ("Arabic", "ar"),
        ("Russian", "ru"),
        ("Turkish", "tr"),
        ("Thai", "th"),
        ("Swedish", "sv"),
        ("Danish", "da"),
        ("Norwegian", "no"),
        ("Dutch", "nl"),
        ("Polish", "pl"),
        ("Czech", "cs"),
    ]

    for name, iso in common_languages:
        cursor.execute(
            "INSERT OR IGNORE INTO languages (name, iso_code) VALUES (?, ?)",
            (name, iso)
        )

    print("  ✅ Pre-seeded common languages")

    conn.commit()

    # ─── Summary ───

    print("\n" + "=" * 50)
    print("📊 Migration Summary:")
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    print(f"   Tables: {len(tables)}")
    for t in tables:
        count = cursor.execute(f"SELECT COUNT(*) FROM [{t[0]}]").fetchone()[0]
        print(f"     {t[0]:30s} → {count:,} rows")

    conn.close()
    print("\n✅ Migration complete!")


if __name__ == "__main__":
    migrate()
