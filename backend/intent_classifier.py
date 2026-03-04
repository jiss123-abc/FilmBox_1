import os
import json
from typing import Optional
from groq import Groq

# The single source of truth for allowed categories
ARCHETYPES = [
    "Blockbuster",
    "Feel-Good",
    "Mind-Bending",
    "Emotional",
    "Dark & Gritty",
    "Epic Journey"
]

def classify_archetype(user_input: str) -> Optional[str]:
    """
    Uses Groq LLM to map user natural language to exactly ONE emotional archetype.
    Returns the archetype name (string) or None if the mapping is invalid.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not found in environment.")
        return None

    client = Groq(api_key=api_key)

    system_prompt = f"""
    You are a strict text classification engine for a movie recommender.
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
            temperature=0.0  # Zero creativity for deterministic classification
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        archetype = data.get("archetype")

        # Validation: Must be in our allowed list
        if archetype in ARCHETYPES:
            return archetype
        
        return None

    except Exception as e:
        print(f"LLM Classification Error: {e}")
        return None
