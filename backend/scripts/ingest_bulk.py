"""
FILMBOX — Parallel Bulk Ingestion Script (Phase 9)

Reads locally cached `movie_ids.json` (up to 300k movies).
Uses ThreadPoolExecutor for concurrent network requests (TMDb).
Uses a strict RateLimiter to prevent 429 errors.
Main thread handles all SQLite inserts for thread safety and speed.
Batch commits every 100 movies.

NOTE: This script DOES NOT do emotional tagging. 
Run `generate_emotional_tags.py` after completion.
"""

import os
import sys
import json
import sqlite3
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# Add project root to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from backend.services.tmdb_service import (
    fetch_movie_everything
)

from backend.scripts.ingest_tmdb import (
    get_or_create_genre,
    get_or_create_keyword,
    get_or_create_person,
    get_or_create_country,
    get_language_id,
    get_certification_id,
)

# Configuration based on user specs
THREADS = 16
API_RATE_LIMIT = 35  # max 40 req/sec allowed by TMDb
BATCH_SIZE = 100
DB_PATH = os.getenv("DB_PATH", "backend/filmbox.db")
IDS_FILE = os.path.join(os.path.dirname(__file__), "..", "movie_ids.json")


# ─── Global Rate Limiter ───

class RateLimiter:
    def __init__(self, calls_per_second):
        self.interval = 1.0 / calls_per_second
        self.last_call = 0.0
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            now = time.perf_counter()
            elapsed = now - self.last_call
            if elapsed < self.interval:
                time.sleep(self.interval - elapsed)
            self.last_call = time.perf_counter()


rate_limiter = RateLimiter(API_RATE_LIMIT)


# ─── Worker Thread Function ───

def fetch_worker(tmdb_id: int):
    """
    Multithreaded network worker. 
    Fetches details, credits, keywords, and certification from TMDb via a single API call!
    Returns a unified dict to the main thread.
    """
    rate_limiter.wait()
    return fetch_movie_everything(tmdb_id)


# ─── SQLite Main Thread Writer ───

def process_and_insert(conn, cursor, data: dict) -> bool:
    tmdb_id = data["tmdb_id"]
    details = data["details"]
    
    # Double check for title/year conflict
    cursor.execute("SELECT id FROM movies WHERE title = ? AND release_year = ?", (details["title"], details["release_year"]))
    if cursor.fetchone():
        return False

    language_id = get_language_id(cursor, details.get("original_language"))
    certification_id = get_certification_id(cursor, data["certification"])

    cursor.execute("""
        INSERT INTO movies (
            tmdb_id, title, overview, release_year, runtime,
            popularity, vote_average, vote_count,
            poster_path, backdrop_path,
            language_id, certification_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        details["tmdb_id"], details["title"], details["overview"],
        details["release_year"], details["runtime"], details["popularity"],
        details["vote_average"], details["vote_count"],
        details["poster_path"], details["backdrop_path"],
        language_id, certification_id,
    ))
    movie_id = cursor.lastrowid

    for genre_name in details.get("genres", []):
        genre_id = get_or_create_genre(cursor, genre_name)
        cursor.execute(
            "INSERT OR IGNORE INTO movie_genres (movie_id, genre_id) VALUES (?, ?)",
            (movie_id, genre_id)
        )

    for kw_name in data["keywords"]:
        keyword_id = get_or_create_keyword(cursor, kw_name)
        cursor.execute(
            "INSERT OR IGNORE INTO movie_keywords (movie_id, keyword_id) VALUES (?, ?)",
            (movie_id, keyword_id)
        )

    if data["credits"]:
        for actor in data["credits"].get("cast", []):
            person_id = get_or_create_person(
                cursor, actor["tmdb_id"], actor["name"], actor.get("profile_path")
            )
            cursor.execute("""
                INSERT OR IGNORE INTO movie_credits
                    (movie_id, person_id, role, character_name, cast_order)
                VALUES (?, ?, 'actor', ?, ?)
            """, (movie_id, person_id, actor.get("character", ""), actor.get("order", 99)))

        for director in data["credits"].get("directors", []):
            person_id = get_or_create_person(
                cursor, director["tmdb_id"], director["name"], director.get("profile_path")
            )
            cursor.execute("""
                INSERT OR IGNORE INTO movie_credits
                    (movie_id, person_id, role, character_name, cast_order)
                VALUES (?, ?, 'director', NULL, NULL)
            """, (movie_id, person_id))

    for country in details.get("production_countries", []):
        if country.get("iso_code"):
            country_id = get_or_create_country(cursor, country["name"], country["iso_code"])
            cursor.execute(
                "INSERT OR IGNORE INTO movie_countries (movie_id, country_id) VALUES (?, ?)",
                (movie_id, country_id)
            )
            
    return True


def bulk_ingest():
    if not os.path.exists(IDS_FILE):
        print(f"❌ Could not find {IDS_FILE}. Run download_bulk_ids.py first.")
        return

    with open(IDS_FILE, "r", encoding="utf-8") as f:
        movie_targets = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # Load existing TMDb IDs into a fast hash set to bypass network and DB entirely for duplicates
    print("⏳ Loading existing movies from database...")
    cursor.execute("SELECT tmdb_id FROM movies WHERE tmdb_id IS NOT NULL")
    existing_ids = {row[0] for row in cursor.fetchall()}
    
    pending_ids = [m["id"] for m in movie_targets if m["id"] not in existing_ids]

    print(f"🎬 FILMBOX Bulk Parallel Ingestion Pipeline")
    print(f"   Target:    {len(movie_targets)} total movies")
    print(f"   Existing:  {len(existing_ids)} skipped")
    print(f"   Pending:   {len(pending_ids)} movies to process")
    print(f"   Config:    {THREADS} threads | {API_RATE_LIMIT} req/s | DB Batch {BATCH_SIZE}")
    print("=" * 60)

    if not pending_ids:
        print("✅ Database is fully up to date with target list.")
        conn.close()
        return

    start_time = time.time()
    processed = 0
    successfully_inserted = 0

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        for result in executor.map(fetch_worker, pending_ids):
            processed += 1
            
            if result is not None:
                inserted = process_and_insert(conn, cursor, result)
                if inserted:
                    successfully_inserted += 1
                    title = result["details"]["title"]
                    year = result["details"]["release_year"]
                    print(f"  [+] {title} ({year})")
                else:
                    title = result["details"]["title"]
                    print(f"  [-] Skipped existing: {title}")
            else:
                print(f"  [!] Failed to fetch an ID")

            # Batch commit
            if successfully_inserted > 0 and successfully_inserted % BATCH_SIZE == 0:
                conn.commit()
                elapsed = time.time() - start_time
                rate = processed / elapsed
                print(f"  💾 Batch Committed! Processed {processed}/{len(pending_ids)} ({rate:.1f} movies/sec)")

    conn.commit()
    conn.close()
    
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"🎬 Ingestion Run Complete!")
    print(f"   Inserted:  {successfully_inserted} new movies")
    print(f"   Time:      {total_time:.1f}s ({(processed / total_time):.1f} movies/sec)")
    print(f"   Next step: Run generate_emotional_tags.py to index vectors.")


if __name__ == "__main__":
    bulk_ingest()
