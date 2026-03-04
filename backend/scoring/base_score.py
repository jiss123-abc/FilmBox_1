import sqlite3

DB_PATH = "backend/filmbox.db"
MIN_VOTES = 1000   # m value (tunable)


def get_global_average():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT AVG(vote_average) FROM movies;")
    C = cursor.fetchone()[0]
    conn.close()
    return C


def get_max_popularity():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(popularity) FROM movies;")
    max_pop = cursor.fetchone()[0]
    conn.close()
    return max_pop


def compute_base_scores():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    C = get_global_average()
    max_pop = get_max_popularity()

    cursor.execute("""
        SELECT id, vote_average, vote_count, popularity
        FROM movies;
    """)

    base_scores = {}

    for movie_id, R, v, popularity in cursor.fetchall():

        # Bayesian weighted rating
        weighted_rating = (
            (v / (v + MIN_VOTES)) * R +
            (MIN_VOTES / (v + MIN_VOTES)) * C
        )

        # Normalize popularity
        pop_score = popularity / max_pop if max_pop else 0

        base_score = (0.7 * weighted_rating) + (0.3 * pop_score)

        # Normalize to 0–1
        normalized_base = base_score / 10

        base_scores[movie_id] = normalized_base

    conn.close()
    return base_scores
