import sqlite3

conn = sqlite3.connect("backend/filmbox.db")
c = conn.cursor()

movies_to_fix = [
    {
        "search_title": "The Avengers",
        "director": "Joss Whedon",
        "cast": [
            ("Robert Downey Jr.", "Tony Stark / Iron Man"),
            ("Chris Evans", "Steve Rogers / Captain America"),
            ("Mark Ruffalo", "Bruce Banner / Hulk"),
            ("Chris Hemsworth", "Thor"),
            ("Scarlett Johansson", "Natasha Romanoff / Black Widow"),
            ("Jeremy Renner", "Clint Barton / Hawkeye"),
            ("Tom Hiddleston", "Loki"),
            ("Samuel L. Jackson", "Nick Fury")
        ],
        "genres": ["Science Fiction", "Action", "Adventure"],
        "keywords": ["superhero", "marvel cinematic universe", "alien invasion", "saving the world"]
    },
    {
        "search_title": "The Dark Knight",
        "director": "Christopher Nolan",
        "cast": [
            ("Christian Bale", "Bruce Wayne / Batman"),
            ("Heath Ledger", "Joker"),
            ("Aaron Eckhart", "Harvey Dent / Two-Face"),
            ("Michael Caine", "Alfred Pennyworth"),
            ("Maggie Gyllenhaal", "Rachel Dawes"),
            ("Gary Oldman", "James Gordon"),
            ("Morgan Freeman", "Lucius Fox")
        ],
        "genres": ["Action", "Crime", "Drama", "Thriller"],
        "keywords": ["dc comics", "crime fighter", "secret identity", "superhero", "gotham city"]
    },
    {
        "search_title": "Inception",
        "director": "Christopher Nolan",
        "cast": [
            ("Leonardo DiCaprio", "Dom Cobb"),
            ("Joseph Gordon-Levitt", "Arthur"),
            ("Elliot Page", "Ariadne"),
            ("Tom Hardy", "Eames"),
            ("Ken Watanabe", "Saito"),
            ("Cillian Murphy", "Robert Fischer"),
            ("Marion Cotillard", "Mal Cobb"),
            ("Michael Caine", "Prof. Stephen Miles")
        ],
        "genres": ["Action", "Science Fiction", "Adventure"],
        "keywords": ["dream", "subconscious", "heist", "philosophy"]
    },
    {
        "search_title": "The Matrix",
        "director": "Lilly Wachowski",
        "director2": "Lana Wachowski",
        "cast": [
            ("Keanu Reeves", "Neo"),
            ("Laurence Fishburne", "Morpheus"),
            ("Carrie-Anne Moss", "Trinity"),
            ("Hugo Weaving", "Agent Smith"),
            ("Joe Pantoliano", "Cypher")
        ],
        "genres": ["Action", "Science Fiction"],
        "keywords": ["saving the world", "artificial intelligence", "dystopia", "simulation"]
    },
    {
        "search_title": "Avengers: Age of Ultron",
        "director": "Joss Whedon",
        "cast": [
            ("Robert Downey Jr.", "Tony Stark / Iron Man"),
            ("Chris Hemsworth", "Thor"),
            ("Mark Ruffalo", "Bruce Banner / Hulk"),
            ("Chris Evans", "Steve Rogers / Captain America"),
            ("Scarlett Johansson", "Natasha Romanoff / Black Widow")
        ],
        "genres": ["Action", "Adventure", "Science Fiction"],
        "keywords": ["artificial intelligence", "superhero", "marvel cinematic universe"]
    }
]

def get_or_create_person(name):
    c.execute("SELECT id FROM people WHERE name = ?", (name,))
    row = c.fetchone()
    if row: return row[0]
    c.execute("INSERT INTO people (name) VALUES (?)", (name,))
    return c.lastrowid

def get_or_create_genre(name):
    c.execute("SELECT id FROM genres WHERE name = ?", (name.lower(),))
    row = c.fetchone()
    if row: return row[0]
    c.execute("INSERT INTO genres (name) VALUES (?)", (name.lower(),))
    return c.lastrowid

def get_or_create_keyword(name):
    c.execute("SELECT id FROM keywords WHERE name = ?", (name.lower(),))
    row = c.fetchone()
    if row: return row[0]
    c.execute("INSERT INTO keywords (name) VALUES (?)", (name.lower(),))
    return c.lastrowid

fixed_count = 0
for data in movies_to_fix:
    c.execute("SELECT id, title FROM movies WHERE title = ?", (data["search_title"],))
    movie_rows = c.fetchall()
    
    for mrow in movie_rows:
        movie_id = mrow[0]
        title = mrow[1]
        
        # Insert Director
        d_id = get_or_create_person(data["director"])
        c.execute("INSERT OR IGNORE INTO movie_credits (movie_id, person_id, role) VALUES (?, ?, 'director')", (movie_id, d_id))
        
        if "director2" in data:
            d2_id = get_or_create_person(data["director2"])
            c.execute("INSERT OR IGNORE INTO movie_credits (movie_id, person_id, role) VALUES (?, ?, 'director')", (movie_id, d2_id))
        
        # Insert Cast
        for i, (actor_name, char_name) in enumerate(data["cast"]):
            p_id = get_or_create_person(actor_name)
            c.execute("""
                INSERT OR IGNORE INTO movie_credits (movie_id, person_id, role, character_name, cast_order)
                VALUES (?, ?, 'actor', ?, ?)
            """, (movie_id, p_id, char_name, i))
            
        # Insert Genres
        for g in data["genres"]:
            g_id = get_or_create_genre(g)
            c.execute("INSERT OR IGNORE INTO movie_genres (movie_id, genre_id) VALUES (?, ?)", (movie_id, g_id))
            
        # Insert Keywords
        for k in data["keywords"]:
            k_id = get_or_create_keyword(k)
            c.execute("INSERT OR IGNORE INTO movie_keywords (movie_id, keyword_id) VALUES (?, ?)", (movie_id, k_id))
            
        print(f"✅ Injected manual data for: {title} (ID {movie_id})")
        fixed_count += 1

conn.commit()
conn.close()
print(f"Done! Fixed {fixed_count} popular movie entries.")
