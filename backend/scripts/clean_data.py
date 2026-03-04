import pandas as pd
import json
import os

RAW_DATA_PATH = "backend/data/raw/movies.csv"
CLEANED_DIR = "backend/data/cleaned"

def parse_json_column(column_data):
    """Safely parse TMDB JSON string columns (like genres or keywords)."""
    try:
        # Some Kaggle datasets use single quotes or malformed JSON
        parsed = json.loads(column_data.replace("'", '"'))
        return [item['name'].lower().strip() for item in parsed]
    except (json.JSONDecodeError, TypeError, AttributeError):
        return []

def clean_data():
    if not os.path.exists(RAW_DATA_PATH):
        print(f"Error: {RAW_DATA_PATH} not found.")
        print("Please place the raw TMDB Kaggle movies.csv in backend/data/raw/")
        return

    print("Loading raw data...")
    # Load dataset, grabbing only the columns we need
    columns_to_keep = [
        'id', 'title', 'overview', 'genres', 'keywords', 
        'popularity', 'vote_average', 'vote_count', 'release_date', 'runtime'
    ]
    
    try:
        df = pd.read_csv(RAW_DATA_PATH, usecols=lambda c: c in columns_to_keep)
    except ValueError as e:
        print(f"Error reading CSV. Ensure it has the correct Kaggle TMDB columns: {e}")
        return

    print("Dropping duplicates and filtering...")
    # Clean base movies data
    df = df.drop_duplicates(subset=['id'])
    df = df.dropna(subset=['title', 'id'])
    
    # Needs to be cast to int/float respectively to filter properly
    df['vote_count'] = pd.to_numeric(df['vote_count'], errors='coerce').fillna(0).astype(int)
    df = df[df['vote_count'] >= 50]
    
    df['popularity'] = pd.to_numeric(df['popularity'], errors='coerce').fillna(0.0)
    df['vote_average'] = pd.to_numeric(df['vote_average'], errors='coerce').fillna(0.0)
    df['runtime'] = pd.to_numeric(df['runtime'], errors='coerce').fillna(0).astype(int)
    df['id'] = df['id'].astype(int)

    # Extract Release Year
    df['release_year'] = pd.to_datetime(df['release_date'], errors='coerce').dt.year.fillna(0).astype(int)

    print("Parsing JSON columns (genres and keywords)...")
    # Parse JSON strings into Python lists
    df['parsed_genres'] = df['genres'].apply(parse_json_column)
    df['parsed_keywords'] = df['keywords'].apply(parse_json_column)

    print("Creating normalized data structures...")
    
    # 1. Export Clean Movies
    clean_movies = df[['id', 'title', 'overview', 'release_year', 'runtime', 'popularity', 'vote_average', 'vote_count']]
    
    # 2. Extract Genres & Movie_Genres mapping
    genre_records = []
    for _, row in df.iterrows():
        movie_id = row['id']
        for genre in row['parsed_genres']:
            genre_records.append({'movie_id': movie_id, 'genre_name': genre})
            
    genres_df = pd.DataFrame(genre_records)
    
    # 3. Extract Keywords & Movie_Keywords mapping
    keyword_records = []
    for _, row in df.iterrows():
        movie_id = row['id']
        for keyword in row['parsed_keywords']:
             keyword_records.append({'movie_id': movie_id, 'keyword_name': keyword})
             
    keywords_df = pd.DataFrame(keyword_records)

    print("Saving cleaned CSVs...")
    os.makedirs(CLEANED_DIR, exist_ok=True)
    
    movies_path = os.path.join(CLEANED_DIR, "movies_cleaned.csv")
    movie_genres_path = os.path.join(CLEANED_DIR, "movie_genres.csv")
    movie_keywords_path = os.path.join(CLEANED_DIR, "movie_keywords.csv")
    
    clean_movies.to_csv(movies_path, index=False)
    genres_df.to_csv(movie_genres_path, index=False)
    keywords_df.to_csv(movie_keywords_path, index=False)
    
    print(f"Success! Cleaned data saved appropriately.")
    print(f"Movies kept: {len(clean_movies)}")
    print(f"Genre mappings extracted: {len(genres_df)}")
    print(f"Keyword mappings extracted: {len(keywords_df)}")

if __name__ == "__main__":
    clean_data()
