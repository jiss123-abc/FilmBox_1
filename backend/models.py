from pydantic import BaseModel
from typing import List, Optional, Dict


class MovieRecommendation(BaseModel):
    id: int
    title: str
    final_score: float
    base_score: float
    emotional_weight: float
    similarity_score: float = 0.0
    poster_path: Optional[str] = None
    dominant_archetype: Optional[str] = None
    explanation: Optional[List[str]] = None

    class Config:
        from_attributes = True


class RecommendationResponse(BaseModel):
    archetype: str
    count: int
    results: List[MovieRecommendation]
    emotional_vector: Optional[Dict[str, float]] = None
    explanation: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    allowed_values: Optional[List[str]] = None


class InteractionRequest(BaseModel):
    session_id: str
    movie_id: int
    action: str


class InteractionResponse(BaseModel):
    status: str

class TopArchetype(BaseModel):
    name: str
    score: float

class ProfileResponse(BaseModel):
    interaction_count: int
    taste_vector: Optional[Dict[str, float]] = None
    top_archetypes: Optional[List[TopArchetype]] = None


class SimilarMovieResult(BaseModel):
    id: int
    title: str
    poster_path: Optional[str] = None
    vote_average: float
    popularity: float
    similarity_score: float
    explanation: List[str] = []


class SimilarMoviesResponse(BaseModel):
    seed_movie_id: int
    seed_movie_title: str
    count: int
    results: List[SimilarMovieResult]


# --- Movie Details Models ---

class Genre(BaseModel):
    id: int
    name: str

class CastMember(BaseModel):
    id: int
    name: str
    character: str

class Director(BaseModel):
    id: int
    name: str

class Keyword(BaseModel):
    id: int
    name: str

class Country(BaseModel):
    id: int
    name: str

class MovieDetailsResponse(BaseModel):
    id: int
    title: str
    overview: Optional[str] = None
    release_date: Optional[str] = None
    runtime: Optional[int] = None
    poster_path: Optional[str] = None
    vote_average: float
    vote_count: int
    popularity: float
    original_language: Optional[str] = None
    genres: List[Genre]
    director: Optional[Director] = None
    cast: List[CastMember]
    keywords: List[Keyword]
    countries: List[Country]
    language: Optional[str] = None
