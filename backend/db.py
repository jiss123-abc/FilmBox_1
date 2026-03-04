import sqlite3

def get_db_connection():
    # Placeholder for database connection logic
    # Use relative path from project root
    conn = sqlite3.connect('backend/filmbox.db')
    conn.row_factory = sqlite3.Row
    return conn
