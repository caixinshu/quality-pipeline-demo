import os
import sqlite3
import tempfile

DB_PATH = os.path.join(tempfile.gettempdir(), "test_demo.db")
os.environ["DB_PATH"] = DB_PATH

conn = sqlite3.connect(DB_PATH)
conn.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL)")
conn.commit()
conn.close()
