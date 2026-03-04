# FilmBox – System Overview

## 1. Purpose

FilmBox is a deterministic emotional movie recommendation engine.

The system maps structured emotional intent into mathematical scoring overlays applied to movie metadata.

All ranking decisions are explainable and formula-driven.

No black-box ranking logic is used.

---

## 2. Core Principles

1. Deterministic Scoring  
   All outputs are derived from fixed mathematical formulas.

2. Explainability  
   Every recommendation can be decomposed into:
   - base_score
   - emotional_score
   - final_score

3. Controlled Emotional Taxonomy  
   Only six predefined emotional archetypes are supported.

---

## 3. Emotional Archetypes (Fixed Set)

The system supports exactly:

- Blockbuster
- Feel-Good
- Mind-Bending
- Emotional
- Dark & Gritty
- Epic Journey

No additional archetypes are dynamically created.

---

## 4. High-Level System Flow

User Input
   ↓
Archetype Selection (Structured Intent)
   ↓
Base Scoring Engine
   ↓
Emotional Overlay
   ↓
Final Score Computation
   ↓
Top-N Ranked Results

---

## 5. Data Architecture Summary

The system uses normalized relational metadata.

Core Movie Fields:
- movie_id
- title
- release_year
- runtime
- popularity
- vote_average
- vote_count

Relational Metadata:
- genres (many-to-many)
- keywords (many-to-many)

All joins are indexed.

---

## 6. Base Scoring Formula

The base score represents global quality and visibility:

base_score =
    0.4 * normalized_vote_average
  + 0.3 * normalized_popularity
  + 0.3 * log_scaled_vote_count

All inputs are normalized to range [0, 1].

This score is emotion-neutral.

---

## 7. Emotional Scoring

Each archetype defines:

- Primary Drivers (strong weights)
- Secondary Drivers (moderate weights)
- Dampeners (penalties)

Each movie receives:

emotional_score ∈ [0, 1]

---

## 8. Final Ranking Formula

final_score = base_score + (0.35 * emotional_score)

Emotional influence is capped at 35% additive weight.

Multiplicative boosting is not used.

---

## 9. API Contract

Endpoint:
GET /recommend?archetype=<ArchetypeName>

Response:
{
  "archetype": "...",
  "results": [
    {
      "title": "...",
      "base_score": 0.x,
      "emotional_score": 0.x,
      "final_score": 0.x
    }
  ]
}

---

## 10. Non-Goals

- Not a clone of The Movie Database (TMDb) or similar encyclopedias
- Not a conversational AI system
- Not collaborative filtering (unless explicitly added later)
- Not neural ranking

This is a structured emotional ranking engine.
