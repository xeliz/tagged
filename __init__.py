import flask
import html
import datetime
import urllib.parse
import hashlib
import base64
import json

from . import common

common.init_mysql()

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
    if not common.con.is_connected():
        common.init_mysql()
    userdata = common.userdata_if_logined()
    if not userdata:
        return common.unlogin_user(False)
    result = common.cur.execute("SELECT id,title,contents,date_created,tags,date_modified FROM notes WHERE userid=%s ORDER BY date_modified DESC LIMIT 10", (userdata["userid"],))
    notes = common.fetchall_as_dict(common.cur)
    # notes = common.cur.fetchall()
    return flask.render_template("index.html", notes=notes)

# new note page: add new note
@app.route("/new", methods=["GET", "POST"])
def new_page():
    if not common.con.is_connected():
        common.init_mysql()
    userdata = common.userdata_if_logined()
    if not userdata:
        return common.unlogin_user(False)
    if flask.request.method == "GET":
        return flask.render_template("new.html")
    elif flask.request.method == "POST":
        if not common.contains_all(flask.request.form, ("title", "contents", "tags")):
            return flask.render_template("message.html", message="Неправильный запрос")
        title = flask.request.form.get("title", "")
        contents = flask.request.form.get("contents", "")
        rawTags = flask.request.form.get("tags", "").strip()
        tagList = rawTags.split()
        for tag in tagList:
            if not common.validate_tag(tag):
                return flask.render_template("message.html", message="Ошибка: метка может содержать только буквы, цифры, нижнее подчёркивание (_) или дефис(-)")
        tags = " ".join(tagList)
        curdt = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
        query = "INSERT INTO notes(title,contents,date_created,tags,date_modified,userid)VALUES(%s,%s,%s,%s,%s,%s)"
        common.cur.execute(query, (title, contents, curdt, tags, curdt, userdata["userid"]))
        common.con.commit()
        return flask.redirect(flask.url_for("note_noteid_page", noteid=common.cur.lastrowid))
    else:
        return flask.render_template("message.html", message="Метод не поддерживается")

# all notes page
@app.route("/all")
def all_page():
    if not common.con.is_connected():
        common.init_mysql()
    userdata = common.userdata_if_logined()
    if not userdata:
        return common.unlogin_user(False)
    result = common.cur.execute("SELECT id,title,contents,date_created,tags,date_modified FROM notes WHERE userid=%s ORDER BY date_modified DESC", (userdata["userid"],))
    notes = common.fetchall_as_dict(common.cur)
    return flask.render_template("all.html", notes=notes)

# search page
@app.route("/search")
def search_page():
    userdata = common.userdata_if_logined()
    if not userdata:
        return common.unlogin_user(False)
    return flask.render_template("search.html")

# search results page
@app.route("/search/results")
def search_results_page():
    if not common.con.is_connected():
        common.init_mysql()
    userdata = common.userdata_if_logined()
    if not userdata:
        return common.unlogin_user(False)
    rawKeywords = flask.request.args.get("keywords", "").strip()
    rawTags = flask.request.args.get("tags", "").strip()
    if rawKeywords == "" and rawTags == "":
        return flask.render_template("message.html", message="Неправильные параметры поиска")
    keywords = rawKeywords.split()
    tags = rawTags.split()
    for tag in tags:
        if not common.validate_tag(tag):
            return flask.render_template("message.html", message="Неправильные параметры поиска")
    for keyword in keywords :
        if not common.validate_tag(keyword):
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
    common.cur.execute(query, [userdata["userid"]] + keywordsLike + tagsLike)
    notes = common.fetchall_as_dict(common.cur)
    return flask.render_template("search_results.html", keywords=keywords, tags=tags, notes=notes)

# delete page
@app.route("/delete/<int:noteid>", methods=["GET", "POST"])
def delete_noteid_page(noteid):
    if not common.con.is_connected():
        common.init_mysql()
    userdata = common.userdata_if_logined()
    if not userdata:
        return common.unlogin_user(False)

    query = """SELECT userid FROM notes WHERE userid=%s AND id=%s"""
    common.cur.execute(query, (userdata["userid"], noteid))
    if not common.fetchall_as_dict(common.cur):
        return flask.render_template("message.html", message="Вы не можете удалить чужую заметку")

    if flask.request.method == "GET":
        return flask.render_template("delete_noteid.html", noteid=noteid)
    elif flask.request.method == "POST":
        query = "DELETE FROM notes WHERE id=%s"
        common.cur.execute(query, (noteid,))
        common.con.commit()
        return flask.render_template("message.html", message="Удалено")
    else:
        return flask.render_template("message.html", message="Метод не поддерживается")

# specific note page
@app.route("/note/<int:noteid>")
def note_noteid_page(noteid):
    if not common.con.is_connected():
        common.init_mysql()
    userdata = common.userdata_if_logined()
    if not userdata:
        return common.unlogin_user(False)
    query = "SELECT id,title,tags,contents,date_created,date_modified FROM notes WHERE id=%s AND userid=%s"
    common.cur.execute(query, (noteid, userdata["userid"]))
    result = common.fetchall_as_dict(common.cur)
    if not result:
        return flask.render_template("message.html", message="Заметка не существует")
    note = result[0]
    return flask.render_template("note_noteid.html", note=note)

# note editing page
@app.route("/edit/<int:noteid>", methods=["GET", "POST"])
def edit_noteid_page(noteid):
    if not common.con.is_connected():
        common.init_mysql()
    userdata = common.userdata_if_logined()
    if not userdata:
        return common.unlogin_user(False)

    query = """SELECT userid FROM notes WHERE userid=%s AND id=%s"""
    common.cur.execute(query, (userdata["userid"], noteid))
    if not common.fetchall_as_dict(common.cur):
        return flask.render_template("message.html", message="Заметка не существует")

    if flask.request.method == "GET":
        query = "SELECT title,contents,tags FROM notes WHERE id=%s"
        common.cur.execute(query, (noteid,))
        note = common.fetchone_as_dict(common.cur)
        return flask.render_template("edit_noteid.html", note=note)
    elif flask.request.method == "POST":
        if not common.contains_all(flask.request.form, ("title", "contents", "tags")):
            return flask.render_template("message.html", message="Неправильный запрос")
        title = flask.request.form.get("title", "")
        contents = flask.request.form.get("contents", "")
        rawTags = flask.request.form.get("tags", "").strip()
        tagList = rawTags.split()
        for tag in tagList:
            if not common.validate_tag(tag):
                return flask.render_template("message.html", message="Ошибка: метка может содержать только буквы, цифры, нижнее подчёркивание (_) или дефис(-)")
        tags = " ".join(tagList)
        curdt = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
        query = "UPDATE notes SET title=%s,contents=%s,tags=%s,date_modified=%s WHERE id=%s"
        common.cur.execute(query, (title, contents, tags, curdt, noteid))
        common.con.commit()
        return flask.redirect(flask.url_for("note_noteid_page", noteid=noteid))
    else:
        return flask.render_template("message.html", message="Метод не поддерживается")

# sign in page
@app.route("/login", methods=["GET", "POST"])
def login_page():
    if not common.con.is_connected():
        common.init_mysql()
    if "session_token" in flask.request.cookies:
        return flask.redirect(flask.url_for("profile_page"))

    if flask.request.method == "GET":
        return flask.render_template("login.html")
    elif flask.request.method == "POST":
        if not common.contains_all(flask.request.form, ("username", "password")):
            return flask.render_template("unauthorizedmessage.html", message="Неправильный запрос")

        # check if user exists
        username = flask.request.form.get("username")
        query = """SELECT id, passhash FROM users WHERE username = %s"""
        common.cur.execute(query, (username,))
        userdata = common.fetchall_as_dict(common.cur)
        if not userdata:
            return flask.render_template("unauthorizedmessage.html", message="Такой пользователь не зарегистрирован")
        userdata = userdata[0]

        # check if passwords match
        password = flask.request.form.get("password")
        passhash = base64.b64encode(hashlib.md5(password.encode("UTF-8")).digest()).decode("UTF-8")
        if userdata["passhash"] != passhash:
            return flask.render_template("unauthorizedmessage.html", message="Неверный пароль")

        return common.login_user(userdata["id"]) 
    else:
        return flask.render_template("unauthorizedmessage.html", message="Метод не поддерживается")

# profile page
@app.route("/profile")
def profile_page():
    if not common.con.is_connected():
        common.init_mysql()
    userdata = common.userdata_if_logined()
    if not userdata:
        return common.unlogin_user(False)
    return flask.render_template("profile.html", userdata=userdata)

# logout page
@app.route("/logout")
def logout_page():
    if not common.con.is_connected():
        common.init_mysql()
    return common.unlogin_user()

# sign up page
@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    if not common.con.is_connected():
        common.init_mysql()
    userdata = common.userdata_if_logined()
    if userdata:
        return flask.redirect(flask.url_for("index_page"))
    if flask.request.method == "GET":
        return flask.render_template("signup.html")
    elif flask.request.method == "POST":
        if not common.contains_all(flask.request.form, ("username", "password1", "password2")):
            return flask.render_template("unauthorizedmessage.html", message="Неправильный запрос")
        username = flask.request.form.get("username")
        if not common.validate_username(username):
            return flask.render_template("unauthorizedmessage.html", message="Имя пользователя может состоять только из букв, цифр, дефиса (-) или нижнего подчёркивания (_)")
        # check if user exists
        query = """SELECT * FROM users WHERE username = %s"""
        common.cur.execute(query, (username,))
        if common.cur.fetchall():
            return flask.render_template("unauthorizedmessage.html", message="Это имя пользователя занято")

        # check if passwords match
        password1 = flask.request.form.get("password1")
        password2 = flask.request.form.get("password2")
        if password1 != password2:
            return flask.render_template("unauthorizedmessage.html", message="Пароли не совпадают")
        passhash = base64.b64encode(hashlib.md5(password1.encode("UTF-8")).digest()).decode("UTF-8")
        query = """INSERT INTO users (username, passhash) VALUES (%s, %s)"""
        common.cur.execute(query, (username, passhash))
        common.con.commit()
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
    if not common.con.is_connected():
        common.init_mysql()
    # get user data from database
    query = """SELECT userid, username, passhash FROM sessions, users WHERE sessions.active = TRUE AND sessions.userid = users.id AND sessions.id = %s"""
    common.cur.execute(query, (token,))
    userdata = common.fetchall_as_dict(common.cur)
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
    if not common.con.is_connected():
        common.init_mysql()
    if not common.contains_all(flask.request.form, ("username", "password")):
        return json_response({"message": "Wrong request"}, False)

    # check if user exists
    username = flask.request.form.get("username")
    query = """SELECT id, passhash FROM users WHERE username = %s"""
    common.cur.execute(query, (username,))
    userdata = common.fetchall_as_dict(common.cur)
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
        token = common.gen_session_token()
        common.cur.execute(query, (token,))
        if not common.cur.fetchall():
            break
    query = """INSERT INTO sessions (id, userid, active) VALUES (%s, %s, TRUE)"""
    common.cur.execute(query, (token, userdata["id"]))
    common.con.commit()
    return json_response({"token": token})

# API function "logout": takes token with POST
# logs user out and returns success object if successful,
# otherwise returs error object
@app.route("/api/logout", methods=["POST"])
def api_logout():
    if not common.con.is_connected():
        common.init_mysql()
    if not common.contains_all(flask.request.form, ("token",)):
        return json_response({"message": "Wrong request"}, False)
    token = flask.request.form.get("token")
    query = """UPDATE sessions SET active = FALSE where id = %s"""
    common.cur.execute(query, (token,))
    common.con.commit()
    return json_response({})

# API function "all after": takes token and note_id with POST
# returns all notes whose id is greater than note_id if successful
# otherwise returns error object
@app.route("/api/allafter", methods=["POST"])
def api_allafter():
    if not common.con.is_connected():
        common.init_mysql()
    if not common.contains_all(flask.request.form, ("token", "note_id")):
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

    result = common.cur.execute("SELECT id,title,contents,CAST(date_created AS CHAR) AS date_created,tags,CAST(date_modified AS CHAR) AS date_modified FROM notes WHERE id > %s AND userid=%s ORDER BY id DESC", (noteid, userdata["userid"]))
    notes = common.fetchall_as_dict(common.cur)
    return json_response({"notes": notes})

# API function "search": takes token and tags or keywords or both with POST
# returns all matching notes if successful
# otherwise returns error object
@app.route("/api/search", methods=["POST"])
def api_search():
    if not common.con.is_connected():
        common.init_mysql()
    if not common.contains_all(flask.request.form, ("token",)):
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
        if not common.validate_tag(tag):
            return json_response({"message": "Wrong search params"}, False)
    for keyword in keywords :
        if not common.validate_tag(keyword):
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
    common.cur.execute(query, [userdata["userid"]] + keywordsLike + tagsLike)
    notes = common.fetchall_as_dict(common.cur)
    return json_response({"notes": notes})

# API function "new": takes token, title, tags, and contents with POST
# returns id if successful
# otherwise returns error object
@app.route("/api/new", methods=["POST"])
def api_new():
    if not common.con.is_connected():
        common.init_mysql()
    if not common.contains_all(flask.request.form, ("token", "title", "tags", "contents")):
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
        if not common.validate_tag(tag):
            return json_response({"message": "A tag must contain only digits, underscore('_'), or hyphen('-')"}, False)
    tags = " ".join(tagList)
    curdt = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
    query = "INSERT INTO notes(title,contents,date_created,tags,date_modified,userid)VALUES(%s,%s,%s,%s,%s,%s)"
    common.cur.execute(query, (title, contents, curdt, tags, curdt, userdata["userid"]))
    common.con.commit()
    return json_response({"note_id": common.cur.lastrowid})

# API function "note": takes token and note_id with POST
# returns note if successful
# otherwise returns error object
@app.route("/api/note", methods=["POST"])
def api_note():
    if not common.con.is_connected():
        common.init_mysql()
    if not common.contains_all(flask.request.form, ("token", "note_id")):
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
    common.cur.execute(query, (noteid, userdata["userid"]))
    result = common.fetchall_as_dict(common.cur)
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
    if not common.con.is_connected():
        common.init_mysql()
    if not common.contains_all(flask.request.form, ("token", "note_id")):
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
    common.cur.execute(query, (userdata["userid"], noteid))
    if not common.fetchall_as_dict(common.cur):
        return json_response({"message": "Not exists"}, False)

    query = "DELETE FROM notes WHERE id=%s"
    common.cur.execute(query, (noteid,))
    common.con.commit()
    return json_response({})

# API function "edit": takes token, note_id, title, tags, and contents with POST
# updates note with id that equals to note_id
# returns success object if successful
# otherwise returns error object
@app.route("/api/edit", methods=["POST"])
def api_edit():
    if not common.con.is_connected():
        common.init_mysql()
    if not common.contains_all(flask.request.form, ("token", "note_id", "title", "tags", "contents")):
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
    common.cur.execute(query, (userdata["userid"], noteid))
    if not common.fetchall_as_dict(common.cur):
        return json_response({"message": "Not exists"}, False)

    title = flask.request.form.get("title", "")
    contents = flask.request.form.get("contents", "")
    rawTags = flask.request.form.get("tags", "").strip()
    tagList = rawTags.split()
    for tag in tagList:
        if not common.validate_tag(tag):
            return json_response({"message": "A tag must contain only digits, underscore('_'), or hyphen('-')"}, False)
    tags = " ".join(tagList)
    curdt = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
    query = "UPDATE notes SET title=%s,contents=%s,tags=%s,date_modified=%s WHERE id=%s"
    common.cur.execute(query, (title, contents, tags, curdt, noteid))
    common.con.commit()
    return json_response({})

