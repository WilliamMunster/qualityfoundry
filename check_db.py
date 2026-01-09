import sqlite3
import os

files = [
    'qualityfoundry.db',
    'backend/qualityfoundry.db'
]

for f in files:
    path = os.path.abspath(f)
    print(f"Checking: {path}")
    if os.path.exists(path):
        try:
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
            print(f"  Tables: {tables}")
            conn.close()
        except Exception as e:
            print(f"  Error: {e}")
    else:
        print("  File not found")
