"""
FILMBOX — Ingest Top 100K Movies

Reads `movie_ids_100k.json` and ingests them into the database.
Uses the same multithreaded logic as `ingest_bulk.py`.
"""

import os
import sys

# Ensure backend module is available
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Read from ingest_bulk but override the IDS_FILE
import backend.scripts.ingest_bulk as ingest_bulk

if __name__ == "__main__":
    # Override the file path to our new 100k targets
    ingest_bulk.IDS_FILE = os.path.join(os.path.dirname(__file__), "..", "movie_ids_100k.json")
    
    print("=" * 60)
    print("FILMBOX — 100K Bulk Ingestion Run")
    print(f"Targeting list: {ingest_bulk.IDS_FILE}")
    print("=" * 60)
    
    # Run the existing robust ingestion logic
    ingest_bulk.bulk_ingest()
