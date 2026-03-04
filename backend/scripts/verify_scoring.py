import sys
import os

# Ensure backend package can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.recommender import get_recommendations

def run_verification():
    """
    Phase 2 Scoring Verification.
    Runs rankings for two distinct archetypes to verify distribution and logic.
    """
    tests = ["Mind-Bending", "Blockbuster"]
    
    print("🚀 Running Phase 2 Scoring Verification...\n")
    
    for archetype in tests:
        print(f"--- Top 5 Recommendations for: {archetype} ---")
        results = get_recommendations(archetype, limit=5)
        
        if not results["results"]:
            print("No results found for this archetype.")
            continue
            
        print(f"{'Title':<20} | {'Base':<8} | {'Emot':<8} | {'Final':<8}")
        print("-" * 55)
        for r in results["results"]:
            print(f"{r['title']:<20} | {r['base_score']:<8.4f} | {r['emotional_score']:<8.4f} | {r['final_score']:<8.4f}")
        print("\n")

if __name__ == "__main__":
    try:
        run_verification()
    except Exception as e:
        print(f"❌ Verification failed: {e}")
