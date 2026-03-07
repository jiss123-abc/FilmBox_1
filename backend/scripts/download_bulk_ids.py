"""
FILMBOX — TMDb Bulk Export Downloader (Phase 9)

Downloads the daily `movie_ids.json.gz` export from TMDb, 
filters for non-adult movies with a minimum popularity, 
sorts them by popularity, and saves a local snapshot.

Scale: ~300,000 top movies.
"""

import urllib.request
import gzip
import json
import os
from datetime import datetime, timedelta

# Target parameters based on Phase 9 spec
MAX_MOVIES = 300000
MIN_POPULARITY = 0.05

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "movie_ids.json")


def process_export():
    import urllib.request
    
    # Try looking for a local file first (if the user curl'd it manually)
    local_file1 = os.path.join(os.path.dirname(__file__), "..", "..", "movie_ids_03_05_2026.json")
    local_file2 = os.path.join(os.path.dirname(__file__), "..", "..", "data", "tmdb_exports", "movie_ids_03_05_2026.json")
    
    url = "http://files.tmdb.org/p/exports/movie_ids_03_05_2026.json.gz"
    
    stream = None
    file_source = ""
    is_gzipped = False
    
    if os.path.exists(local_file1):
        stream = open(local_file1, 'rt', encoding='utf-8')
        file_source = f"Local File: {local_file1}"
    elif os.path.exists(local_file2):
        stream = open(local_file2, 'rt', encoding='utf-8')
        file_source = f"Local File: {local_file2}"
    else:
        # Download directly via streaming
        print(f"📥 Local file not found. Downloading securely via HTTP stream...")
        print(f"   URL: {url}")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        stream = gzip.GzipFile(fileobj=response)
        file_source = "HTTP Stream (Live)"
        is_gzipped = True

    print(f"📥 Processing TMDb Bulk Export...")
    print(f"   Source: {file_source}")
    print(f"   Filtering: Adult = False | Popularity > {MIN_POPULARITY}")
    print("=" * 60)

    movies = []
    
    with stream as s:
        for line in s:
            try:
                # Handle bytes vs string depending on stream type
                if is_gzipped and isinstance(line, bytes):
                    line = line.decode('utf-8')
                data = json.loads(line)
                
                # Filter out adult films
                if data.get("adult", False):
                    continue
                    
                popularity = data.get("popularity", 0.0)
                
                # Apply popularity threshold
                if popularity > MIN_POPULARITY:
                    movies.append({
                        "id": data.get("id"),
                        "popularity": popularity
                    })
                    
            except json.JSONDecodeError:
                continue

    print(f"✅ Found {len(movies)} movies matching the filter criteria.")
    print("   Sorting by popularity (Descending)...")
    
    # Sort purely by popularity so we import the most relevant films first
    movies.sort(key=lambda x: x["popularity"], reverse=True)
    
    # Truncate to our max limit
    top_movies = movies[:MAX_MOVIES]
    
    print(f"   Truncating to top {len(top_movies)} movies.")
    print(f"   Lowest popularity in set: {top_movies[-1]['popularity']:.2f}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(top_movies, f, indent=2)

    print(f"💾 Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    process_export()
