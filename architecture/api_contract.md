# API Contract

The single responsibility of the backend endpoint is to apply deterministic calculations mapped from user intent onto the structured database layer.

## 1. `GET /recommend`

### Parameters
- `archetype` (query path): Allowed strings are exclusively restricted to `"Blockbuster", "Feel-Good", "Mind-Bending", "Emotional", "Dark & Gritty", "Epic Journey"`.

### Response Payload

The response provides a strict, entirely explainable scoring breakdown for maximum transparency.

```json
{
  "archetype": "Mind-Bending",
  "results": [
    {
      "title": "Inception",
      "base_score": 0.62,
      "emotional_score": 0.71,
      "final_score": 0.87
    },
    {
      "title": "Interstellar",
      "base_score": 0.60,
      "emotional_score": 0.68,
      "final_score": 0.84
    }
  ]
}
```

### Explanation
- **`final_score`**: The resulting unified rank priority (capped at additive weights).
- **`base_score`**: Output of `0.4 * normalized_vote_average + 0.3 * normalized_popularity + 0.3 * log_scaled_vote_count`
- **`emotional_score`**: Output representing alignment purely with the requested mapped `archetype` (e.g. drivers/dampeners computation).
