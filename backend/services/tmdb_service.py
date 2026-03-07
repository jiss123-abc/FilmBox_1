"""
FILMBOX — TMDb Service Layer

Handles all TMDb API requests with retry logic and rate limit management.
Returns normalized JSON objects ready for database insertion.

Functions:
    fetch_discover_page(page) -> list of movie summaries
    fetch_movie_details(tmdb_id) -> full movie dict
    fetch_movie_credits(tmdb_id) -> { cast: [...], crew: [...] }
    fetch_movie_keywords(tmdb_id) -> list of keyword strings
"""

import os
import time
import requests
from typing import Optional, List, Dict

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
BASE_URL = "https://api.themoviedb.org/3"
MAX_RETRIES = 5
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


# ─── Internal HTTP helper ───

def _tmdb_get(endpoint: str, params: dict = None) -> Optional[dict]:
    """
    GET request to TMDb with exponential backoff retry.
    Returns parsed JSON or None on failure.
    """
    if not TMDB_API_KEY:
        print("  ❌ TMDB_API_KEY not found in environment.")
        return None

    url = f"{BASE_URL}{endpoint}"
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

            print(f"  ❌ TMDb {response.status_code}: {response.text[:200]}")
            return None

        except requests.RequestException as e:
            wait = 2 ** attempt
            print(f"  ⚠ Request failed ({e}). Retrying in {wait}s...")
            time.sleep(wait)

    print(f"  ❌ TMDb request failed after {MAX_RETRIES} retries.")
    return None


# ─── Public API Functions ───

def fetch_discover_page(page: int = 1, sort_by: str = "popularity.desc") -> list:
    """
    Fetch a page of movies from TMDb /discover/movie.
    Each page = 20 movies. Returns list of movie summary dicts.
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


def fetch_movie_details(tmdb_id: int) -> Optional[dict]:
    """
    Fetch full movie details including genres and production info.
    Returns normalized movie dict or None.
    """
    data = _tmdb_get(f"/movie/{tmdb_id}", {
        "language": "en-US"
    })

    if not data:
        return None

    # Extract genre names
    genres = [g["name"].lower() for g in data.get("genres", [])]

    # Extract production countries
    prod_countries = [
        {"name": c.get("name", ""), "iso_code": c.get("iso_3166_1", "")}
        for c in data.get("production_countries", [])
    ]

    # Extract release year
    release_date = data.get("release_date", "")
    release_year = int(release_date[:4]) if release_date and len(release_date) >= 4 else None

    return {
        "tmdb_id": data.get("id"),
        "title": data.get("title", "Unknown"),
        "overview": data.get("overview", ""),
        "genres": genres,
        "release_year": release_year,
        "runtime": data.get("runtime"),
        "popularity": data.get("popularity", 0),
        "vote_average": data.get("vote_average", 0),
        "vote_count": data.get("vote_count", 0),
        "poster_path": data.get("poster_path"),
        "backdrop_path": data.get("backdrop_path"),
        "original_language": data.get("original_language", "en"),
        "production_countries": prod_countries,
    }


def fetch_movie_credits(tmdb_id: int) -> Optional[dict]:
    """
    Fetch cast and crew for a movie.
    Returns { cast: [top 10], directors: [...] } or None.
    """
    data = _tmdb_get(f"/movie/{tmdb_id}/credits")

    if not data:
        return None

    # Top 10 cast members
    cast = []
    for person in data.get("cast", [])[:10]:
        cast.append({
            "tmdb_id": person.get("id"),
            "name": person.get("name", "Unknown"),
            "character": person.get("character", ""),
            "order": person.get("order", 99),
            "profile_path": person.get("profile_path"),
        })

    # All directors from crew
    directors = []
    for person in data.get("crew", []):
        if person.get("job") == "Director":
            directors.append({
                "tmdb_id": person.get("id"),
                "name": person.get("name", "Unknown"),
                "profile_path": person.get("profile_path"),
            })

    return {"cast": cast, "directors": directors}


def fetch_movie_everything(tmdb_id: int) -> Optional[dict]:
    """
    ULTRA OPTIMIZED (Phase 9): Fetches details, credits, keywords, and certifications 
    all in a single API call using append_to_response.
    Returns the unified dictionary.
    """
    data = _tmdb_get(f"/movie/{tmdb_id}", {
        "language": "en-US",
        "append_to_response": "credits,keywords,release_dates"
    })

    if not data:
        return None

    # 1. Parse details
    genres = [g["name"].lower() for g in data.get("genres", [])]
    prod_countries = [
        {"name": c.get("name", ""), "iso_code": c.get("iso_3166_1", "")}
        for c in data.get("production_countries", [])
    ]
    release_date = data.get("release_date", "")
    release_year = int(release_date[:4]) if release_date and len(release_date) >= 4 else None

    details = {
        "tmdb_id": data.get("id"),
        "title": data.get("title", "Unknown"),
        "overview": data.get("overview", ""),
        "genres": genres,
        "release_year": release_year,
        "runtime": data.get("runtime"),
        "popularity": data.get("popularity", 0),
        "vote_average": data.get("vote_average", 0),
        "vote_count": data.get("vote_count", 0),
        "poster_path": data.get("poster_path"),
        "backdrop_path": data.get("backdrop_path"),
        "original_language": data.get("original_language", "en"),
        "production_countries": prod_countries,
    }

    # 2. Parse credits
    credits_data = data.get("credits", {})
    cast = []
    for person in credits_data.get("cast", [])[:10]:
        cast.append({
            "tmdb_id": person.get("id"),
            "name": person.get("name", "Unknown"),
            "character": person.get("character", ""),
            "order": person.get("order", 99),
            "profile_path": person.get("profile_path"),
        })

    directors = []
    for person in credits_data.get("crew", []):
        if person.get("job") == "Director":
            directors.append({
                "tmdb_id": person.get("id"),
                "name": person.get("name", "Unknown"),
                "profile_path": person.get("profile_path"),
            })
    parsed_credits = {"cast": cast, "directors": directors}

    # 3. Parse keywords
    keywords_data = data.get("keywords", {})
    parsed_keywords = [kw["name"].lower() for kw in keywords_data.get("keywords", [])]

    # 4. Parse certification
    certification = None
    for country in data.get("release_dates", {}).get("results", []):
        if country.get("iso_3166_1") == "US":
            for release in country.get("release_dates", []):
                cert = release.get("certification", "").strip()
                if cert:
                    certification = cert
                    break
            if certification:
                break

    return {
        "tmdb_id": tmdb_id,
        "details": details,
        "credits": parsed_credits,
        "keywords": parsed_keywords,
        "certification": certification
    }


def fetch_movie_keywords(tmdb_id: int) -> List[str]:
    """
    Fetch keywords for a movie.
    Returns list of keyword strings.
    """
    data = _tmdb_get(f"/movie/{tmdb_id}/keywords")

    if not data:
        return []

    return [kw["name"].lower() for kw in data.get("keywords", [])]


def fetch_movie_certification(tmdb_id: int) -> Optional[str]:
    """
    Fetch the US (MPAA) certification for a movie.
    Returns rating string (G, PG, PG-13, R, NC-17) or None.
    """
    data = _tmdb_get(f"/movie/{tmdb_id}/release_dates")

    if not data:
        return None

    for country in data.get("results", []):
        if country.get("iso_3166_1") == "US":
            for release in country.get("release_dates", []):
                cert = release.get("certification", "").strip()
                if cert:
                    return cert

    return None


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
