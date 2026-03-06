import os
import time
import requests
from typing import Optional

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
MAX_RETRIES = 5


def _tmdb_get(endpoint: str, params: dict = None) -> Optional[dict]:
    """
    Internal helper: makes a GET request to TMDb with retry + exponential backoff.
    Returns parsed JSON or None on failure.
    """
    if not TMDB_API_KEY:
        print("Error: TMDB_API_KEY not found in environment.")
        return None

    url = f"{TMDB_BASE_URL}{endpoint}"
    base_params = {"api_key": TMDB_API_KEY}
    if params:
        base_params.update(params)

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=base_params, timeout=10)

            if response.status_code == 200:
                return response.json()

            if response.status_code == 429:
                wait = 2 ** attempt
                print(f"  ⏳ Rate limited. Retrying in {wait}s...")
                time.sleep(wait)
                continue

            print(f"  ❌ TMDb error {response.status_code}: {response.text[:200]}")
            return None

        except requests.RequestException as e:
            wait = 2 ** attempt
            print(f"  ⚠ Request failed ({e}). Retrying in {wait}s...")
            time.sleep(wait)

    print(f"  ❌ TMDb request failed after {MAX_RETRIES} retries.")
    return None


def fetch_discover_page(page: int = 1, sort_by: str = "popularity.desc") -> list:
    """
    Fetch a page of movies from TMDb /discover/movie.
    Returns list of movie dicts or empty list.
    """
    data = _tmdb_get("/discover/movie", {
        "page": page,
        "sort_by": sort_by,
        "include_adult": "false",
        "language": "en-US"
    })

    if not data:
        return []

    return data.get("results", [])


def search_movie(query: str, page: int = 1) -> list:
    """
    Search TMDb by movie title.
    Returns list of movie results.
    """
    data = _tmdb_get("/search/movie", {
        "query": query,
        "page": page,
        "include_adult": "false",
        "language": "en-US"
    })

    if not data:
        return []

    return data.get("results", [])


def fetch_movie_details(tmdb_id: int) -> Optional[dict]:
    """
    Fetch full movie details including genres and keywords.
    Returns enriched movie dict or None.
    """
    # Get base details + keywords in one call using append_to_response
    data = _tmdb_get(f"/movie/{tmdb_id}", {
        "append_to_response": "keywords",
        "language": "en-US"
    })

    if not data:
        return None

    # Extract genre names
    genres = [g["name"].lower() for g in data.get("genres", [])]

    # Extract keyword names
    keywords_data = data.get("keywords", {})
    keywords = [kw["name"].lower() for kw in keywords_data.get("keywords", [])]

    return {
        "tmdb_id": data.get("id"),
        "title": data.get("title", "Unknown"),
        "overview": data.get("overview", ""),
        "genres": genres,
        "keywords": keywords,
        "release_year": int(data["release_date"][:4]) if data.get("release_date") else None,
        "runtime": data.get("runtime"),
        "popularity": data.get("popularity", 0),
        "vote_average": data.get("vote_average", 0),
        "vote_count": data.get("vote_count", 0),
        "poster_path": data.get("poster_path"),
        "backdrop_path": data.get("backdrop_path")
    }
