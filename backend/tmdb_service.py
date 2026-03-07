"""
FILMBOX — TMDb Service (Backward Compatibility Shim)

Re-exports from the new service layer location.
Existing code importing from backend.tmdb_service will continue to work.
"""

from backend.services.tmdb_service import (
    fetch_discover_page,
    fetch_movie_details,
    fetch_movie_credits,
    fetch_movie_keywords,
    fetch_movie_certification,
    search_movie,
    _tmdb_get,
)

__all__ = [
    "fetch_discover_page",
    "fetch_movie_details",
    "fetch_movie_credits",
    "fetch_movie_keywords",
    "fetch_movie_certification",
    "search_movie",
]
