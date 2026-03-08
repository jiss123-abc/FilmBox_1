import os
import json
import math
from typing import Optional, Dict, Tuple
from groq import Groq

# The single source of truth for allowed categories
ARCHETYPES = [
    "mind_bending",
    "dark",
    "emotional",
    "inspirational",
    "adrenaline",
    "light"
]


def normalize_vector(vec_dict: Dict[str, float]) -> Dict[str, float]:
    """Normalize a vector to unit length. Prevents LLM output scale from biasing cosine similarity."""
    values = list(vec_dict.values())
    norm = math.sqrt(sum(v * v for v in values))
    if norm == 0:
        return vec_dict
    return {k: v / norm for k, v in vec_dict.items()}


def classify_emotional_vector(user_input: str) -> Tuple[Dict[str, float], Dict]:
    """
    Uses Groq LLM to parse a natural language query into:
      1. A 6D emotional vector (mood/vibe)
      2. Structured filters (person, language, country, keyword, certification, sort)
      3. Context query for story-level plot search

    Returns: (normalized_vector_dict, structured_intent_dict)
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not found in environment.")
        return {a: 0.0 for a in ARCHETYPES}, {}

    client = Groq(api_key=api_key)

    system_prompt = f"""You are a precise query analysis engine for a movie recommender called FILMBOX.

Your task: Analyze the user's natural language request and extract ALL relevant signals.

Return a JSON object with these keys:

EMOTIONAL VECTOR (always include all 6):
- mind_bending: float 0.0-1.0 — Psychological complexity, twists, non-linear narrative
- dark: float 0.0-1.0 — Gritty, noir, moral tension, violence, crime, horror
- emotional: float 0.0-1.0 — Character depth, drama, tearjerker, heartbreak
- inspirational: float 0.0-1.0 — Uplifting, comeback arcs, triumph, biopics, hope
- adrenaline: float 0.0-1.0 — Action, intensity, fast-paced, thrillers, suspense
- light: float 0.0-1.0 — Feel-good, comedy, wholesome, charming

STRUCTURED FILTERS (set to null if not detected):
- person_name: string|null — Actor or director name (e.g. "Tom Cruise", "Christopher Nolan")
- language: string|null — 2-letter ISO-639-1 language code ONLY (e.g. "hi" for Hindi, "ko" for Korean, "ml" for Malayalam)
- country: string|null — Country or region (e.g. "South Korea", "India", "South America")
- keyword: string|null — Theme or keyword (e.g. "revenge", "time travel", "space")
- certification: string|null — Rating (e.g. "R", "PG-13", "PG")
- sort_by: string|null — One of: "best", "worst", "trending", "random", "hidden_gems" or null
- similar_to_title: string|null — The title of a movie to find recommendations similar to (e.g. for "movies like Inception", extracted value is "Inception")

CONTEXT SEARCH (set to null if not detected):
- context_query: string|null — Search terms to find matching movie plot descriptions. CRITICAL: Do NOT just echo the user's words. Instead, think about what words would ACTUALLY APPEAR in a movie's plot overview/synopsis for this concept. Movie overviews describe what happens in the story — generate 4-8 words that a movie database synopsis would use. Examples: user says "hero loses" → use "defeat tragic death sacrifice failure falls"; user says "villain wins" → use "evil triumphs defeat darkness prevails"; user says "trapped in one room" → use "confined trapped room escape locked"; user says "time loops" → use "loop repeating relive same day over". Set to null for pure mood/filter queries.

RULES:
1. Return ONLY a JSON object. No explanations.
2. If the query is purely about filters (e.g. "Hindi movies"), set all emotional values to 0.0.
3. If the query combines mood + filters (e.g. "dark korean revenge movie"), set BOTH emotional values AND filters.
4. If the query is purely emotional (e.g. "mind-bending thriller"), set emotional values and all filters to null.
5. "best movies" or "top rated" → sort_by: "best". "worst movies" → sort_by: "worst".
6. "trending" or "popular" → sort_by: "trending".
7. "random" or "surprise me" → sort_by: "random".
8. "hidden gems" or "underrated" → sort_by: "hidden_gems".
9. Use the FULL range for emotional values. 0.0 = absent, 1.0 = dominant.
10. NEVER extract the archetype core words ("dark", "mind-bending", "inspirational", "emotional", "light", "adrenaline") as the `keyword` string. The `keyword` should only be concrete plot elements like "revenge" or "space".
11. context_query is for STORY-LEVEL plot concepts that go beyond single keywords. If the user describes a plot pattern (e.g. "movies where the villain wins"), extract the core concept as context_query (e.g. "villain wins defeat"). For simple keyword queries, use keyword instead.
12. context_query and keyword can BOTH be set simultaneously when appropriate.
13. MOVIE NAMES: If the user query is clearly a specific movie title (e.g. "Avengers", "The Matrix", "Interstellar"), do NOT abstract it into a vibe. Set emotional values to low/neutral and let the search engine handle the title.
14. SIMILAR TO: Only extract `similar_to_title` if the user explicitly asks for movies "like", "similar to", or "more of" a specific title (e.g. "movies like Inception"). For pure title entries (e.g. "Inception"), set `similar_to_title` to null.

EXAMPLES:
- "dark korean revenge movie" → {{"mind_bending": 0.3, "dark": 0.9, "emotional": 0.4, "inspirational": 0.0, "adrenaline": 0.6, "light": 0.0, "person_name": null, "language": "ko", "country": "South Korea", "keyword": "revenge", "certification": null, "sort_by": null, "similar_to_title": null, "context_query": null}}
- "Avengers" → {{"mind_bending": 0.1, "dark": 0.1, "emotional": 0.1, "inspirational": 0.1, "adrenaline": 0.3, "light": 0.1, "person_name": null, "language": null, "country": null, "keyword": null, "certification": null, "sort_by": null, "similar_to_title": null, "context_query": null}}
- "movies like The Matrix" → {{"mind_bending": 0.0, "dark": 0.0, "emotional": 0.0, "inspirational": 0.0, "adrenaline": 0.0, "light": 0.0, "person_name": null, "language": null, "country": null, "keyword": null, "certification": null, "sort_by": null, "similar_to_title": "The Matrix", "context_query": null}}
- "Bramayugam" → {{"mind_bending": 0.1, "dark": 0.1, "emotional": 0.1, "inspirational": 0.1, "adrenaline": 0.3, "light": 0.1, "person_name": null, "language": null, "country": null, "keyword": null, "certification": null, "sort_by": null, "similar_to_title": null, "context_query": null}}
- "more like Bramayugam" → {{"mind_bending": 0.0, "dark": 0.0, "emotional": 0.0, "inspirational": 0.0, "adrenaline": 0.0, "light": 0.0, "person_name": null, "language": null, "country": null, "keyword": null, "certification": null, "sort_by": null, "similar_to_title": "Bramayugam", "context_query": null}}
- "Tom Cruise movies" → {{"mind_bending": 0.0, "dark": 0.0, "emotional": 0.0, "inspirational": 0.0, "adrenaline": 0.0, "light": 0.0, "person_name": "Tom Cruise", "language": null, "country": null, "keyword": null, "certification": null, "sort_by": null, "similar_to_title": null, "context_query": null}}
- "movies where the villain wins" → {{"mind_bending": 0.3, "dark": 0.8, "emotional": 0.2, "inspirational": 0.0, "adrenaline": 0.4, "light": 0.0, "person_name": null, "language": null, "country": null, "keyword": null, "certification": null, "sort_by": null, "similar_to_title": null, "context_query": "evil triumphs darkness prevails villain defeats"}}
- "movies where the hero loses" → {{"mind_bending": 0.2, "dark": 0.8, "emotional": 0.6, "inspirational": 0.0, "adrenaline": 0.3, "light": 0.0, "person_name": null, "language": null, "country": null, "keyword": null, "certification": null, "sort_by": null, "similar_to_title": null, "context_query": "defeat tragic death sacrifice failure falls destroyed"}}
- "movies about time loops" → {{"mind_bending": 0.9, "dark": 0.2, "emotional": 0.1, "inspirational": 0.0, "adrenaline": 0.3, "light": 0.0, "person_name": null, "language": null, "country": null, "keyword": "time travel", "certification": null, "sort_by": null, "similar_to_title": null, "context_query": "loop repeating relive same day over again"}}
- "dark psychological movies about obsession" → {{"mind_bending": 0.7, "dark": 0.9, "emotional": 0.5, "inspirational": 0.0, "adrenaline": 0.3, "light": 0.0, "person_name": null, "language": null, "country": null, "keyword": null, "certification": null, "sort_by": null, "similar_to_title": null, "context_query": "obsessed fixated consumed madness spiraling"}}
- "movies where people are trapped in one location" → {{"mind_bending": 0.3, "dark": 0.5, "emotional": 0.2, "inspirational": 0.0, "adrenaline": 0.6, "light": 0.0, "person_name": null, "language": null, "country": null, "keyword": null, "certification": null, "sort_by": null, "similar_to_title": null, "context_query": "trapped confined locked room bunker escape survive"}}
- "hidden gems" → {{"mind_bending": 0.0, "dark": 0.0, "emotional": 0.0, "inspirational": 0.0, "adrenaline": 0.0, "light": 0.0, "person_name": null, "language": null, "country": null, "keyword": null, "certification": null, "sort_by": "hidden_gems", "similar_to_title": null, "context_query": null}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        # Extract emotional vector
        vector = {}
        for a in ARCHETYPES:
            val = data.get(a, 0.0)
            if isinstance(val, (int, float)):
                vector[a] = max(0.0, min(1.0, float(val)))
            else:
                vector[a] = 0.0

        # Normalize to unit vector
        vector = normalize_vector(vector)

        # Extract structured filters
        intent = {}
        for key in ["person_name", "language", "country", "keyword", "certification", "sort_by", "context_query", "similar_to_title"]:
            val = data.get(key)
            if val and isinstance(val, str) and val.strip():
                intent[key] = val.strip()

        return vector, intent

    except Exception as e:
        print(f"LLM Classification Error: {e}")
        return {a: 0.0 for a in ARCHETYPES}, {}


def classify_archetype(user_input: str) -> Optional[str]:
    """
    Backward-compatible: Maps user natural language to exactly ONE emotional archetype.
    Returns the archetype name (string) or None if the mapping is invalid.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not found in environment.")
        return None

    client = Groq(api_key=api_key)

    system_prompt = f"""You are a strict text classification engine for a movie recommender.
    Your task: Map the user's natural language request to exactly ONE of these archetypes:
    {ARCHETYPES}

    RULES:
    1. Only return a JSON object like: {{"archetype": "NAME"}}.
    2. The "NAME" must be exactly as written in the list above.
    3. If the request is vague or doesn't match a movie vibe, return {{"archetype": null}}.
    4. Do not provide any explanation, preamble, or conversational filler.
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        archetype = data.get("archetype")

        if archetype in ARCHETYPES:
            return archetype

        return None

    except Exception as e:
        print(f"LLM Classification Error: {e}")
        return None
