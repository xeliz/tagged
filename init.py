import mysql.connector

# Script for initializing database
# It creates the databasse named "tagged" and table "notes"
# MySQL is used

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "1234"

if __name__ == "__main__":
    con = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        passwd=DB_PASSWORD)
    cur = con.cursor()

    cur.execute("""CREATE DATABASE IF NOT EXISTS tagged""")
    cur.execute("""USE tagged""")
    cur.execute("""CREATE TABLE IF NOT EXISTS notes (
        id INTEGER NOT NULL AUTO_INCREMENT,
        title VARCHAR(100) NOT NULL,
        contents TEXT NOT NULL,
        date_created DATETIME NOT NULL,
        tags VARCHAR(500) NOT NULL,
        date_modified DATETIME NOT NULL,
        userid INTEGER NOT NULL,
        FOREIGN KEY (userid) REFERENCES users(id),
        PRIMARY KEY(id))""")
    cur.execute("""CREATE TABLE users (
        id INTEGER NOT NULL AUTO_INCREMENT,
        username VARCHAR(30) NOT NULL UNIQUE,
        passhash VARCHAR(32) NOT NULL,
        PRIMARY KEY(id))""")
    cur.execute("""CREATE TABLE sessions (
        id VARCHAR(32) NOT NULL UNIQUE,
        userid INTEGER NOT NULL,
        active BOOLEAN NOT NULL,
        FOREIGN KEY (userid) REFERENCES users(id),
        PRIMARY KEY(id))""")
    con.commit()
    con.close()
