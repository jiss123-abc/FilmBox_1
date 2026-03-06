from sqlalchemy import text
import math
from datetime import datetime, timezone

# --- Constants ---
ARCHETYPES = [
    "mind_bending",
    "dark",
    "emotional",
    "inspirational",
    "adrenaline",
    "light"
]

ALPHA = 0.35       # Emotional amplification for single-archetype mode
M = 500             # Reduced Bayesian smoothing constant for slightly faster data sensitivity
QUALITY_FLOOR = 0.4  # Lowered quality floor to allow emotional relevance to lead
EMOTION_CEIL = 0.6   # Increased emotional similarity weight

# --- Personalization Constants ---
ACTION_WEIGHTS = {
    "liked": 1.0,
    "saved": 0.8,
    "clicked": 0.3
}
MIN_INTERACTIONS = 3
MAX_INTERACTIONS = 30
BETA = 0.25 # Personalization strength
DECAY_LAMBDA = 0.035 # Exponential time decay


# --- Vector Math ---
def normalize_vector(vec_dict: dict) -> dict:
    """Normalize a dictionary vector to unit length."""
    values = list(vec_dict.values())
    norm = math.sqrt(sum(v * v for v in values))
    if norm == 0:
        return vec_dict
    return {k: v / norm for k, v in vec_dict.items()}


def cosine_similarity(vec1: list, vec2: list) -> float:
    """Compute cosine similarity between two ordered lists."""
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot / (norm1 * norm2)


def build_movie_vector(archetype_weights: dict) -> list:
    """Build a 6D ordered list from archetype weights, zero-filling missing dimensions."""
    return [archetype_weights.get(a, 0.0) for a in ARCHETYPES]


def build_explanation(movie_vec_dict: dict, query_vec: dict, user_vec: dict, final_vec: dict) -> list:
    contributions = {
        a: final_vec.get(a, 0.0) * movie_vec_dict.get(a, 0.0)
        for a in ARCHETYPES
    }

    sorted_dims = sorted(
        contributions.items(),
        key=lambda x: x[1],
        reverse=True
    )

    explanation = []

    if sorted_dims:
        # Primary match
        primary = sorted_dims[0][0]
        explanation.append(
            f"Strong match for: {primary.replace('_', ' ').title()}"
        )

        # Optional secondary match
        if len(sorted_dims) > 1 and sorted_dims[1][1] > 0.65 * sorted_dims[0][1]:
            secondary = sorted_dims[1][0]
            explanation.append(
                f"Also aligns with: {secondary.replace('_', ' ').title()}"
            )

    # Personalization hint
    if user_vec:
        for a in ARCHETYPES:
            if abs(user_vec.get(a, 0.0) - query_vec.get(a, 0.0)) > 0.15 and movie_vec_dict.get(a, 0.0) > 0.4:
                explanation.append(
                    f"Influenced by your preference for {a.replace('_', ' ')} films"
                )
                break

    return explanation[:3]


# --- Personalization Layer ---
def get_recent_interactions(db, session_id: str, limit: int):
    query = text("""
        SELECT movie_id, action, created_at
        FROM user_interactions
        WHERE session_id = :session_id
        ORDER BY created_at DESC
        LIMIT :limit
    """)
    return db.execute(query, {"session_id": session_id, "limit": limit}).fetchall()


def get_movie_vector(db, movie_id: int):
    query = text("""
        SELECT archetype, weight
        FROM emotional_archetype_tags
        WHERE movie_id = :movie_id
    """)
    rows = db.execute(query, {"movie_id": movie_id}).fetchall()
    return {r.archetype: r.weight for r in rows}


def compute_user_vector(db, session_id: str) -> tuple[dict, int]:
    if not session_id:
        return None, 0

    interactions = get_recent_interactions(db, session_id, MAX_INTERACTIONS)
    interaction_count = len(interactions)

    # Safe Fallback: Do not personalize early experience
    if interaction_count < MIN_INTERACTIONS:
        return None, interaction_count

    accumulator = {a: 0.0 for a in ARCHETYPES}
    now = datetime.now(timezone.utc)

    for action_row in interactions:
        movie_vec = get_movie_vector(db, action_row.movie_id)
        base_weight = ACTION_WEIGHTS.get(action_row.action, 0)
        
        created_at = action_row.created_at
        
        # Robust processing of created_at based on SQLite string or native DB return
        if isinstance(created_at, str):
            try:
                # E.g. "2023-10-12 14:30:00"
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                created_at = now
                
        if getattr(created_at, "tzinfo", None) is None:
            try:
                created_at = created_at.replace(tzinfo=timezone.utc)
            except AttributeError:
                pass
                
        try:
            age_days = (now - created_at).total_seconds() / 86400.0
        except Exception:
            age_days = 0.0
            
        # Guarantee no negative ages due to clock drift
        time_weight = math.exp(-DECAY_LAMBDA * max(0, age_days))
        final_weight = base_weight * time_weight
        
        for a in ARCHETYPES:
            accumulator[a] += movie_vec.get(a, 0.0) * final_weight

    return normalize_vector(accumulator), interaction_count


# --- Single-archetype mode (backward compat for /recommend) ---
def get_recommendations(db, archetype: str, global_c: float):
    query = text("""
    SELECT
        m.id,
        m.title,
        m.vote_average,
        m.vote_count,
        m.popularity,
        m.poster_path,
        COALESCE(e.weight, 0) as emotional_weight
    FROM movies m
    LEFT JOIN emotional_archetype_tags e
        ON m.id = e.movie_id
        AND e.archetype = :archetype
    """)

    movies = db.execute(query, {"archetype": archetype}).fetchall()
    results = []

    for movie in movies:
        R = movie.vote_average or 0
        v = movie.vote_count or 0

        weighted_rating = (
            (v / (v + M)) * R +
            (M / (v + M)) * global_c
        ) if v > 0 else global_c

        pop_score = min((movie.popularity or 0) / 100, 10)
        base_score = (0.7 * weighted_rating) + (0.3 * pop_score)
        normalized_base = base_score / 10

        final_score = normalized_base + (ALPHA * movie.emotional_weight)

        # Rating Soft Boost integration
        normalized_rating = min(R / 10, 1.0)
        final_score *= (1 + 0.05 * normalized_rating)

        results.append({
            "id": movie.id,
            "title": movie.title,
            "final_score": round(final_score, 4),
            "base_score": round(normalized_base, 4),
            "emotional_weight": movie.emotional_weight,
            "poster_path": movie.poster_path,
            "similarity_score": 0.0
        })

    results.sort(key=lambda x: x["final_score"], reverse=True)
    return results


# --- 6D Vector mode (new /explore engine) ---
def get_vector_recommendations(db, query_vector: dict, global_c: float, user_vector: dict = None, interaction_count: int = 0):
    """
    Score all movies using cosine similarity between the final blended emotional vector
    and movie emotional vectors, gated by base quality. Includes Rating Soft Boost and
    Diversity Control (top 30 interleaving).
    """

    # 1. Blending query with personal taste (if enough history)
    if user_vector:
        # Adaptive Beta
        if interaction_count <= 10:
            beta = 0.25
        else:
            beta = 0.35
            
        final_vector = {
            a: (1 - beta) * query_vector.get(a, 0.0) +
               beta * user_vector.get(a, 0.0)
            for a in ARCHETYPES
        }
        final_vector = normalize_vector(final_vector)
    else:
        final_vector = query_vector

    # Build final reference vector (ordered list)
    reference_vec = [final_vector.get(a, 0.0) for a in ARCHETYPES]

    # 2. Load all movies + their archetype tags in one query
    query = text("""
        SELECT
            m.id, m.title, m.vote_average, m.vote_count, m.popularity, m.poster_path,
            e.archetype, e.weight
        FROM movies m
        LEFT JOIN emotional_archetype_tags e ON m.id = e.movie_id
    """)

    rows = db.execute(query).fetchall()

    # 3. Build in-memory movie map
    movie_map = {}
    for row in rows:
        mid = row.id
        if mid not in movie_map:
            movie_map[mid] = {
                "id": mid,
                "title": row.title,
                "vote_average": row.vote_average or 0,
                "vote_count": row.vote_count or 0,
                "popularity": row.popularity or 0,
                "poster_path": row.poster_path,
                "archetypes": {}
            }
        if row.archetype:
            movie_map[mid]["archetypes"][row.archetype] = row.weight

    # 4. Score each movie
    results = []
    for mid, movie in movie_map.items():
        R = movie["vote_average"]
        v = movie["vote_count"]

        # Bayesian weighted rating
        weighted_rating = (
            (v / (v + M)) * R +
            (M / (v + M)) * global_c
        ) if v > 0 else global_c

        pop_score = min(movie["popularity"] / 100, 10)
        base_score = (0.7 * weighted_rating) + (0.3 * pop_score)
        base_quality = base_score / 10

        # Cosine similarity
        movie_vec = build_movie_vector(movie["archetypes"])
        similarity = cosine_similarity(reference_vec, movie_vec)

        # Quality-gated emotional scoring
        final_score = base_quality * (QUALITY_FLOOR + EMOTION_CEIL * similarity)

        # ✨ Premium Upgrade: Rating Soft Boost (max 5%)
        normalized_rating = min(R / 10, 1.0)
        final_score *= (1 + 0.05 * normalized_rating)

        # Determine dominant archetype for diversity interleaving
        dominant_archetype = None
        if movie["archetypes"]:
            dominant_archetype = max(movie["archetypes"], key=movie["archetypes"].get)

        # 🎯 Premium Upgrade: Explanation Layer
        explanation = build_explanation(
            movie["archetypes"], 
            query_vector, 
            user_vector, 
            final_vector
        )

        results.append({
            "id": mid,
            "title": movie["title"],
            "final_score": round(final_score, 4),
            "base_score": round(base_quality, 4),
            "emotional_weight": round(similarity, 4),
            "poster_path": movie["poster_path"],
            "similarity_score": round(similarity, 4),
            "dominant_archetype": dominant_archetype,
            "explanation": explanation,
            "movie_archetypes": movie["archetypes"]
        })

    # Sort descending
    results.sort(key=lambda x: x["final_score"], reverse=True)

    top_30 = results[:30]

    # 6. ✨ Premium Upgrade: Counterfactual Explanations
    # Compare each of the true top 30 against its immediate runner-up (Pre-Interleaving)
    for i in range(len(top_30) - 1):
        A = top_30[i]
        B = top_30[i+1]
        
        score_gap = A["final_score"] - B["final_score"]
        
        # Only compare if they are competitive and runner-up is credible
        if score_gap > 0.05 or score_gap < 0 or B["final_score"] < (0.7 * A["final_score"]):
            continue
            
        advantages = {}
        for a in ARCHETYPES:
            contrib_A = final_vector.get(a, 0.0) * A["movie_archetypes"].get(a, 0.0)
            contrib_B = final_vector.get(a, 0.0) * B["movie_archetypes"].get(a, 0.0)
            advantages[a] = contrib_A - contrib_B
            
        best_archetype = max(advantages, key=advantages.get)
        
        if advantages[best_archetype] > 0.02:
            # Prevent duplicate archetype explanations
            primary_match_str = f"Strong match for: {best_archetype.replace('_', ' ').title()}"
            if any(primary_match_str in exp for exp in A["explanation"]):
                continue

            cf_text = f"Chosen over {B['title']} due to stronger {best_archetype.replace('_', ' ')} alignment."
            # Maintain 3-bullet cap for UX
            if len(A["explanation"]) >= 3:
                A["explanation"][2] = cf_text
            else:
                A["explanation"].append(cf_text)

    # 5. ✨ Premium Upgrade: Emotional Diversity Control
    # Interleave the top 30 to prevent monotone result blocks.
    diverse_results = []
    last_dom = None
    
    while top_30:
        selected_idx = 0  # Default to highest score
        if last_dom:
            # Find the highest scoring movie that breaks the monotone block
            for i, res in enumerate(top_30):
                if res.get("dominant_archetype") != last_dom:
                    selected_idx = i
                    break
        
        selected = top_30.pop(selected_idx)
        diverse_results.append(selected)
        last_dom = selected.get("dominant_archetype")

    # Recombine diverse top 30 with the rest
    final_results = diverse_results + results[30:]

    return final_results, final_vector
