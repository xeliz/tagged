# routes for site pages related to user and their authorization: login/signup/profile/settings

import flask
import hashlib
import base64

from . import common

authapp = flask.Blueprint("authapp", __name__, template_folder="templates")

# sign in page
@authapp.route("/login", methods=["GET", "POST"])
def login_page():
    if not common.con.is_connected():
        common.init_mysql()
    if "session_token" in flask.request.cookies:
        return flask.redirect(flask.url_for(".profile_page"))

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
@authapp.route("/profile")
def profile_page():
    if not common.con.is_connected():
        common.init_mysql()
    userdata = common.userdata_if_logined()
    if not userdata:
        return common.unlogin_user(False)
    return flask.render_template("profile.html", userdata=userdata)

# logout page
@authapp.route("/logout")
def logout_page():
    if not common.con.is_connected():
        common.init_mysql()
    return common.unlogin_user()

# sign up page
@authapp.route("/signup", methods=["GET", "POST"])
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

