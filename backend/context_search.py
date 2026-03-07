"""
FILMBOX — Context Search Engine (Layer 3)

Provides story-level search using SQLite FTS5 full-text search
over movie overviews, plus enhanced multi-keyword matching.

This enables queries like:
    "movies where the villain wins"
    "movies about time loops"
    "movies where people are trapped in one location"
"""

from sqlalchemy import text


# ---------------------
# FTS5 Index Management
# ---------------------

def ensure_fts_index(db):
    """
    Creates an enriched FTS5 virtual table populated from existing movies,
    including their overviews, keywords, and genres for superior semantic matching.
    """
    exists = db.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='movies_fts'")
    ).fetchone()

    if exists:
        count = db.execute(text("SELECT COUNT(*) FROM movies_fts")).scalar()
        if count > 0:
            print(f"[Context Search] FTS index already exists with {count} entries.")
            return
        else:
            db.execute(text("DROP TABLE IF EXISTS movies_fts"))
            db.commit()

    # Create a standard FTS5 table (not externally content-linked because we are
    # injecting joined data from keywords and genres tables)
    db.execute(text("""
        CREATE VIRTUAL TABLE movies_fts USING fts5(
            title,
            overview,
            keywords_genres
        )
    """))
    db.commit()

    print("[Context Search] Building enriched semantic FTS index (this may take a moment)...")
    
    # Populate the FTS index joining overviews + keywords + genres into one searchable block
    db.execute(text("""
        INSERT INTO movies_fts(rowid, title, overview, keywords_genres)
        SELECT 
            m.id, 
            m.title, 
            m.overview,
            (
                SELECT IFNULL(GROUP_CONCAT(k.name, ' '), '') 
                FROM movie_keywords mk 
                JOIN keywords k ON k.id = mk.keyword_id 
                WHERE mk.movie_id = m.id
            ) || ' ' ||
            (
                SELECT IFNULL(GROUP_CONCAT(g.name, ' '), '') 
                FROM movie_genres mg 
                JOIN genres g ON g.id = mg.genre_id 
                WHERE mg.movie_id = m.id
            ) AS keywords_genres
        FROM movies m
        WHERE m.overview IS NOT NULL AND m.overview != ''
    """))
    db.commit()

    final_count = db.execute(text("SELECT COUNT(*) FROM movies_fts")).scalar()
    print(f"[Context Search] FTS index ready — {final_count} movies indexed with semantic enrichment.")


# ---------------------
# Context Search (FTS5)
# ---------------------

def search_by_context(db, context_query: str, limit: int = 500) -> dict:
    """
    Runs FTS5 full-text search against movie overviews using BM25 ranking.

    Args:
        db: SQLAlchemy session
        context_query: Natural language story/plot search phrase
        limit: Max results to return

    Returns:
        dict of {movie_id: normalized_relevance_score} (0.0 to 1.0)
    """
    if not context_query or not context_query.strip():
        return {}

    # Sanitize the query for FTS5:
    # - Remove special FTS5 operators that could cause syntax errors
    # - Split into individual words and join with implicit AND
    words = []
    for word in context_query.strip().split():
        # Remove FTS5 special characters
        clean = word.strip('"\'*(){}[]^~')
        if clean and len(clean) > 1:  # Skip single-char words
            words.append(f'"{clean}"')  # Quote each word for exact term matching

    if not words:
        return {}

    fts_query = " OR ".join(words)  # OR for broader recall

    try:
        rows = db.execute(
            text("""
                SELECT rowid, bm25(movies_fts) AS score
                FROM movies_fts
                WHERE movies_fts MATCH :query
                ORDER BY bm25(movies_fts)
                LIMIT :limit
            """),
            {"query": fts_query, "limit": limit}
        ).fetchall()
    except Exception as e:
        print(f"[Context Search] FTS query error: {e}")
        return {}

    if not rows:
        return {}

    # BM25 scores from SQLite are negative (lower = better match).
    # Normalize to 0-1 range (1.0 = best match).
    raw_scores = {row.rowid: row.score for row in rows}

    min_score = min(raw_scores.values())  # Most negative = best
    max_score = max(raw_scores.values())  # Least negative = worst
    score_range = max_score - min_score

    if score_range == 0:
        # All scores are identical — assign uniform relevance
        return {mid: 1.0 for mid in raw_scores}

    normalized = {}
    for movie_id, score in raw_scores.items():
        # Invert: min_score (best BM25) → 1.0, max_score (worst BM25) → 0.0
        normalized[movie_id] = (max_score - score) / score_range

    return normalized


# --------------------------------
# Enhanced Multi-Keyword Matching
# --------------------------------

def search_by_keywords_multi(db, keywords_list: list) -> dict:
    """
    Matches movies against multiple keyword terms simultaneously.

    Args:
        db: SQLAlchemy session
        keywords_list: List of keyword strings to search for (e.g., ["revenge", "betrayal"])

    Returns:
        dict of {movie_id: match_ratio} where match_ratio = matched_keywords / total_keywords
    """
    if not keywords_list:
        return {}

    # Build LIKE conditions for each keyword
    conditions = []
    params = {}
    for i, kw in enumerate(keywords_list):
        param_name = f"kw_{i}"
        conditions.append(f"LOWER(k.name) LIKE :{param_name}")
        params[param_name] = f"%{kw.lower().strip()}%"

    # Find movies matching ANY of the keywords, counting how many match
    keyword_filter = " OR ".join(conditions)
    sql = f"""
        SELECT mk.movie_id, COUNT(DISTINCT k.id) AS match_count
        FROM movie_keywords mk
        JOIN keywords k ON k.id = mk.keyword_id
        WHERE {keyword_filter}
        GROUP BY mk.movie_id
    """

    try:
        rows = db.execute(text(sql), params).fetchall()
    except Exception as e:
        print(f"[Context Search] Keyword search error: {e}")
        return {}

    if not rows:
        return {}

    total_keywords = len(keywords_list)
    return {row.movie_id: min(row.match_count / total_keywords, 1.0) for row in rows}
