import mysql.connector
import json

# Script for exporting tagged database to json files

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "1234"
DB_NAME = "tagged"

def connect():
    con = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        passwd=DB_PASSWORD,
        database=DB_NAME
    )
    return con

def json_preprocess_table(table_data):
    def preprocess_table_cell(cell):
        if any((isinstance(cell, int), isinstance(cell, float), isinstance(cell, bool), isinstance(cell, str), isinstance(cell, type(None)))):
            return cell
        return str(cell)

    for i, row in enumerate(table_data):
        table_data[i] = [preprocess_table_cell(item) for item in row]

if __name__ == "__main__":
    con = connect()
    cur = con.cursor()

    cur.execute("SELECT id, userid, active FROM SESSIONS")
    with open("SESSIONS.json", encoding="UTF-8", mode="w") as fout:
        data = cur.fetchall()
        json_preprocess_table(data)
        json.dump(data, fout, ensure_ascii=False)

    cur.execute("SELECT id, username, passhash FROM USERS")
    with open("USERS.json", encoding="UTF-8", mode="w") as fout:
        data = cur.fetchall()
        json_preprocess_table(data)
        json.dump(data, fout, ensure_ascii=False)

    cur.execute("SELECT id, title, contents, date_created, tags, date_modified, userid FROM NOTES")
    with open("USERS.json", encoding="UTF-8", mode="w") as fout:
        data = cur.fetchall()
        json_preprocess_table(data)
        json.dump(data, fout, ensure_ascii=False)

    cur.close()
    con.close()

