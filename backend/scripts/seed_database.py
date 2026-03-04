import sqlite3
import pandas as pd
import os

DB_PATH = "backend/filmbox.db"
SCHEMA_PATH = "backend/models/schema.sql"
CLEANED_DIR = "backend/data/cleaned"

def seed_database():
    print("🚀 Starting Phase 1 Database Seeding...")

    # 1. Reset DB (Dev Mode Only)
    if os.path.exists(DB_PATH):
        print(f"Dropping existing database at {DB_PATH}...")
        os.remove(DB_PATH)

    # Connect to SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 2. Execute Schema Atomically
    print("Executing schema.sql...")
    with open(SCHEMA_PATH, 'r') as f:
        schema_sql = f.read()
    cursor.executescript(schema_sql)

    # 3. Load Cleaned CSVs
    print("Loading cleaned CSVs into memory...")
    movies_df = pd.read_csv(os.path.join(CLEANED_DIR, "movies_cleaned.csv")).fillna('')
    movie_genres_df = pd.read_csv(os.path.join(CLEANED_DIR, "movie_genres.csv")).fillna('')
    movie_keywords_df = pd.read_csv(os.path.join(CLEANED_DIR, "movie_keywords.csv")).fillna('')
    tags_df = pd.read_csv(os.path.join(CLEANED_DIR, "emotional_archetype_tags.csv"))

    # Extract distinct genres and keywords early for parent tables
    unique_genres = set(movie_genres_df['genre_name'])
    unique_keywords = set(movie_keywords_df['keyword_name'])

    # Prepare Genre map for junction table
    genre_name_to_id = {}
    genre_data_to_insert = []
    for g_id, g_name in enumerate(unique_genres, start=1):
        genre_name_to_id[g_name] = g_id
        genre_data_to_insert.append((g_id, g_name))

    # Prepare Keyword map for junction table
    keyword_name_to_id = {}
    keyword_data_to_insert = []
    for k_id, k_name in enumerate(unique_keywords, start=1):
        keyword_name_to_id[k_name] = k_id
        keyword_data_to_insert.append((k_id, k_name))

    print("Beginning bulk insertion transaction...")
    try:
        # Wrap inserts in transaction
        conn.execute("BEGIN TRANSACTION")

        # 4. Insert Movies
        print("- Inserting Movies...")
        movie_records = movies_df[['id', 'title', 'overview', 'release_year', 'runtime', 'popularity', 'vote_average', 'vote_count']].values.tolist()
        cursor.executemany("""
            INSERT INTO movies (id, title, overview, release_year, runtime, popularity, vote_average, vote_count) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, movie_records)

        # 5. Insert Genres
        print("- Inserting Distinct Genres...")
        cursor.executemany("INSERT INTO genres (id, name) VALUES (?, ?)", genre_data_to_insert)

        # 6. Insert Movie_Genres
        print("- Inserting Movie_Genres Mapping...")
        mg_records = []
        for _, row in movie_genres_df.iterrows():
            g_id = genre_name_to_id[row['genre_name']]
            mg_records.append((row['movie_id'], g_id))
        cursor.executemany("INSERT OR IGNORE INTO movie_genres (movie_id, genre_id) VALUES (?, ?)", mg_records)

        # 7. Insert Keywords
        print("- Inserting Distinct Keywords...")
        cursor.executemany("INSERT INTO keywords (id, name) VALUES (?, ?)", keyword_data_to_insert)

        # 8. Insert Movie_Keywords
        print("- Inserting Movie_Keywords Mapping...")
        mk_records = []
        for _, row in movie_keywords_df.iterrows():
            k_id = keyword_name_to_id[row['keyword_name']]
            mk_records.append((row['movie_id'], k_id))
        cursor.executemany("INSERT OR IGNORE INTO movie_keywords (movie_id, keyword_id) VALUES (?, ?)", mk_records)

        # 9. Insert Emotional Archetypes
        print("- Inserting Emotional Archetype Tags...")
        tag_records = tags_df[['movie_id', 'archetype', 'weight']].values.tolist()
        cursor.executemany("INSERT INTO emotional_archetype_tags (movie_id, archetype, weight) VALUES (?, ?, ?)", tag_records)

        conn.commit()
        print("✅ Transaction committed successfully.")
    
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during bulk insert transaction: {e}")
        return

    # 10. Post-Seeding Validation Phase
    print("\n📊 --- Post-Seeding Validation ---")
    cursor.execute("SELECT COUNT(*) FROM movies")
    db_movies_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM emotional_archetype_tags")
    db_tags_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT movie_id) FROM emotional_archetype_tags")
    db_movies_with_tags = cursor.fetchone()[0]

    print(f"Movies expected: {len(movies_df)} | Inserted: {db_movies_count}")
    print(f"Genres expected: {len(unique_genres)} | Inserted: {len(genre_data_to_insert)}")
    print(f"Keywords expected: {len(unique_keywords)} | Inserted: {len(keyword_data_to_insert)}")
    print(f"Emotional Tags expected: {len(tags_df)} | Inserted: {db_tags_count}")
    print(f"Distinct movies emotionally mapped: {db_movies_with_tags}")

    # Exception check matching specification rules
    if db_movies_count != len(movies_df):
        raise ValueError(f"Movie row counts mismatch! Expected {len(movies_df)}, got {db_movies_count}")
        
    if db_tags_count != len(tags_df):
        raise ValueError("Emotional tag row counts mismatch!")

    if db_movies_with_tags < db_movies_count:
        print(f"⚠️ Warning: {db_movies_count - db_movies_with_tags} movies do not have any mapped archetypes based on current generation logic.")

    print("\n✅ Phase 1 Data Foundation is officially COMPLETE.")

if __name__ == "__main__":
    seed_database()
