"""
FILMBOX — Query Builder (Phase 8)

Unified pipeline: Structured Intent → SQL Filters → Candidates → Emotional Re-ranking

Takes structured JSON from the intent classifier and builds dynamic SQL queries
combining filters for: person, language, country, keyword, certification, rating.
Then applies emotional vector scoring on the filtered candidates.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session
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
                      context_scores: dict = None, title_scores: dict = None) -> tuple:
    """
    Full discovery pipeline:
        1. Build SQL from structured filters
        2. Fetch candidate movies
        3. Load archetype tags for candidates
        4. Apply emotional re-ranking (if vector present)
        5. Apply context boost (if context_scores present)
        6. Apply title boost (if title_scores present)
        7. Return scored results + metadata

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

    # ── Merge title-matched candidates into the pool ──
    if title_scores:
        existing_ids = {row.id for row in rows}
        title_only_ids = [mid for mid in title_scores if mid not in existing_ids]

        if title_only_ids:
            placeholders = ",".join([f":t_id_{i}" for i in range(len(title_only_ids))])
            t_sql = f"""
                SELECT id, title, overview, vote_average, vote_count,
                       popularity, poster_path, release_year, runtime
                FROM movies
                WHERE id IN ({placeholders})
            """
            t_params = {f"t_id_{i}": cid for i, cid in enumerate(title_only_ids)}
            t_rows = db.execute(text(t_sql), t_params).fetchall()
            rows = list(rows) + list(t_rows)

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

        # Title boost (Direct Priority Match)
        if title_scores and row.id in title_scores:
            title_score = title_scores[row.id]
            # Massive boost (5x) to guarantee exact movie titles stay at the top
            final_score *= (1 + 5.0 * title_score)

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


# -------------------------
# Similar Movies (2-hop Graph Walk)
# -------------------------

# Weights for similarity scoring
SIMILAR_WEIGHTS = {
    "director": 5,
    "actor": 2,
    "genre": 2,
    "keyword": 1,
}

# Cap on seed cast to prevent popular-actor explosion (e.g. Samuel L. Jackson)
SEED_CAST_LIMIT = 10


def get_similar_movies(db, seed_id: int, limit: int = 10, min_votes: int = 100, include_explanations: bool = True) -> dict:
    """
    Finds movies sharing director, cast, genres, and keywords with a seed movie.
    Uses a 2-hop CTE-based graph walk for performance.
    """
    # 1. Fetch seed movie details and vote count for dynamic sensitivity
    seed = db.execute(
        text("SELECT id, title, vote_count FROM movies WHERE id = :id"),
        {"id": seed_id}
    ).fetchone()

    if not seed:
        return {"seed_id": seed_id, "seed_title": "Unknown", "count": 0, "results": []}

    # Dynamic Sensitivity: If seed has few votes (regional/indie), lower the threshold.
    # Prevents empty results for films like Bramayugam.
    if seed.vote_count < min_votes:
        min_votes = max(10, int(seed.vote_count * 0.5))
        print(f"[Similarity] Lowered min_votes to {min_votes} for seed movie '{seed.title}' (votes: {seed.vote_count})")

    # 2. Main Similarity Query
    # Weights: Director=5, Actor=2, Genre=2, Keyword=1
    # Note: If seed has NO attributes, the query will correctly return 0 results due to the WHERE clause.
    sql = text("""
        WITH seed_cast AS (
            SELECT person_id FROM movie_credits
            WHERE movie_id = :seed_id AND role = 'actor'
            LIMIT 10
        ),
        seed_directors AS (
            SELECT person_id FROM movie_credits
            WHERE movie_id = :seed_id AND role = 'director'
        ),
        seed_genres AS (
            SELECT genre_id FROM movie_genres WHERE movie_id = :seed_id
        ),
        seed_keywords AS (
            SELECT keyword_id FROM movie_keywords WHERE movie_id = :seed_id
        )
        SELECT 
            m.id, m.title, m.poster_path, m.vote_average, m.popularity,
            CAST((
                COALESCE(dir_match.score, 0) + 
                COALESCE(cast_match.score, 0) + 
                COALESCE(genre_match.score, 0) + 
                COALESCE(kw_match.score, 0)
            ) AS FLOAT) AS similarity_score
        FROM movies m
        LEFT JOIN (
            SELECT mc.movie_id, COUNT(DISTINCT mc.person_id) * 5 as score
            FROM movie_credits mc
            WHERE mc.role = 'director' AND mc.person_id IN (SELECT person_id FROM seed_directors)
            GROUP BY mc.movie_id
        ) dir_match ON dir_match.movie_id = m.id
        LEFT JOIN (
            SELECT mc.movie_id, COUNT(DISTINCT mc.person_id) * 2 as score
            FROM movie_credits mc
            WHERE mc.role = 'actor' AND mc.person_id IN (SELECT person_id FROM seed_cast)
            GROUP BY mc.movie_id
        ) cast_match ON cast_match.movie_id = m.id
        LEFT JOIN (
            SELECT mg.movie_id, COUNT(DISTINCT mg.genre_id) * 2 as score
            FROM movie_genres mg
            WHERE mg.genre_id IN (SELECT genre_id FROM seed_genres)
            GROUP BY mg.movie_id
        ) genre_match ON genre_match.movie_id = m.id
        LEFT JOIN (
            SELECT mk.movie_id, COUNT(DISTINCT mk.keyword_id) * 1 as score
            FROM movie_keywords mk
            WHERE mk.keyword_id IN (SELECT keyword_id FROM seed_keywords)
            GROUP BY mk.movie_id
        ) kw_match ON kw_match.movie_id = m.id
        WHERE m.id != :seed_id
          AND m.vote_count >= :min_votes
          AND (COALESCE(dir_match.score, 0) > 0 OR COALESCE(cast_match.score, 0) > 0 OR COALESCE(genre_match.score, 0) > 0 OR COALESCE(kw_match.score, 0) > 0)
        ORDER BY similarity_score DESC, m.vote_average DESC, m.popularity DESC
        LIMIT :limit
    """)

    results = db.execute(sql, {"seed_id": seed_id, "min_votes": min_votes, "limit": limit}).fetchall()

    if not results:
        return {
            "seed_movie_id": seed.id,
            "seed_movie_title": seed.title,
            "count": 0,
            "results": [],
        }

    # 3. Batch explanation builder
    explanations = {}
    if include_explanations and results:
        candidate_ids = [r.id for r in results]
        explanations = _build_explanations_batch(db, seed_id, candidate_ids)

    # 4. Assemble response
    formatted_results = []
    for row in results:
        formatted_results.append({
            "id": row.id,
            "title": row.title,
            "poster_path": row.poster_path,
            "vote_average": row.vote_average,
            "popularity": row.popularity,
            "similarity_score": float(row.similarity_score),
            "explanation": explanations.get(row.id, []),
        })

    return {
        "seed_movie_id": seed.id,
        "seed_movie_title": seed.title,
        "count": len(formatted_results),
        "results": formatted_results,
    }




def _build_explanations_batch(db, seed_id: int, candidate_ids: list[int]) -> dict:
    """
    Batch-fetch human-readable explanation strings for all candidates at once.

    Returns: {movie_id: ["same director: X", "shared genre: Sci-Fi", ...]}
    """
    explanations = {cid: [] for cid in candidate_ids}

    # Build parameterized placeholders
    ph = ",".join([f":c_{i}" for i in range(len(candidate_ids))])
    id_params = {f"c_{i}": cid for i, cid in enumerate(candidate_ids)}
    base_params = {"seed_id": seed_id, **id_params}

    # -- Shared directors --
    dir_sql = text(f"""
        SELECT mc.movie_id, p.name
        FROM movie_credits mc
        JOIN people p ON p.id = mc.person_id
        WHERE mc.role = 'director'
          AND mc.movie_id IN ({ph})
          AND mc.person_id IN (
              SELECT person_id FROM movie_credits
              WHERE movie_id = :seed_id AND role = 'director'
          )
    """)
    for row in db.execute(dir_sql, base_params).fetchall():
        explanations[row.movie_id].append(f"same director: {row.name}")

    # -- Shared actors --
    act_sql = text(f"""
        SELECT mc.movie_id, p.name
        FROM movie_credits mc
        JOIN people p ON p.id = mc.person_id
        WHERE mc.role = 'actor'
          AND mc.movie_id IN ({ph})
          AND mc.person_id IN (
              SELECT person_id FROM movie_credits
              WHERE movie_id = :seed_id AND role = 'actor'
              ORDER BY cast_order ASC LIMIT {SEED_CAST_LIMIT}
          )
    """)
    actor_counts = {}
    for row in db.execute(act_sql, base_params).fetchall():
        actor_counts.setdefault(row.movie_id, []).append(row.name)

    for mid, names in actor_counts.items():
        if len(names) == 1:
            explanations[mid].append(f"shared actor: {names[0]}")
        else:
            explanations[mid].append(f"{len(names)} shared actors: {', '.join(names[:3])}")

    # -- Shared genres --
    gen_sql = text(f"""
        SELECT mg.movie_id, g.name
        FROM movie_genres mg
        JOIN genres g ON g.id = mg.genre_id
        WHERE mg.movie_id IN ({ph})
          AND mg.genre_id IN (
              SELECT genre_id FROM movie_genres WHERE movie_id = :seed_id
          )
    """)
    for row in db.execute(gen_sql, base_params).fetchall():
        explanations[row.movie_id].append(f"shared genre: {row.name}")

    # -- Shared keywords (cap at 3 per movie for readability) --
    kw_sql = text(f"""
        SELECT mk.movie_id, k.name
        FROM movie_keywords mk
        JOIN keywords k ON k.id = mk.keyword_id
        WHERE mk.movie_id IN ({ph})
          AND mk.keyword_id IN (
              SELECT keyword_id FROM movie_keywords WHERE movie_id = :seed_id
          )
    """)
    kw_map = {}
    for row in db.execute(kw_sql, base_params).fetchall():
        kw_map.setdefault(row.movie_id, []).append(row.name)

    for mid, kw_names in kw_map.items():
        if len(kw_names) <= 3:
            for kw in kw_names:
                explanations[mid].append(f"shared keyword: {kw}")
        else:
            explanations[mid].append(
                f"{len(kw_names)} shared keywords: {', '.join(kw_names[:3])}…"
            )
    return explanations
def _enrich_from_tmdb(db: Session, movie_id: int):
    """
    On-demand enrichment: Fetches credits, genres, keywords, and countries 
    from TMDb and persists them to the database. Uses a short timeout
    to avoid blocking the page load if TMDb is unreachable.
    """
    import os
    import threading
    import requests as req
    from dotenv import load_dotenv
    load_dotenv()

    tmdb_key = os.getenv("TMDB_API_KEY", "")
    if not tmdb_key:
        return

    row = db.execute(text("SELECT tmdb_id FROM movies WHERE id = :id"), {"id": movie_id}).first()
    if not row or not row.tmdb_id:
        return

    tmdb_id = row.tmdb_id
    print(f"[Enrich] Attempting fast TMDb fetch for movie {movie_id} (tmdb_id={tmdb_id})")

    # Use a direct HTTP call with 3-second timeout instead of the retry-heavy _tmdb_get
    try:
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
        resp = req.get(url, params={
            "api_key": tmdb_key,
            "language": "en-US",
            "append_to_response": "credits,keywords,release_dates"
        }, timeout=3)

        if resp.status_code != 200:
            print(f"[Enrich] TMDb returned {resp.status_code}, skipping")
            return

        data = resp.json()
    except Exception as e:
        print(f"[Enrich] TMDb unreachable ({type(e).__name__}), skipping enrichment")
        return

    try:
        # Parse raw TMDb API response directly (not the normalized fetch_movie_everything format)
        genres = [g["name"].lower() for g in data.get("genres", [])]
        credits_data = data.get("credits", {})
        keywords_data = data.get("keywords", {})
        keywords_list = [kw["name"].lower() for kw in keywords_data.get("keywords", [])]
        prod_countries = data.get("production_countries", [])

        # Helper: get or create a record and return its id
        def get_or_create(table, name_col, name_val, extra_cols=None):
            r = db.execute(text(f"SELECT id FROM {table} WHERE {name_col} = :name"), {"name": name_val}).first()
            if r:
                return r.id
            if extra_cols:
                cols = f"{name_col}, " + ", ".join(extra_cols.keys())
                placeholders = ":name, " + ", ".join(f":{k}" for k in extra_cols.keys())
                params = {"name": name_val, **extra_cols}
            else:
                cols = name_col
                placeholders = ":name"
                params = {"name": name_val}
            db.execute(text(f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({placeholders})"), params)
            r = db.execute(text(f"SELECT id FROM {table} WHERE {name_col} = :name"), {"name": name_val}).first()
            return r.id if r else None

        # Insert genres
        for genre_name in genres:
            genre_id = get_or_create("genres", "name", genre_name)
            if genre_id:
                db.execute(text("INSERT OR IGNORE INTO movie_genres (movie_id, genre_id) VALUES (:mid, :gid)"),
                           {"mid": movie_id, "gid": genre_id})

        # Insert keywords
        for kw_name in keywords_list:
            kw_id = get_or_create("keywords", "name", kw_name)
            if kw_id:
                db.execute(text("INSERT OR IGNORE INTO movie_keywords (movie_id, keyword_id) VALUES (:mid, :kid)"),
                           {"mid": movie_id, "kid": kw_id})

        # Insert cast (top 10)
        for actor in credits_data.get("cast", [])[:10]:
            person_id = get_or_create("people", "name", actor["name"], 
                                       {"tmdb_id": actor.get("id")})
            if person_id:
                db.execute(text("""
                    INSERT OR IGNORE INTO movie_credits (movie_id, person_id, role, character_name, cast_order)
                    VALUES (:mid, :pid, 'actor', :char, :ord)
                """), {"mid": movie_id, "pid": person_id, 
                       "char": actor.get("character", ""), "ord": actor.get("order", 99)})

        # Insert directors
        for crew in credits_data.get("crew", []):
            if crew.get("job") == "Director":
                person_id = get_or_create("people", "name", crew["name"],
                                           {"tmdb_id": crew.get("id")})
                if person_id:
                    db.execute(text("""
                        INSERT OR IGNORE INTO movie_credits (movie_id, person_id, role)
                        VALUES (:mid, :pid, 'director')
                    """), {"mid": movie_id, "pid": person_id})

        # Insert production countries
        for country in prod_countries:
            iso = country.get("iso_3166_1", "")
            if iso:
                country_id = get_or_create("countries", "name", country.get("name", ""),
                                            {"iso_code": iso})
                if country_id:
                    db.execute(text("INSERT OR IGNORE INTO movie_countries (movie_id, country_id) VALUES (:mid, :cid)"),
                               {"mid": movie_id, "cid": country_id})

        # Update language
        orig_lang = data.get("original_language")
        if orig_lang:
            lang = db.execute(text("SELECT id FROM languages WHERE iso_code = :code"), {"code": orig_lang}).first()
            if lang:
                db.execute(text("UPDATE movies SET language_id = :lid WHERE id = :mid"),
                           {"lid": lang.id, "mid": movie_id})

        db.commit()
        print(f"[Enrich] Successfully enriched movie {movie_id} with {len(genres)} genres, {len(keywords_list)} keywords")

    except Exception as e:
        print(f"[Enrich] Error enriching movie {movie_id}: {e}")
        db.rollback()


def get_movie_details(db: Session, movie_id: int) -> dict | None:
    """
    Retrieves full movie metadata by aggregating data from multiple tables.
    Auto-enriches from TMDb if credits are missing.
    """
    # 1. Fetch Core Metadata (Note: release_year mapped to release_date as TEXT)
    movie = db.execute(
        text("""
            SELECT id, title, overview, CAST(release_year AS TEXT) as release_date, 
                   runtime, poster_path, vote_average, vote_count, popularity
            FROM movies WHERE id = :id
        """),
        {"id": movie_id}
    ).mappings().first()

    if not movie:
        return None

    movie_dict = dict(movie)

    # 2. Check if credits exist — if not, auto-enrich from TMDb
    # NOTE: Commented out for local dev (TMDb unreachable). 
    # Uncomment when deployed to Render or when TMDb API is accessible.
    # credit_count = db.execute(
    #     text("SELECT COUNT(*) as cnt FROM movie_credits WHERE movie_id = :id"),
    #     {"id": movie_id}
    # ).first()
    # if credit_count and credit_count.cnt == 0:
    #     _enrich_from_tmdb(db, movie_id)

    # 3. Fetch Genres
    genres_sql = text("""
        SELECT g.id, g.name
        FROM movie_genres mg
        JOIN genres g ON g.id = mg.genre_id
        WHERE mg.movie_id = :id
        ORDER BY g.name
    """)
    genres = db.execute(genres_sql, {"id": movie_id}).mappings().all()

    # 4. Fetch Top 10 Cast (Aliasing character_name to character)
    cast_sql = text("""
        SELECT p.id, p.name, mc.character_name as character
        FROM movie_credits mc
        JOIN people p ON p.id = mc.person_id
        WHERE mc.movie_id = :id AND mc.role = 'actor'
        LIMIT 10
    """)
    cast = db.execute(cast_sql, {"id": movie_id}).mappings().all()

    # 5. Fetch Director
    director_sql = text("""
        SELECT p.id, p.name
        FROM movie_credits mc
        JOIN people p ON p.id = mc.person_id
        WHERE mc.movie_id = :id AND mc.role = 'director'
    """)
    director = db.execute(director_sql, {"id": movie_id}).mappings().first()

    # 6. Fetch Keywords
    keywords_sql = text("""
        SELECT k.id, k.name
        FROM movie_keywords mk
        JOIN keywords k ON k.id = mk.keyword_id
        WHERE mk.movie_id = :id
        ORDER BY k.name
    """)
    keywords = db.execute(keywords_sql, {"id": movie_id}).mappings().all()

    # 7. Fetch Production Countries
    countries_sql = text("""
        SELECT c.id, c.name
        FROM movie_countries mc
        JOIN countries c ON c.id = mc.country_id
        WHERE mc.movie_id = :id
        ORDER BY c.name
    """)
    countries = db.execute(countries_sql, {"id": movie_id}).mappings().all()

    # 8. Resolve Language Name and ISO Code
    lang_sql = text("""
        SELECT l.name, l.iso_code 
        FROM languages l
        JOIN movies m ON m.language_id = l.id
        WHERE m.id = :id
    """)
    lang_info = db.execute(lang_sql, {"id": movie_id}).mappings().first()
    
    language_name = lang_info['name'] if lang_info else None
    language_code = lang_info['iso_code'] if lang_info else None

    # Assemble final dict
    return {
        **movie_dict,
        "genres": [dict(r) for r in genres],
        "cast": [dict(r) for r in cast],
        "director": dict(director) if director else None,
        "keywords": [dict(r) for r in keywords],
        "countries": [dict(r) for r in countries],
        "language": language_name,
        "original_language": language_code
    }
