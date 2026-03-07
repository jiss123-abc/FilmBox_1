-- ============================================
-- FILMBOX — Relational Database Schema
-- Phase 1: Full Data Architecture
-- ============================================

-- ─── Lookup Tables (referenced by movies) ───

CREATE TABLE IF NOT EXISTS languages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    iso_code TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS certifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rating TEXT UNIQUE NOT NULL,
    description TEXT
);

-- ─── Core Movie Table ───

CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tmdb_id INTEGER UNIQUE,
    title TEXT NOT NULL,
    overview TEXT,
    release_year INTEGER,
    runtime INTEGER,
    vote_average REAL,
    vote_count INTEGER,
    popularity REAL,
    poster_path TEXT,
    backdrop_path TEXT,
    language_id INTEGER,
    certification_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (language_id) REFERENCES languages(id),
    FOREIGN KEY (certification_id) REFERENCES certifications(id)
);

-- ─── Genres ───

CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS movie_genres (
    movie_id INTEGER NOT NULL,
    genre_id INTEGER NOT NULL,
    PRIMARY KEY (movie_id, genre_id),
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(id)
);

-- ─── Keywords ───

CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS movie_keywords (
    movie_id INTEGER NOT NULL,
    keyword_id INTEGER NOT NULL,
    PRIMARY KEY (movie_id, keyword_id),
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
    FOREIGN KEY (keyword_id) REFERENCES keywords(id)
);

-- ─── People (Actors & Directors) ───

CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tmdb_id INTEGER UNIQUE,
    name TEXT NOT NULL,
    profile_path TEXT
);

CREATE TABLE IF NOT EXISTS movie_credits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id INTEGER NOT NULL,
    person_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('actor', 'director')),
    character_name TEXT,
    cast_order INTEGER,
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
    FOREIGN KEY (person_id) REFERENCES people(id)
);

-- ─── Countries ───

CREATE TABLE IF NOT EXISTS countries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    iso_code TEXT UNIQUE NOT NULL,
    continent TEXT
);

CREATE TABLE IF NOT EXISTS movie_countries (
    movie_id INTEGER NOT NULL,
    country_id INTEGER NOT NULL,
    PRIMARY KEY (movie_id, country_id),
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
    FOREIGN KEY (country_id) REFERENCES countries(id)
);

-- ─── Emotional Archetype Tags ───

CREATE TABLE IF NOT EXISTS emotional_archetype_tags (
    movie_id INTEGER NOT NULL,
    archetype TEXT NOT NULL,
    weight REAL,
    PRIMARY KEY (movie_id, archetype),
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
);

-- ─── User Interactions ───

CREATE TABLE IF NOT EXISTS user_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    movie_id INTEGER NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('liked','saved','clicked')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
);

-- ─── Performance Indexes ───

CREATE INDEX IF NOT EXISTS idx_movies_tmdb_id ON movies(tmdb_id);
CREATE INDEX IF NOT EXISTS idx_movies_popularity ON movies(popularity);
CREATE INDEX IF NOT EXISTS idx_movies_vote ON movies(vote_average);
CREATE INDEX IF NOT EXISTS idx_movies_language ON movies(language_id);
CREATE INDEX IF NOT EXISTS idx_movies_certification ON movies(certification_id);

CREATE INDEX IF NOT EXISTS idx_archetype_movie ON emotional_archetype_tags(movie_id);
CREATE INDEX IF NOT EXISTS idx_archetype_name ON emotional_archetype_tags(archetype);

CREATE INDEX IF NOT EXISTS idx_credits_movie ON movie_credits(movie_id);
CREATE INDEX IF NOT EXISTS idx_credits_person ON movie_credits(person_id);
CREATE INDEX IF NOT EXISTS idx_credits_role ON movie_credits(role);

CREATE INDEX IF NOT EXISTS idx_people_tmdb ON people(tmdb_id);

CREATE INDEX IF NOT EXISTS idx_session ON user_interactions(session_id);
CREATE INDEX IF NOT EXISTS idx_movies_year ON movies(release_year);
CREATE INDEX IF NOT EXISTS idx_movie_genres_id ON movie_genres(genre_id);
CREATE INDEX IF NOT EXISTS idx_movie_keywords_id ON movie_keywords(keyword_id);
