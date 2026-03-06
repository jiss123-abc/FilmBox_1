import requests
import sqlite3
import os
import time
import socket
from dotenv import load_dotenv

# --- Fix for TMDB Connection Issues (Force IPv4) ---
def force_ipv4():
    orig_getaddrinfo = socket.getaddrinfo
    def new_getaddrinfo(*args, **kwargs):
        return [res for res in orig_getaddrinfo(*args, **kwargs) if res[0] == socket.AF_INET]
    socket.getaddrinfo = new_getaddrinfo

force_ipv4()
# --------------------------------------------------

load_dotenv()

API_KEY = os.getenv("TMDB_API_KEY")
SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
DB_PATH = "backend/filmbox.db"


def search_tmdb(title, year=None):
    """Search TMDB with optional year filter. Returns first result or None."""
    params = {
        "api_key": API_KEY,
        "query": title,
    }
    if year:
        params["year"] = year

    response = requests.get(SEARCH_URL, params=params, timeout=10)

    if response.status_code == 200:
        data = response.json()
        if data["results"]:
            return data["results"][0]
    elif response.status_code == 429:
        print("⏳ Rate limited! Sleeping for 10 seconds...")
        time.sleep(10)
        return search_tmdb(title, year)  # Retry after cooldown

    return None


def enrich_data():
    if not API_KEY:
        print("❌ Error: TMDB_API_KEY not found in .env")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Step 1: Ensure columns exist
    cols_to_add = [
        ("tmdb_id", "INTEGER"),
        ("backdrop_path", "TEXT")
    ]
    for col, col_type in cols_to_add:
        try:
            cursor.execute(f"ALTER TABLE movies ADD COLUMN {col} {col_type}")
            print(f"✅ Added column: {col}")
        except sqlite3.OperationalError:
            pass

    # Step 2: Fetch movies that need enrichment
    cursor.execute("""
        SELECT id, title, release_year
        FROM movies
        WHERE tmdb_id IS NULL OR poster_path IS NULL
    """)
    movies = cursor.fetchall()

    if not movies:
        print("✨ Database is already fully enriched!")
        return

    print(f"🎬 Starting enrichment for {len(movies)} movies...")

    count = 0
    fail_count = 0
    fallback_count = 0
    
    for movie_id, title, year in movies:
        try:
            # Primary search: with year filter
            result = search_tmdb(title, year)

            # Fallback search: without year filter
            if not result and year:
                result = search_tmdb(title)
                if result:
                    fallback_count += 1

            if result:
                cursor.execute("""
                    UPDATE movies
                    SET tmdb_id = ?, 
                        poster_path = ?, 
                        backdrop_path = ?, 
                        overview = ?,
                        popularity = ?,
                        vote_average = ?,
                        vote_count = ?
                    WHERE id = ?
                """, (
                    result["id"],
                    result.get("poster_path"),
                    result.get("backdrop_path"),
                    result.get("overview", ""),
                    result.get("popularity", 0),
                    result.get("vote_average", 0),
                    result.get("vote_count", 0),
                    movie_id
                ))
                print(f"✔ [{(count+1)}/{len(movies)}] Updated: {title}")
                count += 1
            else:
                print(f"✘ No match: {title}")
                fail_count += 1

            # Avoid hitting rate limits (4 req/sec is safe)
            time.sleep(0.25)

            # Periodic commit
            if count % 20 == 0:
                conn.commit()

        except Exception as e:
            print(f"⚠ Error with {title}: {e}")
            fail_count += 1

    conn.commit()
    conn.close()

    # Summary
    print(f"\n🎉 Enrichment Complete!")
    print(f"  ✅ Successfully enriched: {count}")
    print(f"  🔄 Fallback recoveries:   {fallback_count}")
    print(f"  ❌ Failed/No match:       {fail_count}")
    success_rate = (count / len(movies)) * 100 if movies else 0
    print(f"  📊 Success rate:          {success_rate:.1f}%")


if __name__ == "__main__":
    enrich_data()
