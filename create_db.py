import sqlite3 as sq

conn = sq.connect('anime.sqlite3')

with open('db.sql') as f:
    conn.executescript(f.read())

conn.close()