# common functions used by blueprints

import flask
import mysql.connector
import random
import json

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "1234"
DB_NAME = "tagged"

con = cur = None

def init_mysql():
    global con, cur
    # connect to database
    con = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        passwd=DB_PASSWORD,
        database=DB_NAME
    )
    # get cursor
    cur = con.cursor()

# make a new connection to database
def get_connection():
    con = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        passwd=DB_PASSWORD,
        database=DB_NAME
    )
    return con

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

# returns user data from database if signed in
# otherwise, returns None
# might be used to check if user is logined
def userdata_if_logined():
    if not con.is_connected():
        init_mysql()
    # get session token from cookies
    if "session_token" not in flask.request.cookies:
        return None
    token = flask.request.cookies.get("session_token")
    # get user data from database
    query = """SELECT userid, username, passhash FROM sessions, users WHERE sessions.active = TRUE AND sessions.userid = users.id AND sessions.id = %s"""
    cur.execute(query, (token,))
    userdata = fetchall_as_dict(cur)
    # if token was wrong, no rows are returned
    if not userdata:
        return None
    # otherwise, a single row is returned
    userdata = userdata[0]
    return userdata

# login user:
# - generate token
# - update sessions table
# - set cookie
# - redirect to profile page
def login_user(userid):
    if not con.is_connected():
        init_mysql()
    # generate unique session token
    query = """SELECT id FROM sessions WHERE id = %s"""
    while True:
        token = gen_session_token()
        cur.execute(query, (token,))
        if not cur.fetchall():
            break
    query = """INSERT INTO sessions (id, userid, active) VALUES (%s, %s, TRUE)"""
    cur.execute(query, (token, userid))
    con.commit()
    resp = flask.make_response(flask.redirect(flask.url_for("notesapp.index_page")))
    resp.set_cookie("session_token", token)
    return resp

# unlogin user:
# - unset cookie
# - update session table if the param is True
# - redirect to login page
def unlogin_user(deactivateSession=True):
    if not con.is_connected():
        init_mysql()
    resp = flask.make_response(flask.redirect(flask.url_for("authapp.login_page")))
    if "session_token" in flask.request.cookies:
        token = flask.request.cookies.get("session_token")
        if deactivateSession:
            query = """UPDATE sessions SET active = FALSE where id = %s"""
            cur.execute(query, (token,))
            con.commit()
        resp.set_cookie("session_token", "", expires=0)
    return resp

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

# make JSON response from Python object and return it
def json_response(obj, success=True):
    obj["success"] = success
    resp = flask.make_response(json.dumps(obj))
    resp.mimetype = "application/json"
    return resp

# returns user data from database by given token if successful
# otherwise, returns None
def userdata_by_token(token):
    if not con.is_connected():
        init_mysql()
    # get user data from database
    query = """SELECT userid, username, passhash FROM sessions, users WHERE sessions.active = TRUE AND sessions.userid = users.id AND sessions.id = %s"""
    cur.execute(query, (token,))
    userdata = fetchall_as_dict(cur)
    # if token was wrong, no rows are returned
    if not userdata:
        return None
    # otherwise, a single row is returned
    return userdata[0]

