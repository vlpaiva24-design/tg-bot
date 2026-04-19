import sqlite3

conn = sqlite3.connect("data.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    phone TEXT,
    type TEXT,
    branch TEXT,
    text TEXT
)
""")

conn.commit()


def save_request(user_id, name, phone, req_type, branch, text):
    cursor.execute("""
    INSERT INTO requests (user_id, name, phone, type, branch, text)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, name, phone, req_type, branch, text))
    conn.commit()