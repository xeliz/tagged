# routes for site pages related to user and their authorization: login/signup/profile/settings

import flask
import hashlib
import base64

from . import common
from . import flask_utils
from .services import UserService, UserSearchException

authapp = flask.Blueprint("authapp", __name__, template_folder="templates")

# profile page
@authapp.route("/profile")
def profile_page():
    with common.get_con() as con:
        try:
            userid = flask_utils.get_logined_user_id(con)
            us = UserService(con)
            userdata = us.get_by_id(userid)
            return flask.render_template("profile.html", userdata=userdata)
        except flask_utils.NotAuthorized:
            return flask_utils.unlogin_user(con)
        except UserSearchException:
            return flask.render_template("message.html", message="Пользователь не найден (id = {})".format(userid))

# logout page
@authapp.route("/logout")
def logout_page():
    with common.get_con() as con:
        return flask_utils.unlogin_user(con)

# sign in page
@authapp.route("/login", methods=["GET", "POST"])
def login_page():
    with common.get_con() as con:
        if "session_token" in flask.request.cookies:
            return flask.redirect(flask.url_for(".profile_page"))
        if flask.request.method != "POST":
            return flask.render_template("login.html")

        if not common.contains_all(flask.request.form, ("username", "password")):
            return flask.render_template("unauthorizedmessage.html", message="Неправильный запрос")

        us = UserService(con)

        username = flask.request.form.get("username")
        userdata = us.get_by_name(username)

        if userdata is None:
            return flask.render_template("unauthorizedmessage.html", message="Такой пользователь не зарегистрирован")

        # check if passwords match
        password = flask.request.form.get("password")
        passhash = base64.b64encode(hashlib.md5(password.encode("UTF-8")).digest()).decode("UTF-8")

        if userdata["passhash"] != passhash:
            return flask.render_template("unauthorizedmessage.html", message="Неверный пароль")

        return flask_utils.login_user(con, userdata["id"])

# sign up page
@authapp.route("/signup", methods=["GET", "POST"])
def signup_page():
    if flask_utils.has_session_token():
        return flask.redirect(flask.url_for("index_page"))

    if flask.request.method != "POST":
        return flask.render_template("signup.html")

    if not common.contains_all(flask.request.form, ("username", "password1", "password2")):
        return flask.render_template("unauthorizedmessage.html", message="Неправильный запрос")

    username = flask.request.form.get("username")

    # check if passwords match
    password1 = flask.request.form.get("password1")
    password2 = flask.request.form.get("password2")
    if password1 != password2:
        return flask.render_template("unauthorizedmessage.html", message="Пароли не совпадают")

    if not common.validate_username(username):
        return flask.render_template("unauthorizedmessage.html", message="Имя пользователя может состоять только из букв, цифр, дефиса (-) или нижнего подчёркивания (_)")

    with common.get_con() as con:
        us = UserService(con)
        userdata = us.get_by_name(username)
        if userdata is not None:
            return flask.render_template("unauthorizedmessage.html", message="Это имя пользователя занято")
        us.create_user(username, password1)
        return flask.render_template("unauthorizedmessage.html", message="Пользователь зарегистрирован, теперь вы можете авторизоваться")

