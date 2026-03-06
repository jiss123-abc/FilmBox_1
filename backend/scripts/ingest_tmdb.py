"""
FILMBOX — TMDb Bulk Ingestion Script

Fetches movies from TMDb /discover/movie and stores them
with auto-generated archetype vectors using the hybrid tagger.

Usage:
    python -m backend.scripts.ingest_tmdb --pages 5

Each page = 20 movies. Default = 5 pages (100 movies).
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

from backend.tmdb_service import fetch_discover_page, fetch_movie_details
from backend.archetype_tagger import tag_movie, ARCHETYPES

DB_PATH = os.getenv("DB_PATH", "backend/filmbox.db")


def ingest(start_page: int = 1, end_page: int = 5):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ensure tables exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            overview TEXT,
            release_year INTEGER,
            runtime INTEGER,
            popularity REAL,
            vote_average REAL,
            vote_count INTEGER,
            poster_path TEXT,
            backdrop_path TEXT,
            tmdb_id INTEGER UNIQUE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emotional_archetype_tags (
            movie_id INTEGER,
            archetype TEXT NOT NULL,
            weight REAL,
            PRIMARY KEY (movie_id, archetype),
            FOREIGN KEY (movie_id) REFERENCES movies(id)
        )
    """)
    conn.commit()

    total_imported = 0
    total_skipped = 0
    total_tagged = 0

    print(f"🎬 FILMBOX TMDb Ingestion — Fetching pages {start_page} to {end_page} ({ (end_page - start_page + 1) * 20} movies)")
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

            # Skip if already imported by tmdb_id
            cursor.execute("SELECT id FROM movies WHERE tmdb_id = ?", (tmdb_id,))
            if cursor.fetchone():
                total_skipped += 1
                continue

            # Skip if already exists by (title, release_year) to respect UNIQUE constraint
            release_year = int(movie.get("release_date")[:4]) if movie.get("release_date") else None
            cursor.execute("SELECT id FROM movies WHERE title = ? AND release_year = ?", (title, release_year))
            if cursor.fetchone():
                total_skipped += 1
                continue

            # Fetch full details (genres, keywords, runtime)
            details = fetch_movie_details(tmdb_id)
            if not details:
                print(f"  ⚠ Could not fetch details for: {title}")
                continue

            # Insert movie
            cursor.execute("""
                INSERT INTO movies (title, overview, release_year, runtime, popularity,
                                    vote_average, vote_count, poster_path, backdrop_path, tmdb_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                details["title"],
                details["overview"],
                details["release_year"],
                details["runtime"],
                details["popularity"],
                details["vote_average"],
                details["vote_count"],
                details["poster_path"],
                details["backdrop_path"],
                details["tmdb_id"]
            ))
            movie_id = cursor.lastrowid
            total_imported += 1

            # Tag movie using hybrid tagger
            vector = tag_movie(
                title=details["title"],
                overview=details["overview"],
                genres=details["genres"],
                keywords=details["keywords"],
                popularity=details["popularity"],
                runtime=details["runtime"] or 0
            )

            # Store archetype tags
            for archetype in ARCHETYPES:
                weight = vector.get(archetype, 0.0)
                if weight > 0.05:  # Only store meaningful weights
                    cursor.execute("""
                        INSERT OR REPLACE INTO emotional_archetype_tags (movie_id, archetype, weight)
                        VALUES (?, ?, ?)
                    """, (movie_id, archetype, round(weight, 4)))
                    total_tagged += 1

            print(f"  ✅ {details['title']} ({details['release_year'] or '?'})")

        conn.commit()
        print(f"  📊 Page {page} committed.")

        # Brief delay between pages to respect TMDb rate limits
        time.sleep(0.5)

    conn.close()

    print("\n" + "=" * 60)
    print(f"🎬 Ingestion Complete!")
    print(f"   Imported: {total_imported} movies")
    print(f"   Skipped:  {total_skipped} (already in DB)")
    print(f"   Tags:     {total_tagged} archetype tags created")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FILMBOX TMDb Bulk Ingestion")
    parser.add_argument("--start", type=int, default=1, help="Page to start ingestion from (default: 1)")
    parser.add_argument("--end", type=int, default=5, help="Page to end ingestion at (default: 5)")
    args = parser.parse_args()

    ingest(start_page=args.start, end_page=args.end)
