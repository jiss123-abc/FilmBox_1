import sys
import os

# Set up project root in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.scoring.recommender import recommend

def run_phase2_validation():
    print("🎬 FilmBox Phase 2 — Deterministic Scoring Validation\n")

    test_cases = [
        (None, "Global Top Quality"),
        ("Blockbuster", "High Adrenaline/Crowd Pleasers"),
        ("Mind-Bending", "Complex/Sci-Fi/Psychological"),
        ("Feel-Good", "Comedy/Family Joy")
    ]

    for arch, description in test_cases:
        print(f"--- TEST: {description} ({arch if arch else 'ALL'}) ---")
        recs = recommend(archetype=arch, limit=10)
        
        if not recs["results"]:
            print("No movies found for this criteria.\n")
            continue

        print(f"{'Rank':<4} | {'Title':<25} | {'Base':<8} | {'Emot':<8} | {'Final':<8}")
        print("-" * 65)
        for i, r in enumerate(recs["results"], 1):
            print(f"{i:<4} | {r['title']:<25} | {r['base_quality']:<8.4f} | {r['emotional_alignment']:<8.4f} | {r['final_score']:<8.4f}")
        print("\n")

if __name__ == "__main__":
    try:
        run_phase2_validation()
    except Exception as e:
        print(f"❌ Validation Error: {e}")
