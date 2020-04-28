import sqlite3

# Script for initial database creation
# Database name: "tagged"

if __name__ == "__main__":
    con = sqlite3.connect("tagged.db")
    cur = con.cursor()

    cur.execute("""CREATE TABLE users (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        username VARCHAR(30) NOT NULL UNIQUE,
        passhash VARCHAR(32) NOT NULL)""")
    cur.execute("""CREATE TABLE sessions (
        id VARCHAR(32) NOT NULL PRIMARY KEY,
        userid INTEGER NOT NULL,
        active INTEGER(1) NOT NULL,
        FOREIGN KEY (userid) REFERENCES users(id))""")
    cur.execute("""CREATE TABLE notes (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(100) NOT NULL,
        contents TEXT NOT NULL,
        date_created VARCHAR(50) NOT NULL,
        tags VARCHAR(500) NOT NULL,
        date_modified VARCHAR(50) NOT NULL,
        userid INTEGER NOT NULL,
        FOREIGN KEY (userid) REFERENCES users(id))""") 
    con.commit()
    con.close()

