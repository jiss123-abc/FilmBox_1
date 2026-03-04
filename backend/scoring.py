from sqlalchemy import text

ALPHA = 0.35
M = 1000

def get_recommendations(db, archetype: str, global_c: float):

    query = text("""
    SELECT
        m.id,
        m.title,
        m.vote_average,
        m.vote_count,
        m.popularity,
        COALESCE(e.weight, 0) as emotional_weight
    FROM movies m
    LEFT JOIN emotional_archetype_tags e
        ON m.id = e.movie_id
        AND e.archetype = :archetype
    """)

    movies = db.execute(query, {"archetype": archetype}).fetchall()

    results = []

    for movie in movies:
        R = movie.vote_average
        v = movie.vote_count

        weighted_rating = (
            (v / (v + M)) * R +
            (M / (v + M)) * global_c
        ) if v > 0 else global_c

        # Correcting pop_score to use a relative mapping if max_pop is known, 
        # or a safe dampener as per newest spec
        pop_score = min(movie.popularity / 100, 10)

        base_score = (0.7 * weighted_rating) + (0.3 * pop_score)
        normalized_base = base_score / 10

        final_score = normalized_base + (ALPHA * movie.emotional_weight)

        results.append({
            "id": movie.id,
            "title": movie.title,
            "final_score": round(final_score, 4),
            "base_score": round(normalized_base, 4),
            "emotional_weight": movie.emotional_weight
        })

    results.sort(key=lambda x: x["final_score"], reverse=True)

    return results
