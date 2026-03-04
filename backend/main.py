from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
import time

# Absolute imports for package reliability
from .database import SessionLocal
from .scoring import get_recommendations
from .models import RecommendationResponse, ErrorResponse
from .intent_classifier import classify_archetype

app = FastAPI(title="FILMBOX API")

ARCHETYPES = [
    "Blockbuster",
    "Feel-Good",
    "Dark & Gritty",
    "Mind-Bending",
    "Emotional",
    "Comfort"
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
        print(f"🚀 FILMBOX Backend v1.0 | Global C Cached: {GLOBAL_C:.4f}")
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
# Recommendation Endpoint
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
# AI Exploration Endpoint
# -------------------------
@app.get("/explore", response_model=RecommendationResponse)
def explore(
    query: str,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Natural Language -> Intent Classifier -> Scoring Engine.
    Ex: /explore?query=I want to see something dark and psychological
    """
    # 1. Use AI to map query to archetype
    detected_archetype = classify_archetype(query)
    
    # 2. Call deterministic engine
    results = get_recommendations(db, detected_archetype, GLOBAL_C)
    paginated = results[offset: offset + limit]
    
    # 3. Formulate explanation
    vibe = detected_archetype if detected_archetype else "Global Best"
    if detected_archetype:
        explanation = f"AI detected a '{vibe}' vibe in your request. Showing highest quality matches."
    else:
        explanation = "We couldn't detect a specific emotional vibe, so we're showing the global quality leaders."

    return {
        "archetype": vibe,
        "count": len(paginated),
        "results": paginated,
        "explanation": explanation
    }
