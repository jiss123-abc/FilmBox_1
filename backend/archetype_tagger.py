import os
import json
import math
from typing import Dict, List, Optional
from groq import Groq

# The 6 archetypes used throughout FILMBOX
ARCHETYPES = [
    "mind_bending",
    "dark",
    "emotional",
    "inspirational",
    "adrenaline",
    "light"
]

# ─── Genre → Archetype Scoring Matrix ───
# Adapted from generate_emotional_tags.py for the current 6D archetype space.
GENRE_MATRIX = {
    "action":            {"mind_bending": 0.2, "dark": 0.4, "emotional": 0.0, "inspirational": 0.1, "adrenaline": 0.9, "light": 0.0},
    "adventure":         {"mind_bending": 0.2, "dark": 0.1, "emotional": 0.2, "inspirational": 0.7, "adrenaline": 0.6, "light": 0.3},
    "comedy":            {"mind_bending": 0.1, "dark": 0.0, "emotional": 0.3, "inspirational": 0.2, "adrenaline": 0.0, "light": 0.9},
    "drama":             {"mind_bending": 0.2, "dark": 0.4, "emotional": 0.9, "inspirational": 0.3, "adrenaline": 0.0, "light": 0.2},
    "thriller":          {"mind_bending": 0.8, "dark": 0.6, "emotional": 0.2, "inspirational": 0.0, "adrenaline": 0.7, "light": 0.0},
    "mystery":           {"mind_bending": 0.9, "dark": 0.5, "emotional": 0.2, "inspirational": 0.0, "adrenaline": 0.3, "light": 0.0},
    "horror":            {"mind_bending": 0.4, "dark": 0.9, "emotional": 0.2, "inspirational": 0.0, "adrenaline": 0.5, "light": 0.0},
    "fantasy":           {"mind_bending": 0.5, "dark": 0.2, "emotional": 0.3, "inspirational": 0.6, "adrenaline": 0.3, "light": 0.4},
    "science fiction":   {"mind_bending": 0.8, "dark": 0.3, "emotional": 0.2, "inspirational": 0.3, "adrenaline": 0.5, "light": 0.1},
    "romance":           {"mind_bending": 0.1, "dark": 0.0, "emotional": 0.8, "inspirational": 0.3, "adrenaline": 0.0, "light": 0.6},
    "war":               {"mind_bending": 0.3, "dark": 0.8, "emotional": 0.6, "inspirational": 0.4, "adrenaline": 0.6, "light": 0.0},
    "crime":             {"mind_bending": 0.6, "dark": 0.9, "emotional": 0.5, "inspirational": 0.0, "adrenaline": 0.4, "light": 0.0},
    "animation":         {"mind_bending": 0.2, "dark": 0.1, "emotional": 0.4, "inspirational": 0.5, "adrenaline": 0.2, "light": 0.7},
    "family":            {"mind_bending": 0.1, "dark": 0.0, "emotional": 0.3, "inspirational": 0.6, "adrenaline": 0.1, "light": 0.8},
    "documentary":       {"mind_bending": 0.4, "dark": 0.3, "emotional": 0.5, "inspirational": 0.5, "adrenaline": 0.1, "light": 0.2},
    "history":           {"mind_bending": 0.3, "dark": 0.4, "emotional": 0.6, "inspirational": 0.5, "adrenaline": 0.2, "light": 0.1},
    "music":             {"mind_bending": 0.1, "dark": 0.1, "emotional": 0.6, "inspirational": 0.7, "adrenaline": 0.1, "light": 0.5},
    "western":           {"mind_bending": 0.2, "dark": 0.6, "emotional": 0.3, "inspirational": 0.2, "adrenaline": 0.7, "light": 0.0},
    "tv movie":          {"mind_bending": 0.1, "dark": 0.1, "emotional": 0.4, "inspirational": 0.3, "adrenaline": 0.1, "light": 0.5},
}

# ─── Keyword Boost Dictionaries ───
KEYWORD_BOOSTS = {
    "mind_bending":  ["dream", "parallel", "time travel", "time loop", "memory", "psychological",
                      "alternate reality", "conspiracy", "simulation", "perception", "subconscious"],
    "dark":          ["serial killer", "murder", "corruption", "revenge", "brutal", "mafia",
                      "assassin", "violence", "crime", "noir", "abuse", "torture"],
    "emotional":     ["family", "love", "loss", "relationship", "tragedy", "coming of age",
                      "grief", "terminal illness", "friendship", "divorce"],
    "inspirational": ["underdog", "triumph", "sports", "biography", "overcoming", "dream",
                      "hope", "courage", "perseverance", "redemption"],
    "adrenaline":    ["car chase", "explosion", "heist", "survival", "escape", "combat",
                      "martial arts", "gun", "spy", "hostage", "mercenary"],
    "light":         ["feel-good", "romantic comedy", "parody", "slapstick", "holiday",
                      "wedding", "road trip", "summer", "quirky", "satire"],
}

# Confidence threshold — if max dimension is below this, trigger LLM fallback
CONFIDENCE_THRESHOLD = 0.35


def _normalize_vector(vec: Dict[str, float]) -> Dict[str, float]:
    """L2-normalize a vector dict."""
    values = list(vec.values())
    norm = math.sqrt(sum(v * v for v in values))
    if norm == 0:
        return vec
    return {k: v / norm for k, v in vec.items()}


def tag_by_genre(
    genres: List[str],
    keywords: List[str] = None,
    popularity: float = 0,
    runtime: int = 0
) -> Dict[str, float]:
    """
    Rule-based archetype tagging using the genre matrix + keyword boosts.
    Cost: zero. Speed: instant.
    Returns a normalized 6D archetype vector.
    """
    scores = {a: 0.0 for a in ARCHETYPES}

    # 1. Genre matrix averaging
    matched_genres = [g for g in genres if g in GENRE_MATRIX]
    if matched_genres:
        for a in ARCHETYPES:
            total = sum(GENRE_MATRIX[g][a] for g in matched_genres)
            scores[a] = total / len(matched_genres)

    # 2. Keyword boosts (capped at +0.3 per archetype)
    if keywords:
        for a in ARCHETYPES:
            boost_words = KEYWORD_BOOSTS.get(a, [])
            matched = sum(1 for kw in keywords if any(bw in kw for bw in boost_words))
            scores[a] += min(0.3, matched * 0.1)

    # 3. Popularity modifier (adrenaline/inspirational boost for blockbusters)
    if popularity > 50:
        scores["adrenaline"] += 0.1

    # 4. Runtime modifier (mind_bending boost for long films)
    if runtime and runtime > 140:
        scores["mind_bending"] += 0.1

    # 5. Clamp and normalize
    scores = {a: min(1.0, v) for a, v in scores.items()}
    return _normalize_vector(scores)


def tag_by_llm(
    title: str,
    overview: str,
    genres: List[str]
) -> Optional[Dict[str, float]]:
    """
    LLM-based archetype tagging using Groq. Used as a fallback when
    rule-based tagging produces a low-confidence vector.
    Cost: ~220 tokens per call. Use sparingly.
    Returns a normalized 6D archetype vector or None on failure.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not found for LLM tagging.")
        return None

    client = Groq(api_key=api_key)

    genre_str = ", ".join(genres) if genres else "unknown"

    system_prompt = f"""You are an emotional analysis engine for a movie recommender called FILMBOX.

Your task: Given a movie's title, overview, and genres, assign scores from 0.0 to 1.0 for each of the 6 emotional archetypes.

The 6 archetypes are:
- mind_bending: Psychological complexity, twists, non-linear narrative, existential themes
- dark: Gritty, noir, moral tension, violence, crime, horror
- emotional: Character depth, drama, tearjerker, heartbreak, relationship-driven
- inspirational: Uplifting, comeback arcs, triumph, biopics, hope
- adrenaline: Action, intensity, fast-paced, thrillers, suspense, combat
- light: Feel-good, comedy, wholesome, charming, indie warmth

RULES:
1. Return ONLY a JSON object with all 6 keys and float values between 0.0 and 1.0.
2. Use the FULL range. 0.0 means completely absent, 1.0 means dominant.
3. No explanations, no preamble. JSON only."""

    user_prompt = f"""Title: {title}
Genres: {genre_str}
Overview: {overview}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        vector = {}
        for a in ARCHETYPES:
            val = data.get(a, 0.0)
            if isinstance(val, (int, float)):
                vector[a] = max(0.0, min(1.0, float(val)))
            else:
                vector[a] = 0.0

        return _normalize_vector(vector)

    except Exception as e:
        print(f"LLM Tagging Error: {e}")
        return None


def tag_movie(
    title: str,
    overview: str = "",
    genres: List[str] = None,
    keywords: List[str] = None,
    popularity: float = 0,
    runtime: int = 0,
    use_llm_fallback: bool = True
) -> Dict[str, float]:
    """
    Hybrid tagger: tries rule-based first, falls back to LLM if confidence is low.
    This is the main entry point for tagging a movie.
    """
    genres = genres or []
    keywords = keywords or []

    # Step 1: Rule-based tagging (free, instant)
    vector = tag_by_genre(genres, keywords, popularity, runtime)

    # Step 2: Check confidence
    max_dim = max(vector.values()) if vector else 0

    if use_llm_fallback and max_dim < CONFIDENCE_THRESHOLD and overview:
        # Low confidence — use LLM fallback
        llm_vector = tag_by_llm(title, overview, genres)
        if llm_vector:
            return llm_vector

    return vector
