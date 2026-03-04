import sqlite3
from typing import Dict

def get_global_constants(conn: sqlite3.Connection) -> Dict[str, float]:
    """
    Computes global metrics C (average vote) and max_popularity for the dataset.
    m is set to a constant threshold (1000).
    """
    cursor = conn.cursor()
    cursor.execute("SELECT AVG(vote_average), MAX(popularity) FROM movies")
    avg_vote, max_pop = cursor.fetchone()
    
    return {
        "C": avg_vote or 6.5,  # Global average rating
        "max_pop": max_pop or 1.0,
        "m": 1000  # Minimum votes threshold
    }

def calculate_base_score(movie_row: sqlite3.Row, constants: Dict[str, float]) -> Dict[str, float]:
    """
    Calculates the Refined Base Score using Bayesian Weighted Rating.
    
    Formula:
    weighted_rating = ((v / (v + m)) * R + (m / (v + m)) * C)
    pop_score = popularity / max_popularity
    base_score = (0.7 * weighted_rating) + (0.3 * pop_score)
    normalized_base = base_score / 10
    """
    R = movie_row["vote_average"]
    v = movie_row["vote_count"]
    C = constants["C"]
    m = constants["m"]
    pop = movie_row["popularity"]
    max_pop = constants["max_pop"]

    # 1. Bayesian Weighted Rating
    weighted_rating = ((v / (v + m)) * R) + ((m / (v + m)) * C)

    # 2. Popularity Normalization
    pop_score = pop / max_pop if max_pop > 0 else 0

    # 3. Weighted Base Score
    base_score = (0.7 * weighted_rating) + (0.3 * pop_score)

    # 4. Final Normalization to 0-1 scale
    normalized_base = base_score / 10

    return {
        "weighted_rating": round(weighted_rating, 4),
        "pop_score": round(pop_score, 4),
        "normalized_base": round(normalized_base, 4)
    }
