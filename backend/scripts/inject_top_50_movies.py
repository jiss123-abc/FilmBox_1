import sqlite3

conn = sqlite3.connect("backend/filmbox.db")
c = conn.cursor()

# Master list of hardcoded data for the top 75 highest-voted missing movies
movies_to_fix = [
    # Top 5 we already did just in case
    {
        "search_title": "The Avengers",
        "director": "Joss Whedon",
        "cast": ["Robert Downey Jr.", "Chris Evans", "Mark Ruffalo", "Chris Hemsworth", "Scarlett Johansson", "Jeremy Renner", "Tom Hiddleston", "Samuel L. Jackson"],
        "genres": ["Science Fiction", "Action", "Adventure"],
        "keywords": ["superhero", "marvel cinematic universe", "alien invasion", "saving the world"]
    },
    {
        "search_title": "The Dark Knight",
        "director": "Christopher Nolan",
        "cast": ["Christian Bale", "Heath Ledger", "Aaron Eckhart", "Michael Caine", "Maggie Gyllenhaal", "Gary Oldman", "Morgan Freeman"],
        "genres": ["Action", "Crime", "Drama", "Thriller"],
        "keywords": ["dc comics", "crime fighter", "secret identity", "superhero", "gotham city"]
    },
    {
        "search_title": "Inception",
        "director": "Christopher Nolan",
        "cast": ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page", "Tom Hardy", "Ken Watanabe", "Cillian Murphy", "Marion Cotillard", "Michael Caine"],
        "genres": ["Action", "Science Fiction", "Adventure"],
        "keywords": ["dream", "subconscious", "heist", "philosophy"]
    },
    {
        "search_title": "Interstellar",
        "year": 2014,
        "director": "Christopher Nolan",
        "cast": ["Matthew McConaughey", "Anne Hathaway", "Jessica Chastain", "Michael Caine", "Casey Affleck", "Mackenzie Foy", "John Lithgow"],
        "genres": ["Adventure", "Drama", "Science Fiction"],
        "keywords": ["space travel", "astronaut", "black hole", "relativity", "time travel"]
    },
    {
        "search_title": "Joker",
        "year": 2019,
        "director": "Todd Phillips",
        "cast": ["Joaquin Phoenix", "Robert De Niro", "Zazie Beetz", "Frances Conroy", "Brett Cullen", "Shea Whigham", "Bill Camp"],
        "genres": ["Crime", "Thriller", "Drama"],
        "keywords": ["clown", "gotham city", "mental illness", "stand-up comedian", "social outcast"]
    },
    {
        "search_title": "Spider-Man: Into the Spider-Verse",
        "year": 2018,
        "director": "Bob Persichetti",
        "director2": "Peter Ramsey",
        "director3": "Rodney Rothman",
        "cast": ["Shameik Moore", "Jake Johnson", "Hailee Steinfeld", "Mahershala Ali", "Brian Tyree Henry", "Lily Tomlin", "Luna Lauren Velez"],
        "genres": ["Action", "Adventure", "Animation", "Science Fiction"],
        "keywords": ["superhero", "comic book", "spider-man", "alternate universe", "coming of age"]
    },
    {
        "search_title": "The Wolf of Wall Street",
        "year": 2013,
        "director": "Martin Scorsese",
        "cast": ["Leonardo DiCaprio", "Jonah Hill", "Margot Robbie", "Matthew McConaughey", "Kyle Chandler", "Rob Reiner", "Jon Bernthal"],
        "genres": ["Crime", "Drama", "Comedy"],
        "keywords": ["stockbroker", "corruption", "wall street", "based on a true story", "drug abuse"]
    },
    {
        "search_title": "The Matrix",
        "year": 1999,
        "director": "Lilly Wachowski",
        "director2": "Lana Wachowski",
        "cast": ["Keanu Reeves", "Laurence Fishburne", "Carrie-Anne Moss", "Hugo Weaving", "Joe Pantoliano", "Gloria Foster", "Marcus Chong"],
        "genres": ["Action", "Science Fiction"],
        "keywords": ["hacker", "virtual reality", "artificial intelligence", "simulation", "dystopia"]
    },
    {
        "search_title": "Django Unchained",
        "year": 2012,
        "director": "Quentin Tarantino",
        "cast": ["Jamie Foxx", "Christoph Waltz", "Leonardo DiCaprio", "Kerry Washington", "Samuel L. Jackson", "Walton Goggins", "Dennis Christopher"],
        "genres": ["Drama", "Western"],
        "keywords": ["slavery", "bounty hunter", "revenge", "plantation", "racism"]
    },
    {
        "search_title": "Pulp Fiction",
        "year": 1994,
        "director": "Quentin Tarantino",
        "cast": ["John Travolta", "Samuel L. Jackson", "Uma Thurman", "Bruce Willis", "Ving Rhames", "Harvey Keitel", "Tim Roth"],
        "genres": ["Thriller", "Crime"],
        "keywords": ["hitman", "nonlinear timeline", "drug overdose", "los angeles", "gangster"]
    },
    {
        "search_title": "Avengers: Infinity War",
        "year": 2018,
        "director": "Anthony Russo",
        "director2": "Joe Russo",
        "cast": ["Robert Downey Jr.", "Chris Hemsworth", "Mark Ruffalo", "Chris Evans", "Scarlett Johansson", "Benedict Cumberbatch", "Don Cheadle"],
        "genres": ["Adventure", "Action", "Science Fiction"],
        "keywords": ["superhero", "marvel cinematic universe", "infinity stones", "alien invasion"]
    },
    {
        "search_title": "The Hunger Games",
        "year": 2012,
        "director": "Gary Ross",
        "cast": ["Jennifer Lawrence", "Josh Hutcherson", "Liam Hemsworth", "Woody Harrelson", "Elizabeth Banks", "Lenny Kravitz", "Stanley Tucci"],
        "genres": ["Science Fiction", "Adventure", "Fantasy"],
        "keywords": ["dystopia", "survival", "death game", "based on novel", "post-apocalyptic"]
    },
    {
        "search_title": "Fight Club",
        "year": 1999,
        "director": "David Fincher",
        "cast": ["Edward Norton", "Brad Pitt", "Helena Bonham Carter", "Meat Loaf", "Jared Leto", "Zach Grenier", "Holt McCallany"],
        "genres": ["Drama"],
        "keywords": ["split personality", "underground fight club", "insomnia", "anarchism"]
    },
    {
        "search_title": "Forrest Gump",
        "year": 1994,
        "director": "Robert Zemeckis",
        "cast": ["Tom Hanks", "Robin Wright", "Gary Sinise", "Mykelti Williamson", "Sally Field", "Michael Conner Humphreys", "Hanna R. Hall"],
        "genres": ["Comedy", "Drama", "Romance"],
        "keywords": ["vietnam veteran", "running", "based on novel", "developmental disability", "shrimp"]
    },
    {
        "search_title": "The Lord of the Rings: The Fellowship of the Ring",
        "year": 2001,
        "director": "Peter Jackson",
        "cast": ["Elijah Wood", "Ian McKellen", "Viggo Mortensen", "Sean Astin", "Liv Tyler", "Sean Bean", "Cate Blanchett"],
        "genres": ["Adventure", "Fantasy", "Action"],
        "keywords": ["magic ring", "hobbit", "elf", "dwarf", "wizard"]
    },
    {
        "search_title": "Mad Max: Fury Road",
        "year": 2015,
        "director": "George Miller",
        "cast": ["Tom Hardy", "Charlize Theron", "Nicholas Hoult", "Hugh Keays-Byrne", "Josh Helman", "Nathan Jones", "Zoë Kravitz"],
        "genres": ["Action", "Adventure", "Science Fiction"],
        "keywords": ["post-apocalyptic", "dystopia", "desert", "car chase", "wasteland"]
    },
    {
        "search_title": "Guardians of the Galaxy",
        "year": 2014,
        "director": "James Gunn",
        "cast": ["Chris Pratt", "Zoe Saldaña", "Dave Bautista", "Vin Diesel", "Bradley Cooper", "Lee Pace", "Michael Rooker"],
        "genres": ["Action", "Science Fiction", "Adventure"],
        "keywords": ["marvel cinematic universe", "space", "bounty hunter", "raccoon", "alien"]
    },
    {
        "search_title": "Deadpool",
        "year": 2016,
        "director": "Tim Miller",
        "cast": ["Ryan Reynolds", "Morena Baccarin", "Ed Skrein", "T.J. Miller", "Gina Carano", "Leslie Uggams", "Brianna Hildebrand"],
        "genres": ["Action", "Adventure", "Comedy"],
        "keywords": ["superhero", "marvel comics", "fourth wall breaking", "mercenary", "mutant"]
    },
    {
        "search_title": "Avatar",
        "year": 2009,
        "director": "James Cameron",
        "cast": ["Sam Worthington", "Zoe Saldaña", "Sigourney Weaver", "Stephen Lang", "Michelle Rodriguez", "Giovanni Ribisi", "Joel David Moore"],
        "genres": ["Action", "Adventure", "Fantasy", "Science Fiction"],
        "keywords": ["alien", "space travel", "3d", "native population", "future"]
    },
    {
        "search_title": "Se7en",
        "year": 1995,
        "director": "David Fincher",
        "cast": ["Brad Pitt", "Morgan Freeman", "Gwyneth Paltrow", "Kevin Spacey", "R. Lee Ermey", "John C. McGinley", "Richard Roundtree"],
        "genres": ["Crime", "Mystery", "Thriller"],
        "keywords": ["serial killer", "seven deadly sins", "detective", "police", "gore"]
    },
    {
        "search_title": "Iron Man",
        "year": 2008,
        "director": "Jon Favreau",
        "cast": ["Robert Downey Jr.", "Terrence Howard", "Jeff Bridges", "Gwyneth Paltrow", "Leslie Bibb", "Shaun Toub", "Faran Tahir"],
        "genres": ["Action", "Science Fiction", "Adventure"],
        "keywords": ["superhero", "marvel cinematic universe", "weapons manufacturer", "powered armor"]
    },
    {
        "search_title": "Shutter Island",
        "year": 2010,
        "director": "Martin Scorsese",
        "cast": ["Leonardo DiCaprio", "Mark Ruffalo", "Ben Kingsley", "Max von Sydow", "Michelle Williams", "Emily Mortimer", "Patricia Clarkson"],
        "genres": ["Drama", "Thriller", "Mystery"],
        "keywords": ["mental institution", "island", "detective", "rainstorm", "1950s"]
    },
    {
        "search_title": "The Dark Knight Rises",
        "year": 2012,
        "director": "Christopher Nolan",
        "cast": ["Christian Bale", "Gary Oldman", "Tom Hardy", "Joseph Gordon-Levitt", "Anne Hathaway", "Marion Cotillard", "Morgan Freeman"],
        "genres": ["Action", "Crime", "Drama", "Thriller"],
        "keywords": ["dc comics", "crime fighter", "secret identity", "superhero", "gotham city", "terrorist"]
    },
    {
        "search_title": "Inglourious Basterds",
        "year": 2009,
        "director": "Quentin Tarantino",
        "cast": ["Brad Pitt", "Mélanie Laurent", "Christoph Waltz", "Eli Roth", "Michael Fassbender", "Diane Kruger", "Daniel Brühl"],
        "genres": ["Drama", "Action", "Thriller", "War"],
        "keywords": ["world war ii", "nazi", "assassination", "france", "paris"]
    },
    {
        "search_title": "Avengers: Endgame",
        "year": 2019,
        "director": "Anthony Russo",
        "director2": "Joe Russo",
        "cast": ["Robert Downey Jr.", "Chris Evans", "Mark Ruffalo", "Chris Hemsworth", "Scarlett Johansson", "Jeremy Renner", "Don Cheadle"],
        "genres": ["Adventure", "Science Fiction", "Action"],
        "keywords": ["superhero", "marvel cinematic universe", "time travel", "alien invasion"]
    },
    {
        "search_title": "The Shawshank Redemption",
        "year": 1994,
        "director": "Frank Darabont",
        "cast": ["Tim Robbins", "Morgan Freeman", "Bob Gunton", "William Sadler", "Clancy Brown", "Gil Bellows", "James Whitmore"],
        "genres": ["Drama", "Crime"],
        "keywords": ["prison", "corruption", "escape", "friendship", "wrongful imprisonment"]
    },
    {
        "search_title": "Catch Me If You Can",
        "year": 2002,
        "director": "Steven Spielberg",
        "cast": ["Leonardo DiCaprio", "Tom Hanks", "Christopher Walken", "Martin Sheen", "Nathalie Baye", "Amy Adams", "James Brolin"],
        "genres": ["Drama", "Crime"],
        "keywords": ["con man", "forgery", "fbi", "check fraud", "airline pilot"]
    },
    {
        "search_title": "Inside Out",
        "year": 2015,
        "director": "Pete Docter",
        "cast": ["Amy Poehler", "Phyllis Smith", "Richard Kind", "Bill Hader", "Lewis Black", "Mindy Kaling", "Kaitlyn Dias"],
        "genres": ["Animation", "Family", "Adventure", "Drama", "Comedy"],
        "keywords": ["emotion", "memory", "running away", "childhood", "mind"]
    },
    {
        "search_title": "Titanic",
        "year": 1997,
        "director": "James Cameron",
        "cast": ["Leonardo DiCaprio", "Kate Winslet", "Billy Zane", "Kathy Bates", "Frances Fisher", "Bernard Hill", "Jonathan Hyde"],
        "genres": ["Drama", "Romance"],
        "keywords": ["shipwreck", "titanic", "tragedy", "high society", "steerage"]
    },
    {
        "search_title": "Black Panther",
        "year": 2018,
        "director": "Ryan Coogler",
        "cast": ["Chadwick Boseman", "Michael B. Jordan", "Lupita Nyong\\'o", "Danai Gurira", "Martin Freeman", "Daniel Kaluuya", "Letitia Wright"],
        "genres": ["Action", "Adventure", "Science Fiction"],
        "keywords": ["marvel cinematic universe", "superhero", "african futurism", "king", "vibranium"]
    },
    {
        "search_title": "Spider-Man: No Way Home",
        "year": 2021,
        "director": "Jon Watts",
        "cast": ["Tom Holland", "Zendaya", "Benedict Cumberbatch", "Jacob Batalon", "Jon Favreau", "Jamie Foxx", "Willem Dafoe"],
        "genres": ["Action", "Adventure", "Science Fiction"],
        "keywords": ["marvel cinematic universe", "superhero", "multiverse", "magic", "high school"]
    },
    {
        "search_title": "The Truman Show",
        "year": 1998,
        "director": "Peter Weir",
        "cast": ["Jim Carrey", "Laura Linney", "Noah Emmerich", "Natascha McElhone", "Ed Harris", "Holland Taylor", "Brian Delate"],
        "genres": ["Comedy", "Drama"],
        "keywords": ["reality tv", "fake reality", "media satire", "simulation", "television"]
    },
    {
        "search_title": "Gladiator",
        "year": 2000,
        "director": "Ridley Scott",
        "cast": ["Russell Crowe", "Joaquin Phoenix", "Connie Nielsen", "Oliver Reed", "Richard Harris", "Derek Jacobi", "Djimon Hounsou"],
        "genres": ["Action", "Drama", "Adventure"],
        "keywords": ["ancient rome", "gladiator", "revenge", "emperor", "colosseum"]
    },
    {
        "search_title": "John Wick",
        "year": 2014,
        "director": "Chad Stahelski",
        "cast": ["Keanu Reeves", "Michael Nyqvist", "Alfie Allen", "Willem Dafoe", "Dean Winters", "Adrianne Palicki", "Omer Barnea"],
        "genres": ["Action", "Thriller"],
        "keywords": ["hitman", "revenge", "widower", "dog", "russian mafia"]
    },
    {
        "search_title": "Spider-Man",
        "year": 2002,
        "director": "Sam Raimi",
        "cast": ["Tobey Maguire", "Willem Dafoe", "Kirsten Dunst", "James Franco", "Cliff Robertson", "Rosemary Harris", "J.K. Simmons"],
        "genres": ["Action", "Adventure", "Science Fiction"],
        "keywords": ["superhero", "marvel comics", "spider-man", "mutant", "new york city"]
    },
    {
        "search_title": "Star Wars: The Force Awakens",
        "year": 2015,
        "director": "J.J. Abrams",
        "cast": ["Harrison Ford", "Mark Hamill", "Carrie Fisher", "Adam Driver", "Daisy Ridley", "John Boyega", "Oscar Isaac"],
        "genres": ["Action", "Adventure", "Science Fiction", "Fantasy"],
        "keywords": ["space opera", "sequel", "lightsaber", "spaceship", "battle"]
    },
    {
        "search_title": "Finding Nemo",
        "year": 2003,
        "director": "Andrew Stanton",
        "cast": ["Albert Brooks", "Ellen DeGeneres", "Alexander Gould", "Willem Dafoe", "Brad Garrett", "Allison Janney", "Austin Pendleton"],
        "genres": ["Animation", "Family"],
        "keywords": ["ocean", "fish", "father son relationship", "dentist", "great barrier reef"]
    },
    {
        "search_title": "Parasite",
        "year": 2019,
        "director": "Bong Joon-ho",
        "cast": ["Song Kang-ho", "Lee Sun-kyun", "Cho Yeo-jeong", "Choi Woo-shik", "Park So-dam", "Lee Jung-eun", "Jang Hye-jin"],
        "genres": ["Comedy", "Thriller", "Drama"],
        "keywords": ["class differences", "social commentary", "con artist", "basement", "poor family"]
    },
    {
        "search_title": "Logan",
        "year": 2017,
        "director": "James Mangold",
        "cast": ["Hugh Jackman", "Patrick Stewart", "Dafne Keen", "Boyd Holbrook", "Stephen Merchant", "Richard E. Grant", "Eriq La Salle"],
        "genres": ["Action", "Drama", "Science Fiction"],
        "keywords": ["mutant", "superhero", "marvel comics", "road trip", "x-men"]
    },
    {
        "search_title": "Harry Potter and the Deathly Hallows: Part 1",
        "year": 2010,
        "director": "David Yates",
        "cast": ["Daniel Radcliffe", "Rupert Grint", "Emma Watson", "Ralph Fiennes", "Helena Bonham Carter", "Robbie Coltrane", "Warwick Davis"],
        "genres": ["Adventure", "Fantasy"],
        "keywords": ["magic", "wizard", "witch", "dark lord", "part of a whole"]
    },
    {
        "search_title": "It",
        "year": 2017,
        "director": "Andy Muschietti",
        "cast": ["Jaeden Martell", "Bill Skarsgård", "Jeremy Ray Taylor", "Sophia Lillis", "Finn Wolfhard", "Wyatt Oleff", "Chosen Jacobs"],
        "genres": ["Horror", "Thriller"],
        "keywords": ["clown", "monster", "childhood trauma", "missing child", "balloon"]
    },
    {
        "search_title": "WALL·E",
        "year": 2008,
        "director": "Andrew Stanton",
        "cast": ["Ben Burtt", "Elissa Knight", "Jeff Garlin", "Fred Willard", "MacInTalk", "John Ratzenberger", "Kathy Najimy"],
        "genres": ["Animation", "Family", "Science Fiction"],
        "keywords": ["robot", "dystopia", "space", "environment", "future"]
    },
    {
        "search_title": "Gone Girl",
        "year": 2014,
        "director": "David Fincher",
        "cast": ["Ben Affleck", "Rosamund Pike", "Neil Patrick Harris", "Tyler Perry", "Carrie Coon", "Kim Dickens", "Patrick Fugit"],
        "genres": ["Mystery", "Thriller", "Drama"],
        "keywords": ["based on novel", "marriage", "missing person", "investigation", "manipulation"]
    },
    {
        "search_title": "Toy Story",
        "year": 1995,
        "director": "John Lasseter",
        "cast": ["Tom Hanks", "Tim Allen", "Don Rickles", "Jim Varney", "Wallace Shawn", "John Ratzenberger", "Annie Potts"],
        "genres": ["Animation", "Adventure", "Family", "Comedy"],
        "keywords": ["toy", "jealousy", "friendship", "boy", "bedroom"]
    },
    {
        "search_title": "Monsters, Inc.",
        "year": 2001,
        "director": "Pete Docter",
        "cast": ["John Goodman", "Billy Crystal", "Mary Gibbs", "Steve Buscemi", "James Coburn", "Jennifer Tilly", "Bob Peterson"],
        "genres": ["Animation", "Family", "Comedy"],
        "keywords": ["monster", "door", "little girl", "scream", "factory"]
    },
    {
        "search_title": "The Lion King",
        "year": 1994,
        "director": "Roger Allers",
        "director2": "Rob Minkoff",
        "cast": ["Matthew Broderick", "James Earl Jones", "Jeremy Irons", "Moira Kelly", "Nathan Lane", "Ernie Sabella", "Robert Guillaume"],
        "genres": ["Family", "Animation", "Drama"],
        "keywords": ["lion", "loss of father", "uncle", "musical", "africa"]
    },
    {
        "search_title": "The Revenant",
        "year": 2015,
        "director": "Alejandro G. Iñárritu",
        "cast": ["Leonardo DiCaprio", "Tom Hardy", "Domhnall Gleeson", "Will Poulter", "Forrest Goodluck", "Paul Anderson", "Kristoffer Joner"],
        "genres": ["Western", "Drama", "Adventure"],
        "keywords": ["survival", "revenge", "bear", "winter", "wilderness"]
    },
    {
        "search_title": "Arrival",
        "year": 2016,
        "director": "Denis Villeneuve",
        "cast": ["Amy Adams", "Jeremy Renner", "Forest Whitaker", "Michael Stuhlbarg", "Mark O\\'Brien", "Tzi Ma", "Abigail Pniowsky"],
        "genres": ["Science Fiction", "Drama"],
        "keywords": ["alien", "linguist", "communication", "time", "first contact"]
    },
    {
        "search_title": "Deadpool 2",
        "year": 2018,
        "director": "David Leitch",
        "cast": ["Ryan Reynolds", "Josh Brolin", "Morena Baccarin", "Julian Dennison", "Zazie Beetz", "T.J. Miller", "Leslie Uggams"],
        "genres": ["Action", "Comedy", "Adventure"],
        "keywords": ["marvel comics", "superhero", "mercenary", "time travel", "x-men"]
    },
    {
        "search_title": "The Green Mile",
        "year": 1999,
        "director": "Frank Darabont",
        "cast": ["Tom Hanks", "David Morse", "Bonnie Hunt", "Michael Clarke Duncan", "James Cromwell", "Michael Jeter", "Graham Greene"],
        "genres": ["Fantasy", "Drama", "Crime"],
        "keywords": ["prison", "death row", "supernatural power", "healing", "1930s"]
    },
    {
        "search_title": "Batman v Superman: Dawn of Justice",
        "year": 2016,
        "director": "Zack Snyder",
        "cast": ["Ben Affleck", "Henry Cavill", "Amy Adams", "Jesse Eisenberg", "Diane Lane", "Laurence Fishburne", "Jeremy Irons"],
        "genres": ["Action", "Adventure", "Fantasy"],
        "keywords": ["dc comics", "superhero", "clash", "vigilante", "alien"]
    },
    {
        "search_title": "The Incredibles",
        "year": 2004,
        "director": "Brad Bird",
        "cast": ["Craig T. Nelson", "Holly Hunter", "Samuel L. Jackson", "Jason Lee", "Dominique Louis", "Eli Fucile", "Maeve Andrews"],
        "genres": ["Action", "Adventure", "Animation", "Family"],
        "keywords": ["superhero", "secret identity", "family", "midlife crisis"]
    },
    {
        "search_title": "The Shining",
        "year": 1980,
        "director": "Stanley Kubrick",
        "cast": ["Jack Nicholson", "Shelley Duvall", "Danny Lloyd", "Scatman Crothers", "Barry Nelson", "Philip Stone", "Joe Turkel"],
        "genres": ["Horror", "Thriller"],
        "keywords": ["hotel", "isolation", "psychopath", "snow", "writer"]
    },
    {
        "search_title": "Kill Bill: Volume 1",
        "year": 2003,
        "director": "Quentin Tarantino",
        "cast": ["Uma Thurman", "Lucy Liu", "Vivica A. Fox", "Daryl Hannah", "David Carradine", "Michael Madsen", "Julie Dreyfus"],
        "genres": ["Action", "Crime"],
        "keywords": ["assassin", "revenge", "katana", "martial arts", "coma"]
    },
    {
        "search_title": "Get Out",
        "year": 2017,
        "director": "Jordan Peele",
        "cast": ["Daniel Kaluuya", "Allison Williams", "Bradley Whitford", "Catherine Keener", "Caleb Landry Jones", "Marcus Henderson", "Betty Gabriel"],
        "genres": ["Horror", "Thriller", "Mystery"],
        "keywords": ["racism", "hypnosis", "mind control", "suburbia", "dinner party"]
    },
    {
        "search_title": "Shrek",
        "year": 2001,
        "director": "Andrew Adamson",
        "director2": "Vicky Jenson",
        "cast": ["Mike Myers", "Eddie Murphy", "Cameron Diaz", "John Lithgow", "Vincent Cassel", "Peter Dennis", "Clive Pearse"],
        "genres": ["Animation", "Comedy", "Family", "Fantasy"],
        "keywords": ["ogre", "princes", "fairy tale", "dragon", "donkey"]
    },
    {
        "search_title": "The Amazing Spider-Man",
        "year": 2012,
        "director": "Marc Webb",
        "cast": ["Andrew Garfield", "Emma Stone", "Rhys Ifans", "Denis Leary", "Martin Sheen", "Sally Field", "Irrfan Khan"],
        "genres": ["Action", "Adventure", "Fantasy"],
        "keywords": ["marvel comics", "superhero", "high school", "reboot", "mutant"]
    }
]

def get_or_create_person(name):
    c.execute("SELECT id FROM people WHERE name = ?", (name.replace("\\'", "'"),))
    row = c.fetchone()
    if row: return row[0]
    c.execute("INSERT INTO people (name) VALUES (?)", (name.replace("\\'", "'"),))
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
    if "year" in data:
        c.execute("SELECT id, title FROM movies WHERE title = ? AND release_year = ?", (data["search_title"], data["year"]))
    else:
        c.execute("SELECT id, title FROM movies WHERE title = ?", (data["search_title"],))
        
    movie_rows = c.fetchall()
    
    for mrow in movie_rows:
        movie_id = mrow[0]
        title = mrow[1]
        
        # Insert Director
        d_id = get_or_create_person(data["director"])
        c.execute("INSERT OR IGNORE INTO movie_credits (movie_id, person_id, role) VALUES (?, ?, 'director')", (movie_id, d_id))
        
        for k in ["director2", "director3"]:
            if k in data:
                d2_id = get_or_create_person(data[k])
                c.execute("INSERT OR IGNORE INTO movie_credits (movie_id, person_id, role) VALUES (?, ?, 'director')", (movie_id, d2_id))
        
        # Insert Cast
        for i, actor_name in enumerate(data.get("cast", [])):
            p_id = get_or_create_person(actor_name)
            c.execute("""
                INSERT OR IGNORE INTO movie_credits (movie_id, person_id, role, character_name, cast_order)
                VALUES (?, ?, 'actor', '', ?)
            """, (movie_id, p_id, i))
            
        # Insert Genres
        for g in data.get("genres", []):
            g_id = get_or_create_genre(g)
            c.execute("INSERT OR IGNORE INTO movie_genres (movie_id, genre_id) VALUES (?, ?)", (movie_id, g_id))
            
        # Insert Keywords
        for k in data.get("keywords", []):
            k_id = get_or_create_keyword(k)
            c.execute("INSERT OR IGNORE INTO movie_keywords (movie_id, keyword_id) VALUES (?, ?)", (movie_id, k_id))
            
        print(f"✅ Injected manual data for: {title} (ID {movie_id})")
        fixed_count += 1

conn.commit()
conn.close()
print(f"Done! Fixed {fixed_count} popular movie entries with hardcoded data.")
