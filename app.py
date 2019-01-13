import flask
import mysql.connector
import html
import datetime
import urllib.parse
import random
import hashlib
import base64
import json

# --- Common functions --------------------------------------------------------

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "1234"
DB_NAME = "tagged"

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

init_mysql()

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
    resp = flask.make_response(flask.redirect(flask.url_for("index_page")))
    resp.set_cookie("session_token", token)
    return resp

# unlogin user:
# - unset cookie
# - update session table if the param is True
# - redirect to login page
def unlogin_user(deactivateSession=True):
    if not con.is_connected():
        init_mysql()
    resp = flask.make_response(flask.redirect(flask.url_for("login_page")))
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

# --- Flask application -------------------------------------------------------

# --- Website pages -----------------------------------------------------------

# create flask app
app = flask.Flask(__name__)

# template filter "escapeurl"
# it is used for encoding generated urls in templates
@app.template_filter("escapeurl")
def escapeurl_filter(s):
    return urllib.parse.quote_plus(s)

# template filter "raw2html"
# it makes some replacements in raw database contents
# such as "<" -> "&lt;"; "\n" -> "<br>", etc
@app.template_filter("raw2html")
def escapeurl_filter(s):
    s = html.escape(s)
    s = s.replace("\n", "<br>")
    return s

# main page: recent notes
@app.route("/")
def index_page():
    if not con.is_connected():
        init_mysql()
    userdata = userdata_if_logined()
    if not userdata:
        return unlogin_user(False)
    result = cur.execute("SELECT id,title,contents,date_created,tags,date_modified FROM notes WHERE userid=%s ORDER BY date_modified DESC LIMIT 10", (userdata["userid"],))
    notes = fetchall_as_dict(cur)
    # notes = cur.fetchall()
    return flask.render_template("index.html", notes=notes)

# new note page: add new note
@app.route("/new", methods=["GET", "POST"])
def new_page():
    if not con.is_connected():
        init_mysql()
    userdata = userdata_if_logined()
    if not userdata:
        return unlogin_user(False)
    if flask.request.method == "GET":
        return flask.render_template("new.html")
    elif flask.request.method == "POST":
        if not contains_all(flask.request.form, ("title", "contents", "tags")):
            return flask.render_template("message.html", message="Неправильный запрос")
        title = flask.request.form.get("title", "")
        contents = flask.request.form.get("contents", "")
        rawTags = flask.request.form.get("tags", "").strip()
        tagList = rawTags.split()
        for tag in tagList:
            if not validate_tag(tag):
                return flask.render_template("message.html", message="Ошибка: метка может содержать только буквы, цифры, нижнее подчёркивание (_) или дефис(-)")
        tags = " ".join(tagList)
        curdt = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
        query = "INSERT INTO notes(title,contents,date_created,tags,date_modified,userid)VALUES(%s,%s,%s,%s,%s,%s)"
        cur.execute(query, (title, contents, curdt, tags, curdt, userdata["userid"]))
        con.commit()
        return flask.redirect(flask.url_for("note_noteid_page", noteid=cur.lastrowid))
    else:
        return flask.render_template("message.html", message="Метод не поддерживается")

# all notes page
@app.route("/all")
def all_page():
    if not con.is_connected():
        init_mysql()
    userdata = userdata_if_logined()
    if not userdata:
        return unlogin_user(False)
    result = cur.execute("SELECT id,title,contents,date_created,tags,date_modified FROM notes WHERE userid=%s ORDER BY date_modified DESC", (userdata["userid"],))
    notes = fetchall_as_dict(cur)
    return flask.render_template("all.html", notes=notes)

# search page
@app.route("/search")
def search_page():
    userdata = userdata_if_logined()
    if not userdata:
        return unlogin_user(False)
    return flask.render_template("search.html")

# search results page
@app.route("/search/results")
def search_results_page():
    if not con.is_connected():
        init_mysql()
    userdata = userdata_if_logined()
    if not userdata:
        return unlogin_user(False)
    rawKeywords = flask.request.args.get("keywords", "").strip()
    rawTags = flask.request.args.get("tags", "").strip()
    if rawKeywords == "" and rawTags == "":
        return flask.render_template("message.html", message="Неправильные параметры поиска")
    keywords = rawKeywords.split()
    tags = rawTags.split()
    for tag in tags:
        if not validate_tag(tag):
            return flask.render_template("message.html", message="Неправильные параметры поиска")
    for keyword in keywords :
        if not validate_tag(keyword):
            return flask.render_template("message.html", message="Неправильные параметры поиска")
    keywordsLike = list(map(lambda k: ["%" + k + "%"]*2, keywords))
    keywordsLike1 = []
    for keywordLike in keywordsLike:
        keywordsLike1.extend(keywordLike)
    keywordsLike = keywordsLike1
    tagsLike = list(map(lambda t: "%" + t + "%", tags))
    queryParts = ["SELECT id,title,contents,date_created,tags,date_modified FROM notes WHERE userid=%s"]
    if keywords or tags:
        queryParts.append(" AND ")
    if keywords:
        queryParts.append("(" + "OR".join(["(title LIKE %s OR contents LIKE %s)"] * len(keywords)) + ")")
        if tags:
            queryParts.append(" AND ")
    if tags:
        queryParts.append("(" + "OR".join(["(tags LIKE %s)"] * len(tags)) + ")")
    query = "".join(queryParts)
    cur.execute(query, [userdata["userid"]] + keywordsLike + tagsLike)
    notes = fetchall_as_dict(cur)
    return flask.render_template("search_results.html", keywords=keywords, tags=tags, notes=notes)

# delete page
@app.route("/delete/<int:noteid>", methods=["GET", "POST"])
def delete_noteid_page(noteid):
    if not con.is_connected():
        init_mysql()
    userdata = userdata_if_logined()
    if not userdata:
        return unlogin_user(False)

    query = """SELECT userid FROM notes WHERE userid=%s AND id=%s"""
    cur.execute(query, (userdata["userid"], noteid))
    if not fetchall_as_dict(cur):
        return flask.render_template("message.html", message="Вы не можете удалить чужую заметку")

    if flask.request.method == "GET":
        return flask.render_template("delete_noteid.html", noteid=noteid)
    elif flask.request.method == "POST":
        query = "DELETE FROM notes WHERE id=%s"
        cur.execute(query, (noteid,))
        con.commit()
        return flask.render_template("message.html", message="Удалено")
    else:
        return flask.render_template("message.html", message="Метод не поддерживается")

# specific note page
@app.route("/note/<int:noteid>")
def note_noteid_page(noteid):
    if not con.is_connected():
        init_mysql()
    userdata = userdata_if_logined()
    if not userdata:
        return unlogin_user(False)
    query = "SELECT id,title,tags,contents,date_created,date_modified FROM notes WHERE id=%s AND userid=%s"
    cur.execute(query, (noteid, userdata["userid"]))
    result = fetchall_as_dict(cur)
    if not result:
        return flask.render_template("message.html", message="Заметка не существует")
    note = result[0]
    return flask.render_template("note_noteid.html", note=note)

# note editing page
@app.route("/edit/<int:noteid>", methods=["GET", "POST"])
def edit_noteid_page(noteid):
    if not con.is_connected():
        init_mysql()
    userdata = userdata_if_logined()
    if not userdata:
        return unlogin_user(False)

    query = """SELECT userid FROM notes WHERE userid=%s AND id=%s"""
    cur.execute(query, (userdata["userid"], noteid))
    if not fetchall_as_dict(cur):
        return flask.render_template("message.html", message="Заметка не существует")

    if flask.request.method == "GET":
        query = "SELECT title,contents,tags FROM notes WHERE id=%s"
        cur.execute(query, (noteid,))
        note = fetchone_as_dict(cur)
        return flask.render_template("edit_noteid.html", note=note)
    elif flask.request.method == "POST":
        if not contains_all(flask.request.form, ("title", "contents", "tags")):
            return flask.render_template("message.html", message="Неправильный запрос")
        title = flask.request.form.get("title", "")
        contents = flask.request.form.get("contents", "")
        rawTags = flask.request.form.get("tags", "").strip()
        tagList = rawTags.split()
        for tag in tagList:
            if not validate_tag(tag):
                return flask.render_template("message.html", message="Ошибка: метка может содержать только буквы, цифры, нижнее подчёркивание (_) или дефис(-)")
        tags = " ".join(tagList)
        curdt = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
        query = "UPDATE notes SET title=%s,contents=%s,tags=%s,date_modified=%s WHERE id=%s"
        cur.execute(query, (title, contents, tags, curdt, noteid))
        con.commit()
        return flask.redirect(flask.url_for("note_noteid_page", noteid=noteid))
    else:
        return flask.render_template("message.html", message="Метод не поддерживается")

# sign in page
@app.route("/login", methods=["GET", "POST"])
def login_page():
    if not con.is_connected():
        init_mysql()
    if "session_token" in flask.request.cookies:
        return flask.redirect(flask.url_for("profile_page"))

    if flask.request.method == "GET":
        return flask.render_template("login.html")
    elif flask.request.method == "POST":
        if not contains_all(flask.request.form, ("username", "password")):
            return flask.render_template("unauthorizedmessage.html", message="Неправильный запрос")

        # check if user exists
        username = flask.request.form.get("username")
        query = """SELECT id, passhash FROM users WHERE username = %s"""
        cur.execute(query, (username,))
        userdata = fetchall_as_dict(cur)
        if not userdata:
            return flask.render_template("unauthorizedmessage.html", message="Такой пользователь не зарегистрирован")
        userdata = userdata[0]

        # check if passwords match
        password = flask.request.form.get("password")
        passhash = base64.b64encode(hashlib.md5(password.encode("UTF-8")).digest()).decode("UTF-8")
        if userdata["passhash"] != passhash:
            return flask.render_template("unauthorizedmessage.html", message="Неверный пароль")

        return login_user(userdata["id"]) 
    else:
        return flask.render_template("unauthorizedmessage.html", message="Метод не поддерживается")

# profile page
@app.route("/profile")
def profile_page():
    if not con.is_connected():
        init_mysql()
    userdata = userdata_if_logined()
    if not userdata:
        return unlogin_user(False)
    return flask.render_template("profile.html", userdata=userdata)

# logout page
@app.route("/logout")
def logout_page():
    if not con.is_connected():
        init_mysql()
    return unlogin_user()

# sign up page
@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    if not con.is_connected():
        init_mysql()
    userdata = userdata_if_logined()
    if userdata:
        return flask.redirect(flask.url_for("/"))
    if flask.request.method == "GET":
        return flask.render_template("signup.html")
    elif flask.request.method == "POST":
        if not contains_all(flask.request.form, ("username", "password1", "password2")):
            return flask.render_template("unauthorizedmessage.html", message="Неправильный запрос")
        username = flask.request.form.get("username")
        if not validate_username(username):
            return flask.render_template("unauthorizedmessage.html", message="Имя пользователя может состоять только из букв, цифр, дефиса (-) или нижнего подчёркивания (_)")
        # check if user exists
        query = """SELECT * FROM users WHERE username = %s"""
        cur.execute(query, (username,))
        if cur.fetchall():
            return flask.render_template("unauthorizedmessage.html", message="Это имя пользователя занято")

        # check if passwords match
        password1 = flask.request.form.get("password1")
        password2 = flask.request.form.get("password2")
        if password1 != password2:
            return flask.render_template("unauthorizedmessage.html", message="Пароли не совпадают")
        passhash = base64.b64encode(hashlib.md5(password1.encode("UTF-8")).digest()).decode("UTF-8")
        query = """INSERT INTO users (username, passhash) VALUES (%s, %s)"""
        cur.execute(query, (username, passhash))
        con.commit()
        return flask.render_template("unauthorizedmessage.html", message="Пользователь зарегистрирован, теперь вы можете авторизоваться")
    else:
        return flask.render_template("unauthorizedmessage.html", message="Метод не поддерживается")

# --- API functions -----------------------------------------------------------

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

# API function "login": takes username and password with POST
# logs user in and returns token if successful,
# otherwise returs error object
@app.route("/api/login", methods=["POST"])
def api_login():
    if not con.is_connected():
        init_mysql()
    if not contains_all(flask.request.form, ("username", "password")):
        return json_response({"message": "Wrong request"}, False)

    # check if user exists
    username = flask.request.form.get("username")
    query = """SELECT id, passhash FROM users WHERE username = %s"""
    cur.execute(query, (username,))
    userdata = fetchall_as_dict(cur)
    if not userdata:
        return json_response({"message": "No such user"}, False)
    userdata = userdata[0]

    # check if passwords match
    password = flask.request.form.get("password")
    passhash = base64.b64encode(hashlib.md5(password.encode("UTF-8")).digest()).decode("UTF-8")
    if userdata["passhash"] != passhash:
        return json_response({"message": "Wrong password"}, False)

    # generate unique token
    query = """SELECT id FROM sessions WHERE id = %s"""
    while True:
        token = gen_session_token()
        cur.execute(query, (token,))
        if not cur.fetchall():
            break
    query = """INSERT INTO sessions (id, userid, active) VALUES (%s, %s, TRUE)"""
    cur.execute(query, (token, userdata["id"]))
    con.commit()
    return json_response({"token": token})

# API function "logout": takes token with POST
# logs user out and returns success object if successful,
# otherwise returs error object
@app.route("/api/logout", methods=["POST"])
def api_logout():
    if not con.is_connected():
        init_mysql()
    if not contains_all(flask.request.form, ("token",)):
        return json_response({"message": "Wrong request"}, False)
    token = flask.request.form.get("token")
    query = """UPDATE sessions SET active = FALSE where id = %s"""
    cur.execute(query, (token,))
    con.commit()
    return json_response({})

# API function "all after": takes token and note_id with POST
# returns all notes whose id is greater than note_id if successful
# otherwise returns error object
@app.route("/api/allafter", methods=["POST"])
def api_allafter():
    if not con.is_connected():
        init_mysql()
    if not contains_all(flask.request.form, ("token", "note_id")):
        return json_response({"message": "Wrong request"}, False)
    token = flask.request.form.get("token")
    userdata = userdata_by_token(token)
    if not userdata:
        return json_response({"message": "Wrong token"}, False)

    noteid = flask.request.form.get("note_id")
    try:
        noteid = int(noteid)
    except Exception as e:
        return json_response({"message": "Wrong request"}, False)

    result = cur.execute("SELECT id,title,contents,CAST(date_created AS CHAR) AS date_created,tags,CAST(date_modified AS CHAR) AS date_modified FROM notes WHERE id > %s AND userid=%s ORDER BY id DESC", (noteid, userdata["userid"]))
    notes = fetchall_as_dict(cur)
    return json_response({"notes": notes})

# API function "search": takes token and tags or keywords or both with POST
# returns all matching notes if successful
# otherwise returns error object
@app.route("/api/search", methods=["POST"])
def api_search():
    if not con.is_connected():
        init_mysql()
    if not contains_all(flask.request.form, ("token",)):
        return json_response({"message": "Wrong request"}, False)
    token = flask.request.form.get("token")
    userdata = userdata_by_token(token)
    if not userdata:
        return json_response({"message": "Wrong token"}, False)

    rawKeywords = flask.request.form.get("keywords", "").strip()
    rawTags = flask.request.form.get("tags", "").strip()
    if rawKeywords == "" and rawTags == "":
        return json_response({"message": "Wrong search params"}, False)
    keywords = rawKeywords.split()
    tags = rawTags.split()
    for tag in tags:
        if not validate_tag(tag):
            return json_response({"message": "Wrong search params"}, False)
    for keyword in keywords :
        if not validate_tag(keyword):
            return json_response({"message": "Wrong search params"}, False)
    keywordsLike = list(map(lambda k: ["%" + k + "%"]*2, keywords))
    keywordsLike1 = []
    for keywordLike in keywordsLike:
        keywordsLike1.extend(keywordLike)
    keywordsLike = keywordsLike1
    tagsLike = list(map(lambda t: "%" + t + "%", tags))
    queryParts = ["SELECT id,title,contents,CAST(date_created AS CHAR) AS date_created,tags,CAST(date_modified AS CHAR) AS date_modified FROM notes WHERE userid=%s"]
    if keywords or tags:
        queryParts.append(" AND ")
    if keywords:
        queryParts.append("(" + "OR".join(["(title LIKE %s OR contents LIKE %s)"] * len(keywords)) + ")")
        if tags:
            queryParts.append(" AND ")
    if tags:
        queryParts.append("(" + "OR".join(["(tags LIKE %s)"] * len(tags)) + ")")
    query = "".join(queryParts)
    cur.execute(query, [userdata["userid"]] + keywordsLike + tagsLike)
    notes = fetchall_as_dict(cur)
    return json_response({"notes": notes})

# API function "new": takes token, title, tags, and contents with POST
# returns id if successful
# otherwise returns error object
@app.route("/api/new", methods=["POST"])
def api_new():
    if not con.is_connected():
        init_mysql()
    if not contains_all(flask.request.form, ("token", "title", "tags", "contents")):
        return json_response({"message": "Wrong request"}, False)
    token = flask.request.form.get("token")
    userdata = userdata_by_token(token)
    if not userdata:
        return json_response({"message": "Wrong token"}, False)

    title = flask.request.form.get("title", "")
    contents = flask.request.form.get("contents", "")
    rawTags = flask.request.form.get("tags", "").strip()
    tagList = rawTags.split()
    for tag in tagList:
        if not validate_tag(tag):
            return json_response({"message": "A tag must contain only digits, underscore('_'), or hyphen('-')"}, False)
    tags = " ".join(tagList)
    curdt = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
    query = "INSERT INTO notes(title,contents,date_created,tags,date_modified,userid)VALUES(%s,%s,%s,%s,%s,%s)"
    cur.execute(query, (title, contents, curdt, tags, curdt, userdata["userid"]))
    con.commit()
    return json_response({"note_id": cur.lastrowid})

# API function "note": takes token and note_id with POST
# returns note if successful
# otherwise returns error object
@app.route("/api/note", methods=["POST"])
def api_note():
    if not con.is_connected():
        init_mysql()
    if not contains_all(flask.request.form, ("token", "note_id")):
        return json_response({"message": "Wrong request"}, False)
    token = flask.request.form.get("token")
    userdata = userdata_by_token(token)
    if not userdata:
        return json_response({"message": "Wrong token"}, False)

    noteid = flask.request.form.get("note_id")
    try:
        noteid = int(noteid)
    except Exception as e:
        return json_response({"message": "Wrong request"}, False)

    query = "SELECT id,title,tags,contents,CAST(date_created AS CHAR) AS date_created,CAST(date_modified AS CHAR) AS date_modified FROM notes WHERE id=%s AND userid=%s"
    cur.execute(query, (noteid, userdata["userid"]))
    result = fetchall_as_dict(cur)
    if not result:
        return json_response({"message": "Note not exists"}, False)
    note = result[0]
    return json_response({"note": note})

# API function "delete": takes token and note_id with POST
# deletes note with id that equals to note_id
# returns success object if successful
# otherwise returns error object
@app.route("/api/delete", methods=["POST"])
def api_delete():
    if not con.is_connected():
        init_mysql()
    if not contains_all(flask.request.form, ("token", "note_id")):
        return json_response({"message": "Wrong request"}, False)
    token = flask.request.form.get("token")
    userdata = userdata_by_token(token)
    if not userdata:
        return json_response({"message": "Wrong token"}, False)

    noteid = flask.request.form.get("note_id")
    try:
        noteid = int(noteid)
    except Exception as e:
        return json_response({"message": "Wrong request"}, False)

    query = """SELECT userid FROM notes WHERE userid=%s AND id=%s"""
    cur.execute(query, (userdata["userid"], noteid))
    if not fetchall_as_dict(cur):
        return json_response({"message": "Not exists"}, False)

    query = "DELETE FROM notes WHERE id=%s"
    cur.execute(query, (noteid,))
    con.commit()
    return json_response({})

# API function "edit": takes token, note_id, title, tags, and contents with POST
# updates note with id that equals to note_id
# returns success object if successful
# otherwise returns error object
@app.route("/api/edit", methods=["POST"])
def api_edit():
    if not con.is_connected():
        init_mysql()
    if not contains_all(flask.request.form, ("token", "note_id", "title", "tags", "contents")):
        return json_response({"message": "Wrong request"}, False)
    token = flask.request.form.get("token")
    userdata = userdata_by_token(token)
    if not userdata:
        return json_response({"message": "Wrong token"}, False)

    noteid = flask.request.form.get("note_id")
    try:
        noteid = int(noteid)
    except Exception as e:
        return json_response({"message": "Wrong request"}, False)

    query = """SELECT userid FROM notes WHERE userid=%s AND id=%s"""
    cur.execute(query, (userdata["userid"], noteid))
    if not fetchall_as_dict(cur):
        return json_response({"message": "Not exists"}, False)

    title = flask.request.form.get("title", "")
    contents = flask.request.form.get("contents", "")
    rawTags = flask.request.form.get("tags", "").strip()
    tagList = rawTags.split()
    for tag in tagList:
        if not validate_tag(tag):
            return json_response({"message": "A tag must contain only digits, underscore('_'), or hyphen('-')"}, False)
    tags = " ".join(tagList)
    curdt = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
    query = "UPDATE notes SET title=%s,contents=%s,tags=%s,date_modified=%s WHERE id=%s"
    cur.execute(query, (title, contents, tags, curdt, noteid))
    con.commit()
    return json_response({})

