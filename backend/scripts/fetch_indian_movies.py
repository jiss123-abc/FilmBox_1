"""
FILMBOX — Fetch Indian Movies from TMDb

Fetches up to 1000 Indian movies using TMDb's /discover/movie API
with region=IN filter. Skips movies already in the database.
Inserts full details, credits, keywords, genres, countries,
and emotional archetype tags.

Usage:
    cd d:\Filmbox
    d:\Filmbox\.venv\Scripts\python.exe backend\scripts\fetch_indian_movies.py
"""

import os
import sys
import time
import sqlite3
import requests

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from backend.services.tmdb_service import _tmdb_get, fetch_movie_everything
from backend.archetype_tagger import tag_movie

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "filmbox.db")
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TARGET_COUNT = 1000


def fetch_indian_discover_page(page: int, language: str = None) -> list:
    """Fetch a page of Indian movies from TMDb discover API."""
    params = {
        "page": page,
        "sort_by": "popularity.desc",
        "include_adult": "false",
        "with_origin_country": "IN",  # India filter
    }
    if language:
        params["with_original_language"] = language

    data = _tmdb_get("/discover/movie", params)
    if not data:
        return []
    return data.get("results", [])


def get_existing_tmdb_ids(conn):
    """Get all TMDb IDs currently in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT tmdb_id FROM movies WHERE tmdb_id IS NOT NULL")
    return {row[0] for row in cursor.fetchall()}


def insert_movie(conn, movie_data):
    """Insert a fully-fetched movie into the database with all relational data."""
    cursor = conn.cursor()
    details = movie_data["details"]
    credits = movie_data["credits"]
    keywords = movie_data["keywords"]
    certification = movie_data["certification"]
    tmdb_id = movie_data["tmdb_id"]

    # 1. Ensure language exists
    lang_code = details.get("original_language", "en")
    cursor.execute("SELECT id FROM languages WHERE iso_code = ?", (lang_code,))
    lang_row = cursor.fetchone()
    if lang_row:
        language_id = lang_row[0]
    else:
        cursor.execute("INSERT INTO languages (name, iso_code) VALUES (?, ?)", (lang_code, lang_code))
        language_id = cursor.lastrowid

    # 2. Ensure certification exists
    cert_id = None
    if certification:
        cursor.execute("SELECT id FROM certifications WHERE rating = ?", (certification,))
        cert_row = cursor.fetchone()
        if cert_row:
            cert_id = cert_row[0]
        else:
            cursor.execute("INSERT INTO certifications (rating) VALUES (?)", (certification,))
            cert_id = cursor.lastrowid

    # 3. Insert movie
    cursor.execute("""
        INSERT INTO movies (title, overview, release_year, runtime, popularity,
                            vote_average, vote_count, poster_path, backdrop_path,
                            tmdb_id, language_id, certification_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        details["title"], details["overview"], details["release_year"],
        details["runtime"], details["popularity"], details["vote_average"],
        details["vote_count"], details["poster_path"], details["backdrop_path"],
        tmdb_id, language_id, cert_id
    ))
    movie_id = cursor.lastrowid

    # 4. Insert genres
    for genre_name in details.get("genres", []):
        cursor.execute("SELECT id FROM genres WHERE LOWER(name) = ?", (genre_name.lower(),))
        genre_row = cursor.fetchone()
        if genre_row:
            genre_id = genre_row[0]
        else:
            cursor.execute("INSERT OR IGNORE INTO genres (name) VALUES (?)", (genre_name,))
            genre_id = cursor.lastrowid
        if genre_id:
            cursor.execute("INSERT OR IGNORE INTO movie_genres (movie_id, genre_id) VALUES (?, ?)",
                           (movie_id, genre_id))

    # 5. Insert keywords
    for kw_name in keywords:
        cursor.execute("SELECT id FROM keywords WHERE LOWER(name) = ?", (kw_name.lower(),))
        kw_row = cursor.fetchone()
        if kw_row:
            kw_id = kw_row[0]
        else:
            cursor.execute("INSERT OR IGNORE INTO keywords (name) VALUES (?)", (kw_name,))
            kw_id = cursor.lastrowid
        if kw_id:
            cursor.execute("INSERT OR IGNORE INTO movie_keywords (movie_id, keyword_id) VALUES (?, ?)",
                           (movie_id, kw_id))

    # 6. Insert countries
    for country in details.get("production_countries", []):
        iso = country.get("iso_code", "")
        name = country.get("name", "")
        if iso:
            cursor.execute("SELECT id FROM countries WHERE iso_code = ?", (iso,))
            c_row = cursor.fetchone()
            if c_row:
                country_id = c_row[0]
            else:
                cursor.execute("INSERT OR IGNORE INTO countries (name, iso_code) VALUES (?, ?)", (name, iso))
                country_id = cursor.lastrowid
            if country_id:
                cursor.execute("INSERT OR IGNORE INTO movie_countries (movie_id, country_id) VALUES (?, ?)",
                               (movie_id, country_id))

    # 7. Insert credits (cast + directors)
    for person in credits.get("cast", []):
        cursor.execute("SELECT id FROM people WHERE tmdb_id = ?", (person["tmdb_id"],))
        p_row = cursor.fetchone()
        if p_row:
            person_id = p_row[0]
        else:
            cursor.execute("INSERT INTO people (tmdb_id, name, profile_path) VALUES (?, ?, ?)",
                           (person["tmdb_id"], person["name"], person.get("profile_path")))
            person_id = cursor.lastrowid
        cursor.execute("""
            INSERT OR IGNORE INTO movie_credits (movie_id, person_id, role, character_name, cast_order)
            VALUES (?, ?, 'actor', ?, ?)
        """, (movie_id, person_id, person.get("character", ""), person.get("order", 99)))

    for person in credits.get("directors", []):
        cursor.execute("SELECT id FROM people WHERE tmdb_id = ?", (person["tmdb_id"],))
        p_row = cursor.fetchone()
        if p_row:
            person_id = p_row[0]
        else:
            cursor.execute("INSERT INTO people (tmdb_id, name, profile_path) VALUES (?, ?, ?)",
                           (person["tmdb_id"], person["name"], person.get("profile_path")))
            person_id = cursor.lastrowid
        cursor.execute("""
            INSERT OR IGNORE INTO movie_credits (movie_id, person_id, role)
            VALUES (?, ?, 'director')
        """, (movie_id, person_id))

    # 8. Archetype tagging (rule-based only — no LLM to save tokens)
    vector = tag_movie(
        title=details["title"],
        overview=details["overview"],
        genres=details.get("genres", []),
        keywords=keywords,
        popularity=details["popularity"],
        runtime=details.get("runtime") or 0,
        use_llm_fallback=False  # Rule-based only to avoid burning Groq tokens
    )
    for archetype, weight in vector.items():
        if weight > 0.05:
            cursor.execute("""
                INSERT OR REPLACE INTO emotional_archetype_tags (movie_id, archetype, weight)
                VALUES (?, ?, ?)
            """, (movie_id, archetype, round(weight, 4)))

    return movie_id


def main():
    print(f"=" * 60)
    print(f"FILMBOX — Indian Movies Ingestion")
    print(f"Target: {TARGET_COUNT} new Indian movies")
    print(f"Database: {DB_PATH}")
    print(f"=" * 60)

    if not TMDB_API_KEY:
        print("ERROR: TMDB_API_KEY not found in environment!")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    existing_ids = get_existing_tmdb_ids(conn)
    print(f"Existing movies in DB: {len(existing_ids)}")

    inserted = 0
    skipped = 0
    errors = 0
    page = 1
    max_pages = 100  # TMDb allows up to 500 pages, 20 movies each

    # Cycle through Indian languages for variety
    languages = [None, "hi", "ta", "te", "ml", "kn", "bn", "mr", "pa", "gu"]
    lang_idx = 0

    while inserted < TARGET_COUNT and page <= max_pages:
        current_lang = languages[lang_idx % len(languages)]
        lang_label = current_lang or "all"
        print(f"\n--- Page {page} (lang={lang_label}) ---")

        movies = fetch_indian_discover_page(page, language=current_lang)

        if not movies:
            print(f"  No more movies on page {page} for lang={lang_label}")
            lang_idx += 1
            page = 1
            if lang_idx >= len(languages):
                break
            continue

        for movie in movies:
            if inserted >= TARGET_COUNT:
                break

            tmdb_id = movie.get("id")
            title = movie.get("title", "Unknown")

            if tmdb_id in existing_ids:
                skipped += 1
                continue

            # Fetch full details
            try:
                full_data = fetch_movie_everything(tmdb_id)
                if not full_data:
                    print(f"  SKIP (no details): {title}")
                    errors += 1
                    continue

                movie_id = insert_movie(conn, full_data)
                conn.commit()
                existing_ids.add(tmdb_id)
                inserted += 1
                print(f"  [{inserted}/{TARGET_COUNT}] {title} (id={movie_id})")

            except Exception as e:
                print(f"  ERROR: {title} — {e}")
                errors += 1
                conn.rollback()

            # TMDb rate limit: ~40 requests/sec
            time.sleep(0.15)

        page += 1

        # Switch language every 10 pages for variety
        if page % 10 == 0:
            lang_idx += 1
            page = 1

    conn.close()

    print(f"\n{'=' * 60}")
    print(f"DONE!")
    print(f"  Inserted: {inserted}")
    print(f"  Skipped (already in DB): {skipped}")
    print(f"  Errors: {errors}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
