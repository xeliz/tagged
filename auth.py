# routes related to authorization: login/logout/signup

import flask

authapp = flask.Blueprint("authapp", __name__, template_folder="templates")

