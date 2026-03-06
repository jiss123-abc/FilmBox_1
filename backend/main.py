from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import time
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Absolute imports for package reliability
from .database import SessionLocal
from .scoring import get_recommendations, get_vector_recommendations, compute_user_vector
from .models import RecommendationResponse, ErrorResponse, InteractionRequest, InteractionResponse, ProfileResponse
from .intent_classifier import classify_archetype, classify_emotional_vector
from .tmdb_service import search_movie, fetch_movie_details
from .archetype_tagger import tag_movie, ARCHETYPES as TAG_ARCHETYPES


app = FastAPI(title="FILMBOX API")

# CORS — Allow frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ARCHETYPES = [
    "mind_bending",
    "dark",
    "emotional",
    "inspirational",
    "adrenaline",
    "light"
]

GLOBAL_C = 0.0


# -------------------------
# Startup: Cache Global C
# -------------------------
@app.on_event("startup")
def compute_global_average():
    global GLOBAL_C
    db = SessionLocal()
    try:
        GLOBAL_C = db.execute(
            text("SELECT AVG(vote_average) FROM movies")
        ).scalar() or 6.5
        print(f"FILMBOX Backend v2.0 | 6D Vector Scoring | Global C: {GLOBAL_C:.4f}")
    finally:
        db.close()


# -------------------------
# Dependency
# -------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------
# Middleware: Performance Logging
# -------------------------
@app.middleware("http")
async def log_request_time(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    print(f"{request.method} {request.url.path} took {duration:.4f}s")
    return response


# -------------------------
# Health Endpoint
# -------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


# -------------------------
# Recommendation Endpoint (Single Archetype — Backward Compatible)
# -------------------------
@app.get(
    "/recommend",
    response_model=RecommendationResponse,
    responses={400: {"model": ErrorResponse}}
)
def recommend(
    archetype: str,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):

    if archetype not in ARCHETYPES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_ARCHETYPE",
                "allowed_values": ARCHETYPES
            }
        )

    results = get_recommendations(db, archetype, GLOBAL_C)

    paginated = results[offset: offset + limit]

    return {
        "archetype": archetype,
        "count": len(paginated),
        "results": paginated
    }


# -------------------------
# AI Exploration Endpoint (6D Vector Scoring)
# -------------------------
@app.get("/explore", response_model=RecommendationResponse)
def explore(
    query: str,
    limit: int = 20,
    offset: int = 0,
    x_session_id: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Natural Language -> 6D Emotional Vector -> Cosine Similarity Scoring.
    
    Ex: /explore?query=existential psychological thriller
    Ex: /explore?query=dark but hopeful
    Ex: /explore?query=light and fun
    """
    # 1. Convert query to 6D emotional vector via LLM
    query_vector = classify_emotional_vector(query)

    # 2. Check if we got a valid vector (not all zeros)
    has_signal = any(v > 0 for v in query_vector.values())

    if has_signal:
        # 3a. Personalization: compute user vector if session exists
        user_vector, interaction_count = compute_user_vector(db, x_session_id) if x_session_id else (None, 0)

        # 3b. Score using cosine similarity
        results, final_vector = get_vector_recommendations(db, query_vector, GLOBAL_C, user_vector, interaction_count)

        # Find dominant archetype for display
        dominant = max(final_vector, key=final_vector.get)
        explanation = (
            f"Emotional vector analysis: "
            f"Dominant vibe is '{dominant}'. "
            f"Scoring {len(results)} films by emotional alignment."
        )
    else:
        # 3c. Fallback to global quality ranking
        # Using 'Blockbuster' as a proxy for high-quality global leaders if no signal
        results = get_recommendations(db, "Blockbuster", GLOBAL_C)
        dominant = "Global Best"
        final_vector = query_vector
        explanation = (
            "Could not detect a specific emotional vibe. "
            "Showing global quality leaders."
        )

    paginated = results[offset: offset + limit]

    return {
        "archetype": dominant,
        "count": len(paginated),
        "results": paginated,
        "emotional_vector": final_vector,
        "explanation": explanation
    }


# -------------------------
# Interactions Endpoint
# -------------------------
@app.post("/interactions", response_model=InteractionResponse)
def record_interaction(
    req: InteractionRequest,
    db: Session = Depends(get_db)
):
    query = text("""
        INSERT INTO user_interactions (session_id, movie_id, action)
        VALUES (:session_id, :movie_id, :action)
    """)
    db.execute(query, {
        "session_id": req.session_id,
        "movie_id": req.movie_id,
        "action": req.action
    })
    db.commit()
    return {"status": "recorded"}


# -------------------------
# User Profile Endpoint
# -------------------------
@app.get("/profile", response_model=ProfileResponse)
def get_profile(
    x_session_id: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Returns the user's computed interaction count and normalized taste vector 
    (the centroid of their interactions). Used for the frontend memory profile UI.
    """
    if not x_session_id:
        return {"interaction_count": 0, "taste_vector": None}

    user_vector, interaction_count = compute_user_vector(db, x_session_id)

    if not user_vector:
        return {"interaction_count": interaction_count, "taste_vector": None, "top_archetypes": None}

    # Normalize vector defensively
    import math
    norm = math.sqrt(sum(v * v for v in user_vector.values()))
    if norm > 0:
        user_vector = {k: v / norm for k, v in user_vector.items()}

    # Server-side sorting and rounding
    top_archetypes = [
        {"name": k, "score": round(v, 2)}
        for k, v in user_vector.items()
    ]
    top_archetypes.sort(key=lambda x: x["score"], reverse=True)

    taste_vector = {k: round(v, 2) for k, v in user_vector.items()}

    return {
        "interaction_count": interaction_count,
        "taste_vector": taste_vector,
        "top_archetypes": top_archetypes
    }


# -------------------------
# TMDb Live Search Endpoint
# -------------------------
@app.get("/search")
def search_tmdb(
    query: str,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Search TMDb for movies by title.
    Auto-imports results into the local database with hybrid archetype tagging.
    Returns imported movies with their archetype vectors.
    """
    # 1. Search TMDb
    tmdb_results = search_movie(query)
    if not tmdb_results:
        return {"query": query, "count": 0, "results": []}

    imported = []

    for tmdb_movie in tmdb_results[:limit]:
        tmdb_id = tmdb_movie.get("id")
        title = tmdb_movie.get("title", "Unknown")

        # 2. Check if already in DB
        existing = db.execute(
            text("SELECT id, title FROM movies WHERE tmdb_id = :tmdb_id"),
            {"tmdb_id": tmdb_id}
        ).fetchone()

        if existing:
            imported.append({"id": existing.id, "title": existing.title, "status": "exists"})
            continue

        # 3. Fetch full details from TMDb
        details = fetch_movie_details(tmdb_id)
        if not details:
            continue

        # 4. Insert into movies table
        db.execute(
            text("""
                INSERT INTO movies (title, overview, release_year, runtime, popularity,
                                    vote_average, vote_count, poster_path, backdrop_path, tmdb_id)
                VALUES (:title, :overview, :year, :runtime, :popularity,
                        :vote_avg, :vote_cnt, :poster, :backdrop, :tmdb_id)
            """),
            {
                "title": details["title"],
                "overview": details["overview"],
                "year": details["release_year"],
                "runtime": details["runtime"],
                "popularity": details["popularity"],
                "vote_avg": details["vote_average"],
                "vote_cnt": details["vote_count"],
                "poster": details["poster_path"],
                "backdrop": details["backdrop_path"],
                "tmdb_id": details["tmdb_id"]
            }
        )
        db.commit()

        # Get the new movie ID
        new_row = db.execute(
            text("SELECT id FROM movies WHERE tmdb_id = :tmdb_id"),
            {"tmdb_id": tmdb_id}
        ).fetchone()

        if not new_row:
            continue

        movie_id = new_row.id

        # 5. Hybrid tagging
        vector = tag_movie(
            title=details["title"],
            overview=details["overview"],
            genres=details["genres"],
            keywords=details["keywords"],
            popularity=details["popularity"],
            runtime=details["runtime"] or 0
        )

        # 6. Store archetype tags
        for archetype in TAG_ARCHETYPES:
            weight = vector.get(archetype, 0.0)
            if weight > 0.05:
                db.execute(
                    text("""
                        INSERT OR REPLACE INTO emotional_archetype_tags (movie_id, archetype, weight)
                        VALUES (:mid, :arch, :weight)
                    """),
                    {"mid": movie_id, "arch": archetype, "weight": round(weight, 4)}
                )
        db.commit()

        imported.append({
            "id": movie_id,
            "title": details["title"],
            "year": details["release_year"],
            "poster_path": details["poster_path"],
            "archetypes": {k: round(v, 2) for k, v in vector.items()},
            "status": "imported"
        })

    return {
        "query": query,
        "count": len(imported),
        "results": imported
    }
