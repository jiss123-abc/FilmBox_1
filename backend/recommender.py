import sqlite3
from typing import List, Dict
from backend.db import get_db_connection
from backend.base_scoring import get_global_constants, calculate_base_score

def get_recommendations(archetype: str, limit: int = 20) -> Dict:
    """
    Retrieves top-N movies using the refined Phase 2 blending formula.
    
    Formula:
    final_score = normalized_base + (0.35 * emotional_score)
    """
    conn = get_db_connection()
    constants = get_global_constants(conn)
    
    # Fetch movies with emotional tags for this archetype
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            m.*, 
            t.weight as emotional_weight
        FROM movies m
        JOIN emotional_archetype_tags t ON m.id = t.movie_id
        WHERE t.archetype = ?
    """, (archetype,))
    rows = cursor.fetchall()
    
    results = []
    alpha = 0.35

    for row in rows:
        # Calculate refined base score components
        base_scores = calculate_base_score(row, constants)
        norm_base = base_scores["normalized_base"]
        
        # Emotional alignment weight from Phase 1
        emot_weight = row["emotional_weight"]
        
        # final_score = normalized_base + (alpha * emotional_score)
        final_score = norm_base + (alpha * emot_weight)
        
        results.append({
            "title": row["title"],
            "base_score": norm_base,
            "emotional_score": emot_weight,
            "final_score": round(final_score, 4),
            "details": base_scores # Include raw metrics for explainability
        })
    
    # Rank by final score
    results.sort(key=lambda x: x["final_score"], reverse=True)
    
    conn.close()
    
    return {
        "archetype": archetype,
        "results": results[:limit]
    }
