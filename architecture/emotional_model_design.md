# Emotional Model Design – Deterministic Definitions

## 1. Scoring Framework

Each archetype produces:

emotional_score ∈ [0, 1]

Structure:

emotional_score =
    (Primary Drivers Weighted Sum)
  + (Secondary Drivers Weighted Sum)
  - (Dampeners)

Final score is clipped to [0, 1].

---

## 2. Archetype Definitions

----------------------------------------
A. Blockbuster
----------------------------------------

Primary Drivers (max 0.6 total):
- Genre in [Action, Adventure, Sci-Fi] → +0.25
- normalized_popularity → +0.20
- log_scaled_vote_count → +0.15

Secondary Drivers (max 0.2):
- vote_average > 6.8 → +0.10
- runtime between 100–150 → +0.10

Dampeners (max -0.2):
- Genre in [Documentary] → -0.10
- vote_count < threshold_low → -0.10

----------------------------------------
B. Feel-Good
----------------------------------------

Primary Drivers:
- Genre in [Comedy, Family, Romance] → +0.30
- vote_average > 7 → +0.15
- normalized_popularity → +0.15

Secondary Drivers:
- release_year > 1995 → +0.10
- runtime < 130 → +0.10

Dampeners:
- Genre in [War, Horror] → -0.15

----------------------------------------
C. Mind-Bending
----------------------------------------

Primary Drivers:
- Genre in [Sci-Fi, Mystery, Thriller] → +0.30
- vote_average > 7.2 → +0.20
- runtime > 100 → +0.10

Secondary Drivers:
- keyword match in ["dream", "time", "parallel", "memory"] → +0.15
- vote_count moderate (not top 5%) → +0.05

Dampeners:
- Genre in [Comedy, Family] → -0.15

----------------------------------------
D. Emotional
----------------------------------------

Primary Drivers:
- Genre in [Drama, Romance] → +0.30
- vote_average > 7 → +0.20
- runtime 100–140 → +0.10

Secondary Drivers:
- release_year > 1980 → +0.10
- keyword match ["loss", "love", "family"] → +0.10

Dampeners:
- Genre in [Action] → -0.10

----------------------------------------
E. Dark & Gritty
----------------------------------------

Primary Drivers:
- Genre in [Crime, Thriller, War] → +0.30
- vote_average > 7 → +0.20
- runtime > 105 → +0.10

Secondary Drivers:
- release_year > 1990 → +0.10
- lower popularity percentile (avoid mainstream bias) → +0.10

Dampeners:
- Genre in [Animation, Family] → -0.20

----------------------------------------
F. Epic Journey
----------------------------------------

Primary Drivers:
- Genre in [Adventure, Fantasy, Drama] → +0.30
- runtime > 120 → +0.20
- vote_average > 7 → +0.10

Secondary Drivers:
- release_year > 1985 → +0.10
- vote_count high → +0.10

Dampeners:
- runtime < 95 → -0.15

---

## 3. Blending Formula

final_score =
    base_score
  + (0.35 * emotional_score)

Emotional score influence is capped at 35%.

---

## 4. Guardrails

- emotional_score is clipped to [0, 1]
- Negative total values are floored at 0
- Archetype selection is exclusive (only one at a time)
- No stacking of multiple archetypes

---

## 5. Validation Criteria

For each archetype:
- Top 20 results must differ visibly
- Genre distribution must align with archetype definition
- Emotional_score must meaningfully shift rankings
