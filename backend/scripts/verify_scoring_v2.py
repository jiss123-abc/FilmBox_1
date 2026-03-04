import sys
import os

# Add the project root (D:\Filmbox) to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.recommender import get_recommendations

def verify_scoring_v2():
    print("🎬 FilmBox Phase 2 Verification - Refined Bayesian Scoring\n")
    
    archetypes = ["Blockbuster", "Mind-Bending", "Emotional", "Dark & Gritty"]
    
    for arch in archetypes:
        print(f"--- Top 5 for: {arch} ---")
        recs = get_recommendations(arch, limit=5)
        
        if not recs["results"]:
            print("No data found.\n")
            continue
            
        print(f"{'Title':<22} | {'Base':<8} | {'Emot':<8} | {'Final':<8}")
        print("-" * 60)
        for r in recs["results"]:
            print(f"{r['title']:<22} | {r['base_score']:<8.4f} | {r['emotional_score']:<8.4f} | {r['final_score']:<8.4f}")
        print("\n")

if __name__ == "__main__":
    verify_scoring_v2()
