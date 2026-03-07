"""
FILMBOX — TMDb Bulk Ingestion Script (Phase 2)

Full pipeline:
    discover movies → fetch details → fetch credits →
    fetch keywords → store in database → generate emotional vector

Usage:
    python -m backend.scripts.ingest_tmdb --start 1 --end 500

Each page = 20 movies. 500 pages ≈ 10,000 movies.
"""

import argparse
import sqlite3
import os
import sys
import time

# Add project root to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Load .env file from project root
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from backend.services.tmdb_service import (
    fetch_discover_page,
    fetch_movie_details,
    fetch_movie_credits,
    fetch_movie_keywords,
    fetch_movie_certification,
)
from backend.archetype_tagger import tag_movie, ARCHETYPES

DB_PATH = os.getenv("DB_PATH", "backend/filmbox.db")


# ─── Database Helper Functions ───

def get_or_create_genre(cursor, genre_name: str) -> int:
    """Get genre ID by name, or create it. Returns genre ID."""
    cursor.execute("SELECT id FROM genres WHERE name = ?", (genre_name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("INSERT INTO genres (name) VALUES (?)", (genre_name,))
    return cursor.lastrowid


def get_or_create_keyword(cursor, keyword_name: str) -> int:
    """Get keyword ID by name, or create it. Returns keyword ID."""
    cursor.execute("SELECT id FROM keywords WHERE name = ?", (keyword_name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("INSERT INTO keywords (name) VALUES (?)", (keyword_name,))
    return cursor.lastrowid


def get_or_create_person(cursor, tmdb_id: int, name: str, profile_path: str = None) -> int:
    """Get person ID by TMDb ID, or create it. Returns person ID."""
    cursor.execute("SELECT id FROM people WHERE tmdb_id = ?", (tmdb_id,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        "INSERT INTO people (tmdb_id, name, profile_path) VALUES (?, ?, ?)",
        (tmdb_id, name, profile_path)
    )
    return cursor.lastrowid


def get_or_create_country(cursor, name: str, iso_code: str) -> int:
    """Get country ID by ISO code, or create it. Returns country ID."""
    cursor.execute("SELECT id FROM countries WHERE iso_code = ?", (iso_code,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        "INSERT INTO countries (name, iso_code) VALUES (?, ?)",
        (name, iso_code)
    )
    return cursor.lastrowid


def get_language_id(cursor, iso_code: str) -> int:
    """Get language ID by ISO code. Returns ID or None."""
    if not iso_code:
        return None
    cursor.execute("SELECT id FROM languages WHERE iso_code = ?", (iso_code,))
    row = cursor.fetchone()
    if row:
        return row[0]
    # Insert if not pre-seeded
    cursor.execute(
        "INSERT OR IGNORE INTO languages (name, iso_code) VALUES (?, ?)",
        (iso_code, iso_code)
    )
    cursor.execute("SELECT id FROM languages WHERE iso_code = ?", (iso_code,))
    row = cursor.fetchone()
    return row[0] if row else None


def get_certification_id(cursor, rating: str) -> int:
    """Get certification ID by rating string. Returns ID or None."""
    if not rating:
        return None
    cursor.execute("SELECT id FROM certifications WHERE rating = ?", (rating,))
    row = cursor.fetchone()
    if row:
        return row[0]
    # Insert unknown rating
    cursor.execute(
        "INSERT OR IGNORE INTO certifications (rating) VALUES (?)",
        (rating,)
    )
    cursor.execute("SELECT id FROM certifications WHERE rating = ?", (rating,))
    row = cursor.fetchone()
    return row[0] if row else None


# ─── Main Ingestion Pipeline ───

def ingest(start_page: int = 1, end_page: int = 5):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    total_imported = 0
    total_skipped = 0
    total_tagged = 0
    total_credits = 0

    total_pages = end_page - start_page + 1
    print(f"🎬 FILMBOX TMDb Ingestion Pipeline")
    print(f"   Pages {start_page} → {end_page} ({total_pages * 20} movies max)")
    print("=" * 60)

    for page in range(start_page, end_page + 1):
        print(f"\n📄 Page {page}/{end_page}")

        results = fetch_discover_page(page=page)
        if not results:
            print(f"  ⚠ No results for page {page}. Stopping.")
            break

        for movie in results:
            tmdb_id = movie.get("id")
            title = movie.get("title", "Unknown")

            # ── Skip if already imported ──
            cursor.execute("SELECT id FROM movies WHERE tmdb_id = ?", (tmdb_id,))
            if cursor.fetchone():
                total_skipped += 1
                continue

            # ── Step 1: Fetch full details ──
            details = fetch_movie_details(tmdb_id)
            if not details:
                print(f"  ⚠ Could not fetch details for: {title}")
                continue

            # ── Check if already imported by title/year (to prevent IntegrityError) ──
            cursor.execute("SELECT id FROM movies WHERE title = ? AND release_year = ?", (details["title"], details["release_year"]))
            if cursor.fetchone():
                total_skipped += 1
                continue

            # ── Step 2: Fetch credits ──
            credits_data = fetch_movie_credits(tmdb_id)

            # ── Step 3: Fetch keywords ──
            keywords = fetch_movie_keywords(tmdb_id)

            # ── Step 4: Fetch certification ──
            certification = fetch_movie_certification(tmdb_id)

            # ── Step 5: Resolve foreign keys ──
            language_id = get_language_id(cursor, details.get("original_language"))
            certification_id = get_certification_id(cursor, certification)

            # ── Step 6: Insert movie ──
            cursor.execute("""
                INSERT INTO movies (
                    tmdb_id, title, overview, release_year, runtime,
                    popularity, vote_average, vote_count,
                    poster_path, backdrop_path,
                    language_id, certification_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                details["tmdb_id"],
                details["title"],
                details["overview"],
                details["release_year"],
                details["runtime"],
                details["popularity"],
                details["vote_average"],
                details["vote_count"],
                details["poster_path"],
                details["backdrop_path"],
                language_id,
                certification_id,
            ))
            movie_id = cursor.lastrowid
            total_imported += 1

            # ── Step 7: Insert genres ──
            for genre_name in details.get("genres", []):
                genre_id = get_or_create_genre(cursor, genre_name)
                cursor.execute(
                    "INSERT OR IGNORE INTO movie_genres (movie_id, genre_id) VALUES (?, ?)",
                    (movie_id, genre_id)
                )

            # ── Step 8: Insert keywords ──
            for kw_name in keywords:
                keyword_id = get_or_create_keyword(cursor, kw_name)
                cursor.execute(
                    "INSERT OR IGNORE INTO movie_keywords (movie_id, keyword_id) VALUES (?, ?)",
                    (movie_id, keyword_id)
                )

            # ── Step 9: Insert credits (cast + directors) ──
            if credits_data:
                for actor in credits_data.get("cast", []):
                    person_id = get_or_create_person(
                        cursor, actor["tmdb_id"], actor["name"], actor.get("profile_path")
                    )
                    cursor.execute("""
                        INSERT OR IGNORE INTO movie_credits
                            (movie_id, person_id, role, character_name, cast_order)
                        VALUES (?, ?, 'actor', ?, ?)
                    """, (movie_id, person_id, actor.get("character", ""), actor.get("order", 99)))
                    total_credits += 1

                for director in credits_data.get("directors", []):
                    person_id = get_or_create_person(
                        cursor, director["tmdb_id"], director["name"], director.get("profile_path")
                    )
                    cursor.execute("""
                        INSERT OR IGNORE INTO movie_credits
                            (movie_id, person_id, role, character_name, cast_order)
                        VALUES (?, ?, 'director', NULL, NULL)
                    """, (movie_id, person_id))
                    total_credits += 1

            # ── Step 10: Insert production countries ──
            for country in details.get("production_countries", []):
                if country.get("iso_code"):
                    country_id = get_or_create_country(
                        cursor, country["name"], country["iso_code"]
                    )
                    cursor.execute(
                        "INSERT OR IGNORE INTO movie_countries (movie_id, country_id) VALUES (?, ?)",
                        (movie_id, country_id)
                    )

            # ── Step 11: Generate emotional archetype vector ──
            vector = tag_movie(
                title=details["title"],
                overview=details["overview"],
                genres=details.get("genres", []),
                keywords=keywords,
                popularity=details["popularity"],
                runtime=details["runtime"] or 0
            )

            for archetype in ARCHETYPES:
                weight = vector.get(archetype, 0.0)
                if weight > 0.05:  # Only store meaningful weights
                    cursor.execute("""
                        INSERT OR REPLACE INTO emotional_archetype_tags
                            (movie_id, archetype, weight)
                        VALUES (?, ?, ?)
                    """, (movie_id, archetype, round(weight, 4)))
                    total_tagged += 1

            print(f"  ✅ {details['title']} ({details['release_year'] or '?'})")

            # Brief delay to respect TMDb rate limits (<4 req/sec)
            time.sleep(0.3)

        conn.commit()
        print(f"  📊 Page {page} committed.")

        # Brief delay between pages
        time.sleep(0.5)

    conn.close()

    print("\n" + "=" * 60)
    print(f"🎬 Ingestion Complete!")
    print(f"   Imported:  {total_imported} movies")
    print(f"   Skipped:   {total_skipped} (already in DB)")
    print(f"   Credits:   {total_credits} people linked")
    print(f"   Tags:      {total_tagged} archetype tags created")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FILMBOX TMDb Bulk Ingestion Pipeline")
    parser.add_argument("--start", type=int, default=1, help="Page to start from (default: 1)")
    parser.add_argument("--end", type=int, default=5, help="Page to end at (default: 5)")
    args = parser.parse_args()

    ingest(start_page=args.start, end_page=args.end)
