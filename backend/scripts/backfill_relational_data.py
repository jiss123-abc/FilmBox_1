"""
FILMBOX — Relational Data Backfill Script

Finds all movies in the database that are missing relational data (credits, genres, keywords)
and fetches the required information from TMDb to populate the new tables.
"""

import sqlite3
import os
import sys
import time

# Add project root to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from backend.services.tmdb_service import (
    fetch_movie_details,
    fetch_movie_credits,
    fetch_movie_keywords,
    fetch_movie_certification,
)

from backend.scripts.ingest_tmdb import (
    get_or_create_genre,
    get_or_create_keyword,
    get_or_create_person,
    get_or_create_country,
    get_language_id,
    get_certification_id,
)

DB_PATH = os.getenv("DB_PATH", "backend/filmbox.db")


def backfill():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # Find movies with a tmdb_id that have NO entries in movie_credits
    cursor.execute("""
        SELECT id, tmdb_id, title
        FROM movies
        WHERE tmdb_id IS NOT NULL
          AND id NOT IN (SELECT DISTINCT movie_id FROM movie_credits)
    """)
    movies_to_backfill = cursor.fetchall()

    total = len(movies_to_backfill)
    if total == 0:
        print("✅ All movies with a TMDb ID already have relational data.")
        conn.close()
        return

    print(f"🎬 FILMBOX Relational Backfill Pipeline")
    print(f"   Found {total} movies needing relational data.")
    print("=" * 60)

    processed = 0

    for movie_id, tmdb_id, title in movies_to_backfill:
        print(f"🔄 Processing [{processed+1}/{total}]: {title}")

        # ── Step 1: Fetch details ──
        details = fetch_movie_details(tmdb_id)
        if not details:
            print(f"  ⚠ Could not fetch details. Skipping.")
            continue

        # ── Step 2: Fetch credits ──
        credits_data = fetch_movie_credits(tmdb_id)

        # ── Step 3: Fetch keywords ──
        keywords = fetch_movie_keywords(tmdb_id)

        # ── Step 4: Fetch certification ──
        certification = fetch_movie_certification(tmdb_id)

        # ── Step 5: Update movie with language and certification ──
        language_id = get_language_id(cursor, details.get("original_language"))
        certification_id = get_certification_id(cursor, certification)

        cursor.execute("""
            UPDATE movies
            SET language_id = ?, certification_id = ?
            WHERE id = ?
        """, (language_id, certification_id, movie_id))

        # ── Step 6: Insert genres ──
        for genre_name in details.get("genres", []):
            genre_id = get_or_create_genre(cursor, genre_name)
            cursor.execute(
                "INSERT OR IGNORE INTO movie_genres (movie_id, genre_id) VALUES (?, ?)",
                (movie_id, genre_id)
            )

        # ── Step 7: Insert keywords ──
        for kw_name in keywords:
            keyword_id = get_or_create_keyword(cursor, kw_name)
            cursor.execute(
                "INSERT OR IGNORE INTO movie_keywords (movie_id, keyword_id) VALUES (?, ?)",
                (movie_id, keyword_id)
            )

        # ── Step 8: Insert credits (cast + directors) ──
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

            for director in credits_data.get("directors", []):
                person_id = get_or_create_person(
                    cursor, director["tmdb_id"], director["name"], director.get("profile_path")
                )
                cursor.execute("""
                    INSERT OR IGNORE INTO movie_credits
                        (movie_id, person_id, role, character_name, cast_order)
                    VALUES (?, ?, 'director', NULL, NULL)
                """, (movie_id, person_id))

        # ── Step 9: Insert production countries ──
        for country in details.get("production_countries", []):
            if country.get("iso_code"):
                country_id = get_or_create_country(
                    cursor, country["name"], country["iso_code"]
                )
                cursor.execute(
                    "INSERT OR IGNORE INTO movie_countries (movie_id, country_id) VALUES (?, ?)",
                    (movie_id, country_id)
                )

        print(f"  ✅ Synced: {title}")

        # Commit every 10 movies to save progress
        processed += 1
        if processed % 10 == 0:
            conn.commit()

        # Respect rate limits
        time.sleep(0.3)

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print(f"🎬 Backfill Complete! Processed {processed} movies.")


if __name__ == "__main__":
    backfill()
