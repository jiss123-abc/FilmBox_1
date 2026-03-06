import os
import sqlite3
import requests
import time
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "backend/filmbox.db"
API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3/movie/"

def fetch_posters():
    if not API_KEY:
        print("❌ Error: TMDB_API_KEY not found in .env file.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ensure the column exists (in case schema.sql wasn't rerun)
    try:
        cursor.execute("ALTER TABLE movies ADD COLUMN poster_path TEXT")
        print("✅ Added poster_path column to movies table.")
    except sqlite3.OperationalError:
        print("ℹ️ poster_path column already exists.")

    # Get movies that don't have a poster_path yet
    cursor.execute("SELECT id, title FROM movies WHERE poster_path IS NULL")
    movies_to_update = cursor.fetchall()

    if not movies_to_update:
        print("✨ All movies already have posters or no movies found.")
        return

    print(f"🎬 Found {len(movies_to_update)} movies to update...")

    # Use a session with retries for better stability
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)

    count = 0
    for movie_id, title in movies_to_update:
        try:
            # Added explicit timeout (timeout=10)
            response = session.get(
                f"{BASE_URL}{movie_id}",
                params={"api_key": API_KEY},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                poster_path = data.get("poster_path")
                
                if poster_path:
                    cursor.execute(
                        "UPDATE movies SET poster_path = ? WHERE id = ?",
                        (poster_path, movie_id)
                    )
                    count += 1
                    print(f"✅ Updated: {title}")
                else:
                    # Mark as empty so we don't keep trying
                    cursor.execute(
                        "UPDATE movies SET poster_path = '' WHERE id = ?",
                        (movie_id,)
                    )
                    print(f"⚠️ No poster found for: {title}")
            elif response.status_code == 429:
                print("⏳ Rate limited! Sleeping for 10 seconds...")
                time.sleep(10)
            else:
                print(f"❌ Failed to fetch {title} (Status: {response.status_code})")

            # Small delay to respect rate limits
            time.sleep(0.1)

            # Periodic commit
            if count % 50 == 0:
                conn.commit()

        except Exception as e:
            print(f"❌ Error fetching {title}: {e}")

    conn.commit()
    conn.close()
    print(f"\n🎉 Finished! Updated {count} posters in the database.")

if __name__ == "__main__":
    fetch_posters()
