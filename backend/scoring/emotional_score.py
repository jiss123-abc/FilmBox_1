import sqlite3

DB_PATH = "backend/filmbox.db"


def get_emotional_weights(archetype: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT movie_id, weight
        FROM emotional_archetype_tags
        WHERE archetype = ?;
    """, (archetype,))

    weights = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()
    return weights
