"""
FILMBOX — Generate 100K IDs

Downloads the TMDb daily export and extracts the top 100,000 movies by popularity,
bypassing the popularity floor that restricted the previous set to ~60k.
"""

import urllib.request
import gzip
import json
import os

MAX_MOVIES = 100000
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "movie_ids_100k.json")

def process():
    # Use today's date format for the TMDb export URL (or a recent one)
    # The URL changes daily; we'll try the latest one available in the system, 
    # or just stream the official 03_05_2026 file the user had.
    
    local_file1 = os.path.join(os.path.dirname(__file__), "..", "..", "movie_ids_03_05_2026.json")
    local_file2 = os.path.join(os.path.dirname(__file__), "..", "..", "data", "tmdb_exports", "movie_ids_03_05_2026.json")
    url = "http://files.tmdb.org/p/exports/movie_ids_03_05_2026.json.gz"
    
    stream = None
    is_gzipped = False
    
    if os.path.exists(local_file1):
        stream = open(local_file1, 'rt', encoding='utf-8')
    elif os.path.exists(local_file2):
        stream = open(local_file2, 'rt', encoding='utf-8')
    else:
        print(f"Downloading securely via HTTP stream from {url}")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        stream = gzip.GzipFile(fileobj=response)
        is_gzipped = True

    print("Processing...")
    movies = []
    
    with stream as s:
        for line in s:
            try:
                if is_gzipped and isinstance(line, bytes):
                    line = line.decode('utf-8')
                data = json.loads(line)
                
                if data.get("adult", False):
                    continue
                    
                popularity = data.get("popularity", 0.0)
                movies.append({"id": data.get("id"), "popularity": popularity})
            except json.JSONDecodeError:
                continue

    movies.sort(key=lambda x: x["popularity"], reverse=True)
    top_movies = movies[:MAX_MOVIES]
    
    print(f"Truncating to top {len(top_movies)} movies.")
    print(f"Lowest popularity in set: {top_movies[-1]['popularity']:.3f}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(top_movies, f, indent=2)

    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process()
