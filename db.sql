CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(16) NOT NULL,
    password VARCHAR(32) NOT NULL
);