import sqlite3

DB_PATH = "backend/filmbox.db"
# A high-quality placeholder from TMDB (Interstellar)
PLACEHOLDER_PATH = "/gEU2QniE6EUnU0FFm6TBAoK6SOS.jpg" 

def set_placeholders():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("🛠️ Setting high-quality cinematic placeholders...")

    # Ensure column exists
    try:
        cursor.execute("ALTER TABLE movies ADD COLUMN poster_path TEXT")
    except sqlite3.OperationalError:
        pass

    cursor.execute("UPDATE movies SET poster_path = ?", (PLACEHOLDER_PATH,))
    
    conn.commit()
    conn.close()
    print("✅ All movies updated with cinematic placeholders.")

if __name__ == "__main__":
    set_placeholders()
