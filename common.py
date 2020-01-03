# common functions used by blueprints

import flask
import mysql.connector
import random
import json
from contextlib import contextmanager

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "1234"
DB_NAME = "tagged"

# make a new connection to database
def get_connection():
    con = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        passwd=DB_PASSWORD,
        database=DB_NAME
    )
    return con

# a context manager (with-block) for database connection
@contextmanager
def get_con():
    con = None
    try:
        con = get_connection()
        yield con
    finally:
        if con is not None:
            con.close()

# fetches one row from MySQL cursor object
# makes a dict from it
def fetchone_as_dict(cur):
    colnames = cur.column_names
    row = dict(zip(colnames, cur.fetchone()))
    return row

# fetches all rows from MySQL cursor object
# makes a list of dicts from it
def fetchall_as_dict(cur):
    colnames = cur.column_names
    rows = []
    for row in cur.fetchall():
        row = dict(zip(colnames, row))
        rows.append(row)
    return rows

# generate a session token
# a token is a string of 20 alphanumeric chars
# TODO: replace random.choice() with more cryptographically safe algorithm
TOKEN_LENGTH = 20
TOKEN_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
def gen_session_token():
    token = []
    for _ in range(TOKEN_LENGTH):
        c = random.choice(TOKEN_CHARS)
        token.append(c)
    return "".join(token)

# validate tag or keyword when creating/changing/searching notes
# a tag/keyword can only contain letters, digits, underline, or hyphon.
def validate_tag(tag):
    if not tag:
        return False
    for c in tag:
        if not (c in "_-" or c.isalnum()):
            return False
    return True

# a valid username is non-empty alphanumeric (or -/_) string
def validate_username(username):
    if not username:
        return False
    for c in username:
        if not (c in "_-" or c.isalnum()):
            return False
    return True

# check if "needles" is a subset of "hay"
def contains_all(hay, needles):
    for needle in needles:
        if needle not in hay:
            return False
    return True

