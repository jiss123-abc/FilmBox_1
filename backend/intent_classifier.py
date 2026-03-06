import os
import json
import math
from typing import Optional, Dict
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


def classify_emotional_vector(user_input: str) -> Dict[str, float]:
    """
    Uses Groq LLM to map natural language to a 6D emotional vector.
    Returns a normalized dict like: {"mind_bending": 0.7, "dark": 0.5, ...}
    All 6 archetypes are guaranteed present (zero-filled if missing).
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not found in environment.")
        return {a: 0.0 for a in ARCHETYPES}

    client = Groq(api_key=api_key)

    system_prompt = f"""You are a precise emotional analysis engine for a movie recommender called FILMBOX.

Your task: Analyze the user's natural language request and output a 6-dimensional emotional vector.

The 6 dimensions are:
- mind_bending: Psychological complexity, twists, non-linear narrative, existential themes
- dark: Gritty, noir, moral tension, violence, crime, horror
- emotional: Character depth, drama, tearjerker, heartbreak, relationship-driven
- inspirational: Uplifting, comeback arcs, triumph, biopics, hope
- adrenaline: Action, intensity, fast-paced, thrillers, suspense, combat
- light: Feel-good, comedy, wholesome, charming, indie warmth

RULES:
1. Return ONLY a JSON object with all 6 keys and float values between 0.0 and 1.0.
2. Example output: {{"mind_bending": 0.8, "dark": 0.7, "emotional": 0.3, "inspirational": 0.0, "adrenaline": 0.4, "light": 0.0}}
3. Use the FULL range. 0.0 means completely absent, 1.0 means dominant.
4. Do NOT use 1.0 unless the dimension is extremely dominant.
5. A vague request should spread weight across multiple dimensions.
6. No explanations, no preamble. JSON only."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        # Zero-fill any missing archetypes, clamp values to [0, 1]
        vector = {}
        for a in ARCHETYPES:
            val = data.get(a, 0.0)
            if isinstance(val, (int, float)):
                vector[a] = max(0.0, min(1.0, float(val)))
            else:
                vector[a] = 0.0

        # Normalize to unit vector
        return normalize_vector(vector)

    except Exception as e:
        print(f"LLM Classification Error: {e}")
        return {a: 0.0 for a in ARCHETYPES}


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
            model="llama-3.3-70b-versatile",
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
