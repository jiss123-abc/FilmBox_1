# Scoring Architecture

The ranking system is built on two transparent, formulaic pillars: a global base score and an archetype-specific emotional score. They are calculated independently and blended additively.

## 1. Base Score Engine
The base score measures a movie's global quality and visibility, irrespective of user mood. It is emotion-neutral.

**Formula:**
`base_score = 0.4 * normalized_vote_average + 0.3 * normalized_popularity + 0.3 * log_scaled_vote_count`

### Rationale for Weights
- **0.4 (Vote Average)**: Quality is prioritized over sheer visibility, ensuring highly-rated movies are surfaced first. 
- **0.3 (Popularity) & 0.3 (Vote Count)**: Combining these factors accounts for community volume and momentum, preventing obscure, highly-rated but deeply niche movies (with only 1 or 2 votes) from dominating the top ranks unexplainably.

### Normalization and Scaling
- **Why Normalization?**: All metrics must be normalized to a standard numeric domain (e.g. `[0, 1]`) to prevent metrics with large numeric ranges (e.g., `vote_count` capable of passing millions) from unconditionally overpowering smaller-scale metrics (e.g., `vote_average` sitting in `[0, 10]`).
- **Why Log Scaling?**: Specifically used for `vote_count` because vote distributions follow a power law (a few movies have millions of votes, most have few). Log scaling linearizes this impact so a movie requires exponentially more votes to push the score closer to 1.0. This flattens the curve and keeps the scale balanced.

## 2. Emotional Archetype Overlay
Each movie receives an `emotional_score ∈ [0, 1]` based on how well its metadata aligns with the selected archetype (as explicitly laid out in `emotional_model_design.md`).

## 3. Final Ranking Blend
The ultimate rank is determined by blending the global quality with the emotional alignment constraint.

**Formula:**
`final_score = base_score + (0.35 * emotional_score)`

### Why Additive Blending?
Multiplying scores would disproportionately penalize great movies with slightly lower emotional alignment, or vastly over-favor perfectly aligned movies that are statistically terrible. Additive blending ensures stability and allows movies with exceptionally high base scores to remain a competitive recommendation.

### Why Capped at 35%?
The emotional influence is capped by using a `0.35` multiplier on the emotional score. This prevents the system from highly ranking obscure/poorly-rated movies solely because they match the genre tags perfectly. Global quality (Base Score) remains the reliable anchor, while the Emotional Score acts as a robust tie-breaker or context directional booster.
