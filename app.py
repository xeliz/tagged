import flask
import mysql.connector
import html
import datetime
import urllib.parse
import random
import hashlib
import base64

DB_USER = "root"
DB_PASSWORD = "1234"
DB_NAME = "tagged"

# connect to database
con = mysql.connector.connect(
    host="localhost",
    user=DB_USER,
    passwd=DB_PASSWORD,
    database=DB_NAME
)

# get cursor
cur = con.cursor()

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
    resp = flask.make_response(flask.redirect(flask.url_for("profile_page")))
    resp.set_cookie("session_token", token)
    return resp

# unlogin user:
# - unset cookie
# - update session table if the param is True
# - redirect to login page
def unlogin_user(deactivateSession=True):
    token = flask.request.cookies.get("session_token")
    if deactivateSession:
        query = """UPDATE sessions SET active = FALSE where id = %s"""
        cur.execute(query, (token,))
        con.commit()
    resp = flask.make_response(flask.redirect(flask.url_for("login_page")))
    resp.set_cookie("session_token", "", expires=0)
    return resp

# create flask app
app = flask.Flask(__name__)

# make a new template filter "escapeurl"
# it is used for encoding generated url in templates
@app.template_filter("escapeurl")
def escapeurl_filter(s):
    return urllib.parse.quote_plus(s)

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

# main page: recent notes
@app.route("/")
def index_page():
    result = cur.execute("SELECT id,title,contents,date_created,tags,date_modified FROM notes ORDER BY date_modified DESC LIMIT 10");
    notes = fetchall_as_dict(cur)
    # notes = cur.fetchall()
    return flask.render_template("index.html", title="Главная", notes=notes)

# new note page: add new note
@app.route("/new", methods=["GET", "POST"])
def new_page():
    if flask.request.method == "GET":
        return flask.render_template("new.html", title="Новая запись")
    elif flask.request.method == "POST":
        if not contains_all(flask.request.form, ("title", "contents", "tags")):
            return flask.render_template("message.html", title="Сообщение", message="Неверный запрос")
        title = html.escape(flask.request.form.get("title", ""))
        contents = html.escape(flask.request.form.get("contents", "")).replace("\n", "<br>")
        rawTags = html.escape(flask.request.form.get("tags", "")).strip()
        tagList = rawTags.split()
        for tag in tagList:
            if not validate_tag(tag):
                return flask.render_template("message.html", title="Сообщение", message="Ошибка: метка может содержать только буквы, цифры, нижнее подчёркивание (_) или дефис(-)")
        tags = " ".join(tagList)
        curdt = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
        query = "INSERT INTO notes(title,contents,date_created,tags,date_modified,userid)VALUES(%s,%s,%s,%s,%s,1)"
        cur.execute(query, (title, contents, curdt, tags, curdt))
        con.commit()
        return flask.redirect(flask.url_for("note_noteid_page", noteid=cur.lastrowid))
    else:
        return flask.render_template("message.html", title="Сообщение", message="Метод не поддерживается")

# all notes page
@app.route("/all")
def all_page():
    result = cur.execute("SELECT id,title,contents,date_created,tags,date_modified FROM notes ORDER BY date_modified DESC");
    notes = fetchall_as_dict(cur)
    return flask.render_template("all.html", title="Все записи", notes=notes)

# search page
@app.route("/search")
def search_page():
    return flask.render_template("search.html", title="Поиск")

# search results page
@app.route("/search/results")
def search_results_page():
    rawKeywords = flask.request.args.get("keywords", "").strip()
    rawTags = flask.request.args.get("tags", "").strip()
    if rawKeywords == "" and rawTags == "":
        return flask.render_template("message.html", title="Сообщение", message="Неправильные параметры поиска")
    keywords = rawKeywords.split()
    tags = rawTags.split()
    for tag in tags:
        if not validate_tag(tag):
            return flask.render_template("message.html", title="Сообщение", message="Неправильные параметры поиска")
    for keyword in keywords :
        if not validate_tag(keyword):
            return flask.render_template("message.html", title="Сообщение", message="Неправильные параметры поиска")
    keywordsLike = list(map(lambda k: ["%" + k + "%"]*2, keywords))
    keywordsLike1 = []
    for keywordLike in keywordsLike:
        keywordsLike1.extend(keywordLike)
    keywordsLike = keywordsLike1
    tagsLike = list(map(lambda t: "%" + t + "%", tags))
    queryParts = ["SELECT id,title,contents,date_created,tags,date_modified FROM notes WHERE "]
    if keywords:
        queryParts.append("(" + "OR".join(["(title LIKE %s OR contents LIKE %s)"] * len(keywords)) + ")")
        if tags:
            queryParts.append(" AND ")
    if tags:
        queryParts.append("(" + "OR".join(["(tags LIKE %s)"] * len(tags)) + ")")
    query = "".join(queryParts)
    cur.execute(query, keywordsLike + tagsLike)
    notes = fetchall_as_dict(cur)
    return flask.render_template("search_results.html", title="Результаты поиска", keywords=keywords, tags=tags, notes=notes)

# delete page
@app.route("/delete/<int:noteid>", methods=["GET", "POST"])
def delete_noteid_page(noteid):
    if flask.request.method == "GET":
        return flask.render_template("delete_noteid.html", title="Удаление записи", noteid=noteid)
    elif flask.request.method == "POST":
        query = "DELETE FROM notes WHERE id={}".format(noteid)
        cur.execute(query)
        con.commit()
        return flask.render_template("message.html", title="Сообщение", message="Удалено")
    else:
        return flask.render_template("message.html", title="Сообщение", message="Метод не поддерживается")

# specific note page
@app.route("/note/<int:noteid>")
def note_noteid_page(noteid):
    query = "SELECT id,title,tags,contents,date_created,date_modified FROM notes WHERE id={}".format(noteid)
    cur.execute(query)
    note = fetchone_as_dict(cur)
    return flask.render_template("note_noteid.html", title="Просмотр записи", note=note)

# note editing page
@app.route("/edit/<int:noteid>", methods=["GET", "POST"])
def edit_noteid_page(noteid):
    if flask.request.method == "GET":
        query = "SELECT title,contents,tags FROM notes WHERE id={}".format(noteid)
        cur.execute(query)
        note = fetchone_as_dict(cur)
        note["contents"] = note["contents"].replace("<br>", "\n")
        return flask.render_template("edit_noteid.html", title="Изменение записи", note=note)
    elif flask.request.method == "POST":
        if not contains_all(flask.request.form, ("title", "contents", "tags")):
            return flask.render_template("message.html", title="Сообщение", message="Метод не поддерживается")
        title = html.escape(flask.request.form.get("title", ""))
        contents = html.escape(flask.request.form.get("contents", "")).replace("\n", "<br>")
        rawTags = html.escape(flask.request.form.get("tags", "")).strip()
        tagList = rawTags.split()
        for tag in tagList:
            if not validate_tag(tag):
                return flask.render_template("message.html", title="Сообщение", message="Ошибка: метка может содержать только буквы, цифры, нижнее подчёркивание (_) или дефис(-)")
        tags = " ".join(tagList)
        curdt = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
        query = "UPDATE notes SET title=%s,contents=%s,tags=%s,date_modified=%s WHERE id={}".format(noteid)
        cur.execute(query, (title, contents, tags, curdt))
        con.commit()
        return flask.redirect(flask.url_for("note_noteid_page", noteid=noteid))
    else:
        return flask.render_template("message.html", title="Сообщение", message="Метод не поддерживается")

# sign in page
@app.route("/login", methods=["GET", "POST"])
def login_page():
    if "session_token" in flask.request.cookies:
        return flask.redirect(flask.url_for("profile_page"))

    if flask.request.method == "GET":
        return flask.render_template("login.html", title="Вход")
    elif flask.request.method == "POST":
        if not contains_all(flask.request.form, ("username", "password")):
            return flask.render_template("unauthorizedmessage.html", title="Сообщение", message="Неправильный запрос")

        username = flask.request.form.get("username")
        if not validate_username(username):
            return flask.render_template("unauthorizedmessage.html", title="Сообщение", message="Имя пользователя может состоять только из букв, цифр, дефиса (-) или нижнего подчёркивания (_)")
        # check if user exists
        query = """SELECT id, passhash FROM users WHERE username = %s"""
        cur.execute(query, (username,))
        userdata = fetchall_as_dict(cur)
        if not userdata:
            return flask.render_template("unauthorizedmessage.html", title="Сообщение", message="Такой пользователь не зарегистрирован")
        userdata = userdata[0]

        # check if passwords match
        password = flask.request.form.get("password")
        passhash = base64.b64encode(hashlib.md5(password.encode("UTF-8")).digest()).decode("UTF-8")
        if userdata["passhash"] != passhash:
            return flask.render_template("unauthorizedmessage.html", title="Сообщение", message="Неверный пароль")

        return login_user(userdata["id"]) 
    else:
        return flask.render_template("unauthorizedmessage.html", title="Сообщение", message="Метод не поддерживается")

# profile page
@app.route("/profile", methods=["GET", "POST"])
def profile_page():
    userdata = userdata_if_logined()
    if not userdata:
        return unlogin_user(False)
    if flask.request.method == "GET":
        return flask.render_template("profile.html", title="Профиль", userdata=userdata)
    elif flask.request.method == "POST":
        if "action" not in flask.request.form:
            return flask.render_template("unauthorizedmessage.html", title="Сообщение", message="Неправильный запрос")
        action = flask.request.form.get("action")
        if action == "logout":
            return unlogin_user()
        else:
            return flask.render_template("unauthorizedmessage.html", title="Сообщение", message="Неправильное действие")
    else:
        return flask.render_template("unauthorizedmessage.html", title="Сообщение", message="Метод не поддерживается")

# sign up page
@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    if flask.request.method == "GET":
        return flask.render_template("signup.html", title="Регистрация")
    elif flask.request.method == "POST":
        if contains_all(flask.request.form, ("username", "password1", "password2")):
            return flask.render_template("unauthorizedmessage.html", title="Сообщение", message="Неправильный запрос")
        username = flask.request.form.get("username")
        # check if user exists
        query = """SELECT * FROM users WHERE username = %s"""
        cur.execute(query, (username,))
        if cur.fetchall():
            return flask.render_template("unauthorizedmessage.html", title="Сообщение", message="Это имя пользователя занято")

        # check if passwords match
        password1 = flask.request.form.get("password1")
        password2 = flask.request.form.get("password2")
        if password1 != password2:
            return flask.render_template("unauthorizedmessage.html", title="Сообщение", message="Пароли не совпадают")
        passhash = base64.b64encode(hashlib.md5(password1.encode("UTF-8")).digest()).decode("UTF-8")
        query = """INSERT INTO users (username, passhash) VALUES (%s, %s)"""
        cur.execute(query, (username, passhash))
        con.commit()
        return flask.render_template("unauthorizedmessage.html", title="Сообщение", message="Пользователь зарегистрирован, теперь вы можете авторизоваться")
    else:
        return flask.render_template("unauthorizedmessage.html", title="Сообщение", message="Метод не поддерживается")
