from .base_score import compute_base_scores
from .emotional_score import get_emotional_weights

ALPHA = 0.35   # emotional amplification factor


def recommend(archetype: str | None = None, limit: int = 20):

    base_scores = compute_base_scores()

    if archetype:
        emotional_weights = get_emotional_weights(archetype)
    else:
        emotional_weights = {}

    final_scores = []

    for movie_id, base in base_scores.items():

        emotional = emotional_weights.get(movie_id, 0)

        final_score = base + (ALPHA * emotional)

        final_scores.append((movie_id, final_score))

    # Sort descending
    final_scores.sort(key=lambda x: x[1], reverse=True)

    return final_scores[:limit]
