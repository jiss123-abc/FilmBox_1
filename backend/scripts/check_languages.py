import sqlite3
import os

db_path = os.path.join("d:\\Filmbox", "backend", "filmbox.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check movies linked to Malayalam language
cursor.execute('''
    SELECT COUNT(*) 
    FROM movies m 
    JOIN languages l ON m.language_id = l.id 
    WHERE LOWER(l.name) LIKE '%malayalam%' OR LOWER(l.iso_code) = 'ml'
''')
count = cursor.fetchone()[0]
print(f"Total Malayalam movies in database: {count}")

# Let's also check what languages are available that start with 'm'
cursor.execute('''
    SELECT name, iso_code, COUNT(m.id) as movie_count
    FROM languages l
    LEFT JOIN movies m ON m.language_id = l.id
    WHERE LOWER(l.name) LIKE 'm%'
    GROUP BY l.id
    ORDER BY movie_count DESC
    LIMIT 10
''')
print("\nTop languages starting with 'M':")
for row in cursor.fetchall():
    print(f"- {row[0]} ({row[1]}): {row[2]} movies")

conn.close()
