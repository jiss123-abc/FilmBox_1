import sqlite3
import os

DB_PATH = "backend/filmbox.db"

def check_distribution():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n--- Archetype Distribution (Threshold 0.20) ---")
    query = """
    SELECT archetype,
           COUNT(*) AS total,
           ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM emotional_archetype_tags), 2) AS percentage
    FROM emotional_archetype_tags
    GROUP BY archetype
    ORDER BY percentage DESC;
    """
    cursor.execute(query)
    for row in cursor.fetchall():
        print(f"{row[0]:<15} | {row[1]:<5} | {row[2]}%")

    print("\n--- System Coverage ---")
    cursor.execute("SELECT COUNT(*) FROM movies;")
    total_movies = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT movie_id) FROM emotional_archetype_tags;")
    mapped_movies = cursor.fetchone()[0]
    
    coverage_pct = (mapped_movies / total_movies * 100) if total_movies > 0 else 0
    
    print(f"Total Movies in DB:       {total_movies}")
    print(f"Emotionally Mapped:       {mapped_movies}")
    print(f"Unmapped:                 {total_movies - mapped_movies}")
    print(f"Coverage:                 {coverage_pct:.2f}%")

    print("\n--- Density Check ---")
    cursor.execute("SELECT COUNT(*) FROM (SELECT movie_id FROM emotional_archetype_tags GROUP BY movie_id HAVING COUNT(*) > 4);")
    excessive_count = cursor.fetchone()[0]
    print(f"Movies with > 4 archetypes: {excessive_count}")

    conn.close()

if __name__ == "__main__":
    check_distribution()
