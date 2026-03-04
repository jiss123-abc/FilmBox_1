-- Core Tables

CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    overview TEXT,
    release_year INTEGER,
    runtime INTEGER,
    popularity REAL,
    vote_average REAL,
    vote_count INTEGER
);

CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS movie_genres (
    movie_id INTEGER,
    genre_id INTEGER,
    PRIMARY KEY (movie_id, genre_id),
    FOREIGN KEY (movie_id) REFERENCES movies(id),
    FOREIGN KEY (genre_id) REFERENCES genres(id)
);

CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS movie_keywords (
    movie_id INTEGER,
    keyword_id INTEGER,
    PRIMARY KEY (movie_id, keyword_id),
    FOREIGN KEY (movie_id) REFERENCES movies(id),
    FOREIGN KEY (keyword_id) REFERENCES keywords(id)
);

-- Emotional Mapping Table
CREATE TABLE IF NOT EXISTS emotional_archetype_tags (
    movie_id INTEGER,
    archetype TEXT NOT NULL,
    weight REAL,
    PRIMARY KEY (movie_id, archetype),
    FOREIGN KEY (movie_id) REFERENCES movies(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_popularity ON movies(popularity);
CREATE INDEX IF NOT EXISTS idx_vote ON movies(vote_average);
CREATE INDEX IF NOT EXISTS idx_archetype ON emotional_archetype_tags(archetype);
