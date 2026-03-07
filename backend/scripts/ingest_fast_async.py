"""
FILMBOX — Ultra-Fast Async Bulk Ingestion Script
Based on optimizations for maximum ingestion speed and relevance:

1. append_to_response=credits,keywords,release_dates -> 1 API call per movie
2. aiohttp + asyncio for blazing fast concurrency
3. Quality over Quantity: Strict vote_count >= 200 filter so we ONLY
   ingest movies with robust metadata (best for emotional engine & context search).

Usage:
    pip install aiohttp
    python backend/scripts/ingest_fast_async.py
"""

import os
import sys
import json
import time
import asyncio
import aiohttp
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Import existing SQLite writer helper from the synchronous script
from backend.scripts.ingest_bulk import process_and_insert

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
DB_PATH = os.getenv("DB_PATH", "backend/filmbox.db")
IDS_FILE = os.path.join(os.path.dirname(__file__), "..", "movie_ids.json")

# Hyperparameters
MAX_CONCURRENT_REQUESTS = 40  # TMDb allows 40 req/sec
VOTE_COUNT_THRESHOLD = 200    # Only ingest high-quality metadata movies


async def fetch_movie_async(session, tmdb_id, semaphore):
    """Fetch movie details using aiohttp with append_to_response."""
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "append_to_response": "credits,keywords,release_dates"
    }

    async with semaphore:
        for attempt in range(3):
            try:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        return None
            except Exception:
                await asyncio.sleep(1.0)
        return None


def parse_tmdb_response(data, tmdb_id):
    """Normalize TMDb JSON into the nested structure expected by process_and_insert."""
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


async def bound_fetch_and_parse(session, tmdb_id, semaphore):
    """Fetch from network and directly parse."""
    raw_data = await fetch_movie_async(session, tmdb_id, semaphore)
    if not raw_data:
        return None
    return parse_tmdb_response(raw_data, tmdb_id)


async def main_async():
    if not TMDB_API_KEY:
        print("❌ Error: TMDB_API_KEY not set.")
        return

    if not os.path.exists(IDS_FILE):
        print(f"❌ Could not find {IDS_FILE}. Run download_bulk_ids.py first.")
        return

    with open(IDS_FILE, "r", encoding="utf-8") as f:
        movie_targets = json.load(f)

    print("🔌 Connecting to DB...")
    conn = sqlite3.connect(DB_PATH, isolation_level=None) # Auto-commit helps with batching here
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    cursor = conn.cursor()

    cursor.execute("SELECT tmdb_id FROM movies WHERE tmdb_id IS NOT NULL")
    existing_ids = {row[0] for row in cursor.fetchall()}
    
    pending_ids = [m["id"] for m in movie_targets if m["id"] not in existing_ids]

    print(f"🚀 FILMBOX Async Parallel Ingestion Pipeline")
    print(f"   Target list:  {len(movie_targets)} total movies")
    print(f"   Condition:    Vote Count >= {VOTE_COUNT_THRESHOLD}")
    print(f"   Existing:     {len(existing_ids)} skipped")
    print(f"   Pending:      {len(pending_ids)} to fetch")
    print(f"   Config:       {MAX_CONCURRENT_REQUESTS} concurrent reqs (aiohttp)")
    print("=" * 60)

    if not pending_ids:
        print("✅ Database is fully up to date with target list.")
        conn.close()
        return

    start_time = time.time()
    processed = 0
    inserted = 0
    rejected = 0

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    async with aiohttp.ClientSession() as session:
        # We process in batches of 1000 to avoid memory blowup with asyncio.gather
        batch_size = 1000
        for i in range(0, len(pending_ids), batch_size):
            batch_ids = pending_ids[i:i + batch_size]
            
            tasks = [bound_fetch_and_parse(session, tid, semaphore) for tid in batch_ids]
            
            # Run the batch concurrently
            results = await asyncio.gather(*tasks)
            
            cursor.execute("BEGIN TRANSACTION;")
            for res in results:
                processed += 1
                if res is None:
                    rejected += 1
                    continue
                
                # Insert into DB (synchronous, but SQLite is incredibly fast for this)
                 # process_and_insert will return True if inserted, False if conflict
                if process_and_insert(conn, cursor, res):
                    inserted += 1
            cursor.execute("COMMIT;")
            
            elapsed = time.time() - start_time
            rate = processed / elapsed
            print(f"⏱️  Batch complete | Processed: {processed} | Inserted: {inserted} | Rejected (Low Votes): {rejected} | Rate: {rate:.1f} req/s")

    conn.close()

    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"🎬 Ingestion Run Complete!")
    print(f"   Inserted: {inserted} high-quality movies")
    print(f"   Rejected: {rejected} (Vote Count < {VOTE_COUNT_THRESHOLD} or Network Error)")
    print(f"   Time:     {total_time:.1f}s ({processed / total_time:.1f} api_calls/sec)")
    print("=" * 60)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main_async())
