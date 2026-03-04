from pydantic import BaseModel
from typing import List, Optional

class MovieRecommendation(BaseModel):
    id: int
    title: str
    final_score: float
    base_score: float
    emotional_weight: float

    class Config:
        from_attributes = True

class RecommendationResponse(BaseModel):
    archetype: str
    count: int
    results: List[MovieRecommendation]

class ErrorResponse(BaseModel):
    error: str
    allowed_values: Optional[List[str]] = None
