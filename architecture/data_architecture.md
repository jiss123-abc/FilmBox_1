# Data Architecture

FilmBox relies on structured, normalized movie metadata to drive deterministic scoring.

## Database Schema & Tables

### 1. `movies`
Stores core emotion-neutral and operational metadata.
- `id` (Primary Key)
- `title` (String)
- `release_year` (Integer)
- `runtime` (Integer, minutes)
- `popularity` (Float)
- `vote_average` (Float, 0-10)
- `vote_count` (Integer)

### 2. `genres`
Stores the fixed taxonomy of movie genres.
- `id` (Primary Key)
- `name` (String, e.g., "Action", "Drama")

### 3. `movie_genres`
Mapping table for the many-to-many relationship between movies and genres.
- `movie_id` (Foreign Key -> movies.id)
- `genre_id` (Foreign Key -> genres.id)

### 4. `keywords`
Stores descriptive tags for semantic context.
- `id` (Primary Key)
- `name` (String, e.g., "space travel", "revenge")

### 5. `movie_keywords`
Mapping table for the many-to-many relationship between movies and keywords.
- `movie_id` (Foreign Key -> movies.id)
- `keyword_id` (Foreign Key -> keywords.id)

## Relationships & Normalization
- All data is structured in **3rd Normal Form (3NF)**.
- Many-to-many relationships are resolved using bridging tables (`movie_genres`, `movie_keywords`).
- Foreign key constraints ensure referential integrity, avoiding orphaned mapping entries. 

## Index Strategy
- **Primary Indexes** on all `id` fields.
- **Foreign Key Indexes** on `movie_genres(movie_id, genre_id)` and `movie_keywords(movie_id, keyword_id)` to speed up join operations filtering by archetype.
- **Performance Indexes** on `movies(vote_average, popularity, vote_count)` to optimize base score computation across large query sets.

## Why No Collaborative Filtering?
FilmBox is designed to be an explainable, intent-driven engine rather than a mass-behavior-driven one. Collaborative filtering (e.g. matrix factorization) introduces "black-box" recommendations based on hidden user similarity vectors. This violates the core design philosophy of deterministic and mathematically decomposable recommendation logic.
