"""
FILMBOX — Offline Emotional Tagging Engine (Phase 9)

Computes the 6D emotional archetype vector for movies.
Designed to run purely offline after `ingest_bulk.py` has run.
Processes only movies missing from the `emotional_archetype_tags` table.
"""

import os
import sys
import sqlite3
import time

# Add project root to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from backend.archetype_tagger import tag_movie, ARCHETYPES

DB_PATH = os.getenv("DB_PATH", "backend/filmbox.db")
BATCH_SIZE = 1000


def batch_tag_movies():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # 1. Identify movies that have no tags yet
    print("⏳ Finding movies missing emotional tags...")
    cursor.execute("""
        SELECT m.id, m.title, m.overview, m.popularity, m.runtime
        FROM movies m
        LEFT JOIN emotional_archetype_tags e ON m.id = e.movie_id
        WHERE e.movie_id IS NULL
    """)
    movies_to_tag = cursor.fetchall()
    
    total = len(movies_to_tag)
    if total == 0:
        print("✅ All movies are fully tagged.")
        conn.close()
        return
        
    print(f"🎬 FILMBOX Offline Tagging Engine")
    print(f"   Movies to process: {total}")
    print("=" * 60)

    start_time = time.time()
    processed = 0
    tags_inserted = 0

    for i, (movie_id, title, overview, popularity, runtime) in enumerate(movies_to_tag):
        # Fetch genres
        cursor.execute("""
            SELECT g.name 
            FROM genres g 
            JOIN movie_genres mg ON mg.genre_id = g.id 
            WHERE mg.movie_id = ?
        """, (movie_id,))
        genres = [row[0] for row in cursor.fetchall()]

        # Fetch keywords
        cursor.execute("""
            SELECT k.name 
            FROM keywords k 
            JOIN movie_keywords mk ON mk.keyword_id = k.id 
            WHERE mk.movie_id = ?
        """, (movie_id,))
        keywords = [row[0] for row in cursor.fetchall()]

        # Run completely local rule-based tagger (disable LLM fallback for bulk processing)
        vector = tag_movie(
            title=title,
            overview=overview,
            genres=genres,
            keywords=keywords,
            popularity=popularity or 0,
            runtime=runtime or 0,
            use_llm_fallback=False
        )

        for archetype in ARCHETYPES:
            weight = vector.get(archetype, 0.0)
            if weight > 0.05:
                cursor.execute("""
                    INSERT INTO emotional_archetype_tags
                        (movie_id, archetype, weight)
                    VALUES (?, ?, ?)
                """, (movie_id, archetype, round(weight, 4)))
                tags_inserted += 1

        processed += 1
        
        # Batch Commit
        if processed % BATCH_SIZE == 0:
            conn.commit()
            elapsed = time.time() - start_time
            rate = processed / elapsed
            print(f"  💾 Tagged {processed}/{total} movies ({rate:.1f} movies/sec)")

    conn.commit()
    conn.close()

    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"🎬 Tagging Engine Complete!")
    print(f"   Processed: {processed} movies")
    print(f"   Vectors:   {tags_inserted} rows inserted")
    print(f"   Time:      {total_time:.1f}s ({(processed / total_time):.1f} movies/sec)")


if __name__ == "__main__":
    batch_tag_movies()
