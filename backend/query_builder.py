"""
FILMBOX — Query Builder (Phase 8)

Unified pipeline: Structured Intent → SQL Filters → Candidates → Emotional Re-ranking

Takes structured JSON from the intent classifier and builds dynamic SQL queries
combining filters for: person, language, country, keyword, certification, rating.
Then applies emotional vector scoring on the filtered candidates.
"""

from sqlalchemy import text
import math

from .scoring import (
    ARCHETYPES, M, QUALITY_FLOOR, EMOTION_CEIL,
    normalize_vector, cosine_similarity, build_movie_vector,
    build_explanation,
)


def build_filtered_query(intent: dict) -> tuple:
    """
    Builds a dynamic SQL query from structured intent filters.

    Intent keys:
        person_name: str | None
        language: str | None
        country: str | None
        keyword: str | None
        certification: str | None
        sort_by: str | None  ("best", "worst", "trending", "random", "hidden_gems")

    Returns: (sql_string, params_dict)
    """
    select = """
        SELECT DISTINCT
            m.id, m.title, m.overview, m.vote_average, m.vote_count,
            m.popularity, m.poster_path, m.release_year, m.runtime
        FROM movies m
    """
    joins = []
    conditions = []
    params = {}

    # ── Person filter ──
    person_name = intent.get("person_name")
    if person_name:
        joins.append("JOIN movie_credits mc ON mc.movie_id = m.id")
        joins.append("JOIN people p ON p.id = mc.person_id")
        conditions.append("LOWER(p.name) LIKE :person_pattern")
        params["person_pattern"] = f"%{person_name.lower()}%"

    # ── Language filter ──
    language = intent.get("language")
    if language:
        joins.append("JOIN languages lang ON lang.id = m.language_id")
        if len(language) <= 3:
            # Short codes → exact match on ISO code (e.g. "hi", "ko", "en")
            conditions.append("LOWER(lang.iso_code) = :lang_code")
            params["lang_code"] = language.lower()
        else:
            # Longer strings → fuzzy match on name (e.g. "Hindi", "Korean")
            conditions.append("LOWER(lang.name) LIKE :lang_pattern")
            params["lang_pattern"] = f"%{language.lower()}%"

    # ── Country filter ──
    country = intent.get("country")
    if country:
        joins.append("JOIN movie_countries mco ON mco.movie_id = m.id")
        joins.append("JOIN countries co ON co.id = mco.country_id")
        conditions.append("(LOWER(co.name) LIKE :country_pattern OR LOWER(co.continent) LIKE :country_pattern)")
        params["country_pattern"] = f"%{country.lower()}%"

    # ── Keyword filter ──
    keyword = intent.get("keyword")
    if keyword:
        joins.append("JOIN movie_keywords mkw ON mkw.movie_id = m.id")
        joins.append("JOIN keywords kw ON kw.id = mkw.keyword_id")
        conditions.append("LOWER(kw.name) LIKE :kw_pattern")
        params["kw_pattern"] = f"%{keyword.lower()}%"

    # ── Certification filter ──
    certification = intent.get("certification")
    if certification:
        joins.append("JOIN certifications cert ON cert.id = m.certification_id")
        conditions.append("UPPER(cert.rating) = :cert_rating")
        params["cert_rating"] = certification.upper()

    # ── Hidden gems filter ──
    sort_by = intent.get("sort_by")
    if sort_by == "hidden_gems":
        conditions.append("m.vote_average > 7.0")
        conditions.append("m.vote_count < 500")

    # ── Assemble query ──
    sql = select
    for j in joins:
        sql += f"\n        {j}"

    if conditions:
        sql += "\n        WHERE " + " AND ".join(conditions)

    # ── Ordering ──
    if sort_by == "best":
        sql += "\n        ORDER BY m.vote_average DESC"
    elif sort_by == "worst":
        sql += "\n        ORDER BY m.vote_average ASC"
    elif sort_by == "trending":
        sql += "\n        ORDER BY m.popularity DESC"
    elif sort_by == "random":
        sql += "\n        ORDER BY RANDOM()"
    elif sort_by == "hidden_gems":
        sql += "\n        ORDER BY m.vote_average DESC"
    else:
        sql += "\n        ORDER BY m.popularity DESC"

    sql += "\n        LIMIT 200"

    return sql, params


CONTEXT_BOOST = 0.4  # Context match provides up to 40% score boost


def execute_discovery(db, intent: dict, global_c: float, query_vector: dict = None,
                      user_vector: dict = None, interaction_count: int = 0,
                      context_scores: dict = None) -> tuple:
    """
    Full discovery pipeline:
        1. Build SQL from structured filters
        2. Fetch candidate movies
        3. Load archetype tags for candidates
        4. Apply emotional re-ranking (if vector present)
        5. Apply context boost (if context_scores present)
        6. Return scored results + metadata

    Returns: (results_list, final_vector_or_None, explanation_str)
    """

    sql, params = build_filtered_query(intent)
    rows = db.execute(text(sql), params).fetchall()

    # ── Merge context-matched candidates into the pool ──
    # When context search finds movies not already in the SQL candidates,
    # we fetch them separately so they can participate in scoring.
    if context_scores:
        existing_ids = {row.id for row in rows}
        context_only_ids = [mid for mid in context_scores if mid not in existing_ids]

        if context_only_ids:
            # Fetch the top context-matched movies not already in candidates
            top_context_ids = sorted(context_only_ids, key=lambda x: context_scores.get(x, 0), reverse=True)[:300]
            placeholders = ",".join([f":ctx_{i}" for i in range(len(top_context_ids))])
            ctx_sql = f"""
                SELECT id, title, overview, vote_average, vote_count,
                       popularity, poster_path, release_year, runtime
                FROM movies
                WHERE id IN ({placeholders})
            """
            ctx_params = {f"ctx_{i}": cid for i, cid in enumerate(top_context_ids)}
            ctx_rows = db.execute(text(ctx_sql), ctx_params).fetchall()
            rows = list(rows) + list(ctx_rows)

    if not rows:
        return [], None, "No movies found matching your criteria."

    candidate_ids = [row.id for row in rows]

    # ── Load archetype tags for candidates ──
    if candidate_ids:
        placeholders = ",".join([f":id_{i}" for i in range(len(candidate_ids))])
        tag_sql = f"""
            SELECT movie_id, archetype, weight
            FROM emotional_archetype_tags
            WHERE movie_id IN ({placeholders})
        """
        tag_params = {f"id_{i}": cid for i, cid in enumerate(candidate_ids)}
        tag_rows = db.execute(text(tag_sql), tag_params).fetchall()
    else:
        tag_rows = []

    # Build archetype map
    archetype_map = {}
    for tr in tag_rows:
        if tr.movie_id not in archetype_map:
            archetype_map[tr.movie_id] = {}
        archetype_map[tr.movie_id][tr.archetype] = tr.weight

    # ── Determine if emotional re-ranking applies ──
    has_emotion = query_vector and any(v > 0 for v in query_vector.values())

    if has_emotion:
        # Blend with user vector if available
        if user_vector:
            beta = 0.25 if interaction_count <= 10 else 0.35
            final_vector = {
                a: (1 - beta) * query_vector.get(a, 0.0) +
                   beta * user_vector.get(a, 0.0)
                for a in ARCHETYPES
            }
            final_vector = normalize_vector(final_vector)
        else:
            final_vector = query_vector

        reference_vec = [final_vector.get(a, 0.0) for a in ARCHETYPES]
    else:
        final_vector = None
        reference_vec = None

    # ── Score candidates ──
    results = []
    for row in rows:
        R = row.vote_average or 0
        v = row.vote_count or 0

        weighted_rating = (
            (v / (v + M)) * R +
            (M / (v + M)) * global_c
        ) if v > 0 else global_c

        pop_score = min((row.popularity or 0) / 100, 10)
        base_score = (0.7 * weighted_rating) + (0.3 * pop_score)
        base_quality = base_score / 10

        movie_archetypes = archetype_map.get(row.id, {})

        if has_emotion and reference_vec:
            movie_vec = build_movie_vector(movie_archetypes)
            similarity = cosine_similarity(reference_vec, movie_vec)
            final_score = base_quality * (QUALITY_FLOOR + EMOTION_CEIL * similarity)
        else:
            similarity = 0.0
            final_score = base_quality

        # Rating soft boost
        normalized_rating = min(R / 10, 1.0)
        final_score *= (1 + 0.05 * normalized_rating)

        # Context boost (Layer 3)
        context_score = 0.0
        has_context_match = False
        if context_scores and row.id in context_scores:
            context_score = context_scores[row.id]
            has_context_match = True
            final_score *= (1 + CONTEXT_BOOST * context_score)

        # Dominant archetype
        dominant_archetype = None
        if movie_archetypes:
            dominant_archetype = max(movie_archetypes, key=movie_archetypes.get)

        # Explanation
        explanation = []
        if has_emotion and final_vector:
            explanation = build_explanation(movie_archetypes, query_vector, user_vector, final_vector)
        if has_context_match:
            explanation.append(f"📖 Story match: {context_score:.0%} relevance")

        results.append({
            "id": row.id,
            "title": row.title,
            "final_score": round(final_score, 4),
            "base_score": round(base_quality, 4),
            "emotional_weight": round(similarity, 4),
            "poster_path": row.poster_path,
            "similarity_score": round(similarity, 4),
            "dominant_archetype": dominant_archetype,
            "explanation": explanation,
            "context_match": has_context_match,
        })

    # Sort by final score
    sort_by = intent.get("sort_by")
    if sort_by == "worst":
        results.sort(key=lambda x: x["final_score"])
    elif sort_by == "random":
        pass  # Already random from SQL
    else:
        results.sort(key=lambda x: x["final_score"], reverse=True)

    # ── Build explanation text ──
    filter_parts = []
    if intent.get("person_name"):
        filter_parts.append(f"featuring {intent['person_name']}")
    if intent.get("language"):
        filter_parts.append(f"in {intent['language']}")
    if intent.get("country"):
        filter_parts.append(f"from {intent['country']}")
    if intent.get("keyword"):
        filter_parts.append(f"about '{intent['keyword']}'")
    if intent.get("certification"):
        filter_parts.append(f"rated {intent['certification']}")
    if sort_by:
        sort_labels = {
            "best": "sorted by highest rating",
            "worst": "sorted by lowest rating",
            "trending": "sorted by trending",
            "random": "randomized selection",
            "hidden_gems": "hidden gems (high rating, low vote count)",
        }
        filter_parts.append(sort_labels.get(sort_by, ""))

    if has_emotion and final_vector:
        dominant = max(final_vector, key=final_vector.get)
        filter_parts.append(f"re-ranked by '{dominant}' emotional alignment")

    explanation_text = f"Showing {len(results)} movies " + ", ".join(filter_parts) + "." if filter_parts else f"Showing {len(results)} movies."

    return results, final_vector, explanation_text
