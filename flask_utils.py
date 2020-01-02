
# Some utility functions/classes, related to flask

import flask
from .services import SessionService
from . import common

class NotAuthorized(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

def has_session_token():
    return "session_token" in flask.request.cookies

def get_session_token():
    return flask.request.cookies.get("session_token", None)

def login_user(con, userid):
    # generate unique session token
    cur = con.cursor()
    ss = SessionService(con)
    while True:
        token = common.gen_session_token()
        if not ss.session_exists(token):
            break
    ss.create_session(userid, token)
    con.commit()
    resp = flask.make_response(flask.redirect(flask.url_for("notesapp.index_page")))
    resp.set_cookie("session_token", token)
    return resp

def unlogin_user(con):
    if has_session_token():
        ss = SessionService(con)
        ss.deactivate_session(get_session_token())
    resp = flask.make_response(flask.redirect(flask.url_for("authapp.login_page")))
    resp.set_cookie("session_token", "", expires=0)
    return resp

def get_logined_user_id(con):
    if not has_session_token():
        raise NotAuthorized()
    ss = SessionService(con)
    userid = ss.get_userid(get_session_token())
    if userid is None:
        raise NotAuthorized()
    return userid

