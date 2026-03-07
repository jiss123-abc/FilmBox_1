import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

load_dotenv()

from backend.intent_classifier import classify_emotional_vector

print(classify_emotional_vector("malayalam movie"))
