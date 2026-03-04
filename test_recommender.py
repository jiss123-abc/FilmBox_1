import sys
import os

# Ensure we can import from backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.scoring.recommender import recommend

print("Top 10 Global:")
print(recommend(None, 10))

print("\nTop 10 Dark & Gritty:")
print(recommend("Dark & Gritty", 10))

print("\nTop 10 Feel-Good:")
print(recommend("Feel-Good", 10))
