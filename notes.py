# routes for site pages related to notes: viewing, editing, etc.

import flask
import html
import datetime

from . import common

notesapp = flask.Blueprint("notesapp", __name__, template_folder="templates")

# main page: recent notes
@notesapp.route("/")
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
@notesapp.route("/new", methods=["GET", "POST"])
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
        return flask.redirect(flask.url_for(".note_noteid_page", noteid=common.cur.lastrowid))
    else:
        return flask.render_template("message.html", message="Метод не поддерживается")

# all notes page
@notesapp.route("/all")
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
@notesapp.route("/search")
def search_page():
    userdata = common.userdata_if_logined()
    if not userdata:
        return common.unlogin_user(False)
    return flask.render_template("search.html")

# search results page
@notesapp.route("/search/results")
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
@notesapp.route("/delete/<int:noteid>", methods=["GET", "POST"])
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
@notesapp.route("/note/<int:noteid>")
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
@notesapp.route("/edit/<int:noteid>", methods=["GET", "POST"])
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
        return flask.redirect(flask.url_for(".note_noteid_page", noteid=noteid))
    else:
        return flask.render_template("message.html", message="Метод не поддерживается")

