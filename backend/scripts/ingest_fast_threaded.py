"""
FILMBOX — Fast Threaded Bulk Ingestion Script (Fallback)
Using `requests` and `ThreadPoolExecutor` because `aiohttp` failed to build.

1. append_to_response=credits,keywords,release_dates -> 1 API call per movie
2. ThreadPoolExecutor for fast I/O bound concurrency
3. Strict vote_count >= 200 filter so we ONLY ingest high-quality metadata movies.

Usage:
    d:\Filmbox\.venv\Scripts\python.exe backend\scripts\ingest_fast_threaded.py
"""

import os
import sys
import json
import time
import requests
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Import existing SQLite writer helper
from backend.scripts.ingest_bulk import process_and_insert

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
DB_PATH = os.getenv("DB_PATH", "backend/filmbox.db")
IDS_FILE = os.path.join(os.path.dirname(__file__), "..", "movie_ids_100k.json")

# Hyperparameters
MAX_CONCURRENT_REQUESTS = 30  # Keep it safe for requests thread pool
VOTE_COUNT_THRESHOLD = 200


class RateLimiter:
    """Thread-safe rate limiter to stay under 40 req/s."""
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

rate_limiter = RateLimiter(35)


def fetch_movie_sync(tmdb_id):
    """Fetch movie details using requests with append_to_response."""
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "append_to_response": "credits,keywords,release_dates"
    }

    rate_limiter.wait()
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                time.sleep(1.0 * (attempt + 1))
                continue
            else:
                return None
        except Exception:
            time.sleep(1.0)
    return None


def parse_tmdb_response(data, tmdb_id):
    """Normalize TMDb JSON into the nested structure."""
    if not data:
        return None

    # Quality check!
    if data.get("vote_count", 0) < VOTE_COUNT_THRESHOLD:
        return None

    genres = [g["name"].lower() for g in data.get("genres", [])]
    prod_countries = [
        {"name": c.get("name", ""), "iso_code": c.get("iso_3166_1", "")}
        for c in data.get("production_countries", [])
    ]
    release_date = data.get("release_date", "")
    release_year = int(release_date[:4]) if release_date and len(release_date) >= 4 else None

    details = {
        "tmdb_id": data.get("id"),
        "title": data.get("title", "Unknown"),
        "overview": data.get("overview", ""),
        "genres": genres,
        "release_year": release_year,
        "runtime": data.get("runtime"),
        "popularity": data.get("popularity", 0),
        "vote_average": data.get("vote_average", 0),
        "vote_count": data.get("vote_count", 0),
        "poster_path": data.get("poster_path"),
        "backdrop_path": data.get("backdrop_path"),
        "original_language": data.get("original_language", "en"),
        "production_countries": prod_countries,
    }

    credits_data = data.get("credits", {})
    cast = []
    for person in credits_data.get("cast", [])[:10]:
        cast.append({
            "tmdb_id": person.get("id"),
            "name": person.get("name", "Unknown"),
            "character": person.get("character", ""),
            "order": person.get("order", 99),
            "profile_path": person.get("profile_path"),
        })

    directors = []
    for person in credits_data.get("crew", []):
        if person.get("job") == "Director":
            directors.append({
                "tmdb_id": person.get("id"),
                "name": person.get("name", "Unknown"),
                "profile_path": person.get("profile_path"),
            })
    parsed_credits = {"cast": cast, "directors": directors}

    keywords_data = data.get("keywords", {})
    parsed_keywords = [kw["name"].lower() for kw in keywords_data.get("keywords", [])]

    certification = None
    for country in data.get("release_dates", {}).get("results", []):
        if country.get("iso_3166_1") == "US":
            for release in country.get("release_dates", []):
                cert = release.get("certification", "").strip()
                if cert:
                    certification = cert
                    break
            if certification:
                break

    return {
        "tmdb_id": tmdb_id,
        "details": details,
        "credits": parsed_credits,
        "keywords": parsed_keywords,
        "certification": certification
    }


def worker(tmdb_id):
    raw = fetch_movie_sync(tmdb_id)
    return parse_tmdb_response(raw, tmdb_id)


def main():
    if not TMDB_API_KEY:
        print("❌ Error: TMDB_API_KEY not set.")
        return

    if not os.path.exists(IDS_FILE):
        print(f"❌ Could not find {IDS_FILE}. Run download_bulk_ids.py first.")
        return

    with open(IDS_FILE, "r", encoding="utf-8") as f:
        movie_targets = json.load(f)

    print("🔌 Connecting to DB...")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cursor.execute("SELECT tmdb_id FROM movies WHERE tmdb_id IS NOT NULL")
    existing_ids = {row[0] for row in cursor.fetchall()}
    
    pending_ids = [m["id"] for m in movie_targets if m["id"] not in existing_ids]

    print(f"🚀 FILMBOX Fast Threaded Ingestion Pipeline")
    print(f"   Target list:  {len(movie_targets)} total movies")
    print(f"   Condition:    Vote Count >= {VOTE_COUNT_THRESHOLD}")
    print(f"   Existing:     {len(existing_ids)} skipped")
    print(f"   Pending:      {len(pending_ids)} to fetch")
    print(f"   Threads:      {MAX_CONCURRENT_REQUESTS}")
    print("=" * 60)

    if not pending_ids:
        print("✅ Database is fully up to date with target list.")
        conn.close()
        return

    start_time = time.time()
    processed = 0
    inserted = 0
    rejected = 0

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as executor:
        for result in executor.map(worker, pending_ids):
            processed += 1
            if result is None:
                rejected += 1
            else:
                if process_and_insert(conn, cursor, result):
                    inserted += 1

            # Batch commit every 100 insertions
            if inserted > 0 and inserted % 100 == 0:
                conn.commit()
                elapsed = time.time() - start_time
                rate = processed / elapsed
                print(f"  💾 Batch Committed! Processed {processed}/{len(pending_ids)} | Inserted: {inserted} | Rejected: {rejected} | Rate: {rate:.1f} req/s")

    conn.commit()
    conn.close()

    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"🎬 Ingestion Run Complete!")
    print(f"   Inserted: {inserted} high-quality movies")
    print(f"   Rejected: {rejected} (Vote Count < {VOTE_COUNT_THRESHOLD} or Network Error)")
    print(f"   Time:     {total_time:.1f}s ({processed / total_time:.1f} api_calls/sec)")
    print("=" * 60)


if __name__ == "__main__":
    main()
