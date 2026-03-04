import pandas as pd
import os

CLEANED_DIR = "backend/data/cleaned"
OUTPUT_FILE = "backend/data/cleaned/emotional_archetype_tags.csv"

# Global definitions matching `architecture/emotional_model_design.md`
ARCHETYPES = [
    "Blockbuster",
    "Feel-Good",
    "Mind-Bending",
    "Emotional",
    "Dark & Gritty",
    "Epic Journey"
]

# STEP 1: Formal Genre Mapping Matrix
GENRE_MATRIX = {
    'action':    {'Blockbuster': 0.7, 'Feel-Good': 0.0, 'Mind-Bending': 0.2, 'Emotional': 0.0, 'Dark & Gritty': 0.4, 'Epic Journey': 0.5},
    'adventure': {'Blockbuster': 0.6, 'Feel-Good': 0.3, 'Mind-Bending': 0.2, 'Emotional': 0.2, 'Dark & Gritty': 0.1, 'Epic Journey': 0.8},
    'comedy':    {'Blockbuster': 0.2, 'Feel-Good': 0.9, 'Mind-Bending': 0.1, 'Emotional': 0.3, 'Dark & Gritty': 0.0, 'Epic Journey': 0.1},
    'drama':     {'Blockbuster': 0.1, 'Feel-Good': 0.2, 'Mind-Bending': 0.2, 'Emotional': 0.9, 'Dark & Gritty': 0.4, 'Epic Journey': 0.3},
    'thriller':  {'Blockbuster': 0.3, 'Feel-Good': 0.0, 'Mind-Bending': 0.8, 'Emotional': 0.2, 'Dark & Gritty': 0.6, 'Epic Journey': 0.2},
    'mystery':   {'Blockbuster': 0.2, 'Feel-Good': 0.0, 'Mind-Bending': 0.9, 'Emotional': 0.2, 'Dark & Gritty': 0.5, 'Epic Journey': 0.1},
    'horror':    {'Blockbuster': 0.3, 'Feel-Good': 0.0, 'Mind-Bending': 0.4, 'Emotional': 0.2, 'Dark & Gritty': 0.9, 'Epic Journey': 0.0},
    'fantasy':   {'Blockbuster': 0.4, 'Feel-Good': 0.4, 'Mind-Bending': 0.5, 'Emotional': 0.3, 'Dark & Gritty': 0.2, 'Epic Journey': 0.9},
    'science fiction':    
                 {'Blockbuster': 0.5, 'Feel-Good': 0.1, 'Mind-Bending': 0.8, 'Emotional': 0.2, 'Dark & Gritty': 0.3, 'Epic Journey': 0.6},
    'romance':   {'Blockbuster': 0.1, 'Feel-Good': 0.6, 'Mind-Bending': 0.1, 'Emotional': 0.8, 'Dark & Gritty': 0.0, 'Epic Journey': 0.2},
    'war':       {'Blockbuster': 0.5, 'Feel-Good': 0.0, 'Mind-Bending': 0.3, 'Emotional': 0.6, 'Dark & Gritty': 0.8, 'Epic Journey': 0.7},
    'crime':     {'Blockbuster': 0.4, 'Feel-Good': 0.0, 'Mind-Bending': 0.6, 'Emotional': 0.5, 'Dark & Gritty': 0.9, 'Epic Journey': 0.2}
}

# STEP 2: Keyword Boosting Dictionaries
KEYWORD_BOOSTS = {
    'Dark & Gritty': ['violence', 'corruption', 'murder', 'crime', 'revenge', 'brutal', 'mafia', 'assassin'],
    'Mind-Bending': ['dream', 'parallel', 'time', 'memory', 'psychological', 'alternate reality', 'conspiracy'],
    'Emotional': ['family', 'love', 'loss', 'relationship', 'tragedy', 'coming of age']
}

def generate_tags():
    movies_path = os.path.join(CLEANED_DIR, "movies_cleaned.csv")
    genres_path = os.path.join(CLEANED_DIR, "movie_genres.csv")
    keywords_path = os.path.join(CLEANED_DIR, "movie_keywords.csv")

    if not all(os.path.exists(p) for p in [movies_path, genres_path, keywords_path]):
        print("Missing cleaned data. Run clean_data.py first.")
        return

    print("Loading cleaned datasets...")
    movies_df = pd.read_csv(movies_path).fillna('')
    movies_df['popularity'] = pd.to_numeric(movies_df['popularity'], errors='coerce').fillna(0)
    movies_df['vote_count'] = pd.to_numeric(movies_df['vote_count'], errors='coerce').fillna(0)
    movies_df['runtime'] = pd.to_numeric(movies_df['runtime'], errors='coerce').fillna(0)
    
    genres_df = pd.read_csv(genres_path)
    keywords_df = pd.read_csv(keywords_path)

    print("Indexing genres and keywords...")
    genre_map = genres_df.groupby('movie_id')['genre_name'].apply(set).to_dict()
    keyword_map = keywords_df.groupby('movie_id')['keyword_name'].apply(set).to_dict()

    print("Executing strict matrix tagging...")
    records = []
    
    for _, movie in movies_df.iterrows():
        movie_id = movie['id']
        m_genres = genre_map.get(movie_id, set())
        m_keywords = keyword_map.get(movie_id, set())
        
        # 1. Base initialization
        scores = {arch: 0.0 for arch in ARCHETYPES}
        
        # Count matching formal genres to calculate averages
        valid_genres = [g for g in m_genres if g in GENRE_MATRIX]
        
        # 2. Apply genre averages
        if valid_genres:
            for arch in ARCHETYPES:
                total_genre_weight = sum(GENRE_MATRIX[g][arch] for g in valid_genres)
                scores[arch] = total_genre_weight / len(valid_genres)
        
        # 3. Apply keyword boosts
        for arch in ['Dark & Gritty', 'Mind-Bending', 'Emotional']:
            matched_kw = sum(1 for kw in m_keywords if any(boost_kw in kw for boost_kw in KEYWORD_BOOSTS[arch]))
            boost = min(0.3, matched_kw * 0.1) # Cap at +0.3
            scores[arch] += boost
            
        # 4. Apply Popularity Modifier (Blockbuster)
        if movie['popularity'] > 50:
            scores['Blockbuster'] += 0.1
        if movie['vote_count'] > 2000:
            scores['Blockbuster'] += 0.1
            
        # 5. Apply Runtime Modifier (Epic Journey)
        if movie['runtime'] > 140:
            scores['Epic Journey'] += 0.1
            
        # 6. Normalize Scores & Filter
        for arch in ARCHETYPES:
            final_score = min(1.0, scores[arch]) # Clamp values
            if final_score >= 0.20: # Save to table criteria
                records.append({
                    'movie_id': movie_id,
                    'archetype': arch,
                    'weight': round(final_score, 4)
                })

    final_tags_df = pd.DataFrame(records)
    if final_tags_df.empty:
        print("Warning: No tags matched the criteria. Check matrix/dataset mapping.")
        return

    # Sanity checks required by spec
    # No movie has > 4 archetypes
    arch_counts = final_tags_df.groupby('movie_id').size()
    excessive_movies = arch_counts[arch_counts > 4]
    if not excessive_movies.empty:
        print(f"Warning: {len(excessive_movies)} movies have more than 4 archetypes mapped.")
        
    final_tags_df.to_csv(OUTPUT_FILE, index=False)
    
    print(f"Success! {len(final_tags_df)} emotional tags mapped perfectly to matrix constraints.")
    print("--- Distribution Sanity Check ---")
    print(final_tags_df['archetype'].value_counts(normalize=True).round(4))
    
if __name__ == "__main__":
    generate_tags()
