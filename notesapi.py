# routes for API related to notes: viewing, editing, etc.

import flask
import html
import datetime

from . import common

notesapiapp = flask.Blueprint("notesapiapp", __name__, template_folder="templates")

# API function "all after id": takes token as GET param and noteid as URL part
# returns all notes whose id is greater than note_id if successful
# otherwise returns error object
@notesapiapp.route("/api/allafterid/<int:noteid>")
def api_allafterid(noteid):
    if not common.con.is_connected():
        common.init_mysql()
    if not common.contains_all(flask.request.args, ("token",)):
        return common.json_response({"message": "Wrong request"}, False)
    token = flask.request.args.get("token")
    userdata = common.userdata_by_token(token)
    if not userdata:
        return common.json_response({"message": "Wrong token"}, False)

    result = common.cur.execute("SELECT id,title,contents,CAST(date_created AS CHAR) AS date_created,tags,CAST(date_modified AS CHAR) AS date_modified FROM notes WHERE id > %s AND userid=%s ORDER BY id DESC", (noteid, userdata["userid"]))
    notes = common.fetchall_as_dict(common.cur)
    return common.json_response({"notes": notes})

# API function "search": takes token and tags or keywords or both with GET
# returns all matching notes if successful
# otherwise returns error object
@notesapiapp.route("/api/search")
def api_search():
    if not common.con.is_connected():
        common.init_mysql()
    if not common.contains_all(flask.request.args, ("token",)):
        return common.json_response({"message": "Wrong request"}, False)
    token = flask.request.args.get("token")
    userdata = common.userdata_by_token(token)
    if not userdata:
        return common.json_response({"message": "Wrong token"}, False)

    rawKeywords = flask.request.args.get("keywords", "").strip()
    rawTags = flask.request.args.get("tags", "").strip()
    if rawKeywords == "" and rawTags == "":
        return common.json_response({"message": "Wrong search params"}, False)
    keywords = rawKeywords.split()
    tags = rawTags.split()
    for tag in tags:
        if not common.validate_tag(tag):
            return common.json_response({"message": "Wrong search params"}, False)
    for keyword in keywords :
        if not common.validate_tag(keyword):
            return common.json_response({"message": "Wrong search params"}, False)
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
    return common.json_response({"notes": notes})

# API function "new": takes token, title, tags, and contents with POST
# returns id if successful
# otherwise returns error object
@notesapiapp.route("/api/new", methods=["POST"])
def api_new():
    if not common.con.is_connected():
        common.init_mysql()
    if not common.contains_all(flask.request.form, ("token", "title", "tags", "contents")):
        return common.json_response({"message": "Wrong request"}, False)
    token = flask.request.form.get("token")
    userdata = common.userdata_by_token(token)
    if not userdata:
        return common.json_response({"message": "Wrong token"}, False)

    title = flask.request.form.get("title", "")
    contents = flask.request.form.get("contents", "")
    rawTags = flask.request.form.get("tags", "").strip()
    tagList = rawTags.split()
    for tag in tagList:
        if not common.validate_tag(tag):
            return common.json_response({"message": "A tag must contain only digits, underscore('_'), or hyphen('-')"}, False)
    tags = " ".join(tagList)
    curdt = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
    query = "INSERT INTO notes(title,contents,date_created,tags,date_modified,userid)VALUES(%s,%s,%s,%s,%s,%s)"
    common.cur.execute(query, (title, contents, curdt, tags, curdt, userdata["userid"]))
    common.con.commit()
    return common.json_response({"note_id": common.cur.lastrowid})

# API function "note": takes token as GET param and noteid as URL part
# returns note if successful
# otherwise returns error object
@notesapiapp.route("/api/note/<int:noteid>")
def api_note(noteid):
    if not common.con.is_connected():
        common.init_mysql()
    if not common.contains_all(flask.request.args, ("token",)):
        return common.json_response({"message": "Wrong request"}, False)
    token = flask.request.args.get("token")
    userdata = common.userdata_by_token(token)
    if not userdata:
        return common.json_response({"message": "Wrong token"}, False)

    query = "SELECT id,title,tags,contents,CAST(date_created AS CHAR) AS date_created,CAST(date_modified AS CHAR) AS date_modified FROM notes WHERE id=%s AND userid=%s"
    common.cur.execute(query, (noteid, userdata["userid"]))
    result = common.fetchall_as_dict(common.cur)
    if not result:
        return common.json_response({"message": "Note not exists"}, False)
    note = result[0]
    return common.json_response({"note": note})

# API function "delete": takes token as POST and noteid as URL part
# deletes note with id that equals to noteid
# returns success object if successful
# otherwise returns error object
@notesapiapp.route("/api/delete/<int:noteid>", methods=["POST"])
def api_delete(noteid):
    if not common.con.is_connected():
        common.init_mysql()
    if not common.contains_all(flask.request.form, ("token",)):
        return common.json_response({"message": "Wrong request"}, False)
    token = flask.request.form.get("token")
    userdata = common.userdata_by_token(token)
    if not userdata:
        return common.json_response({"message": "Wrong token"}, False)

    query = """SELECT userid FROM notes WHERE userid=%s AND id=%s"""
    common.cur.execute(query, (userdata["userid"], noteid))
    if not common.fetchall_as_dict(common.cur):
        return common.json_response({"message": "Not exists"}, False)

    query = "DELETE FROM notes WHERE id=%s"
    common.cur.execute(query, (noteid,))
    common.con.commit()
    return common.json_response({})

# API function "edit": takes noteid as URL part and token, title, tags, and contents with POST
# updates note with id that equals to noteid
# returns success object if successful
# otherwise returns error object
@notesapiapp.route("/api/edit/<int:noteid>", methods=["POST"])
def api_edit(noteid):
    if not common.con.is_connected():
        common.init_mysql()
    if not common.contains_all(flask.request.form, ("token", "title", "tags", "contents")):
        return common.json_response({"message": "Wrong request"}, False)
    token = flask.request.form.get("token")
    userdata = common.userdata_by_token(token)
    if not userdata:
        return common.json_response({"message": "Wrong token"}, False)

    query = """SELECT userid FROM notes WHERE userid=%s AND id=%s"""
    common.cur.execute(query, (userdata["userid"], noteid))
    if not common.fetchall_as_dict(common.cur):
        return common.json_response({"message": "Not exists"}, False)

    title = flask.request.form.get("title", "")
    contents = flask.request.form.get("contents", "")
    rawTags = flask.request.form.get("tags", "").strip()
    tagList = rawTags.split()
    for tag in tagList:
        if not common.validate_tag(tag):
            return common.json_response({"message": "A tag must contain only digits, underscore('_'), or hyphen('-')"}, False)
    tags = " ".join(tagList)
    curdt = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
    query = "UPDATE notes SET title=%s,contents=%s,tags=%s,date_modified=%s WHERE id=%s"
    common.cur.execute(query, (title, contents, tags, curdt, noteid))
    common.con.commit()
    return common.json_response({})

