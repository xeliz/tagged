# routes for site API related to user and their authorization: login/signup/profile/settings

import flask
import hashlib
import base64

from . import common

authapiapp = flask.Blueprint("authapiapp", __name__, template_folder="templates")

# API function "login": takes username and password with POST
# logs user in and returns token if successful,
# otherwise returs error object
@authapiapp.route("/api/login", methods=["POST"])
def api_login():
    if not common.con.is_connected():
        common.init_mysql()
    if not common.contains_all(flask.request.form, ("username", "password")):
        return common.json_response({"message": "Wrong request"}, False)

    # check if user exists
    username = flask.request.form.get("username")
    query = """SELECT id, passhash FROM users WHERE username = %s"""
    common.cur.execute(query, (username,))
    userdata = common.fetchall_as_dict(common.cur)
    if not userdata:
        return common.json_response({"message": "No such user"}, False)
    userdata = userdata[0]

    # check if passwords match
    password = flask.request.form.get("password")
    passhash = base64.b64encode(hashlib.md5(password.encode("UTF-8")).digest()).decode("UTF-8")
    if userdata["passhash"] != passhash:
        return common.json_response({"message": "Wrong password"}, False)

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
    return common.json_response({"token": token})

# API function "logout": takes token with POST
# logs user out and returns success object if successful,
# otherwise returs error object
@authapiapp.route("/api/logout", methods=["POST"])
def api_logout():
    if not common.con.is_connected():
        common.init_mysql()
    if not common.contains_all(flask.request.form, ("token",)):
        return common.json_response({"message": "Wrong request"}, False)
    token = flask.request.form.get("token")
    query = """UPDATE sessions SET active = FALSE where id = %s"""
    common.cur.execute(query, (token,))
    common.con.commit()
    return common.json_response({})

