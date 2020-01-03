import flask
import html
import datetime
import urllib.parse
import hashlib
import base64
import json

from . import common
from .auth import authapp
from .notes import notesapp

# create flask app
app = flask.Flask(__name__)

app.register_blueprint(authapp)
app.register_blueprint(notesapp)

# template filter "escapeurl"
# it is used for encoding generated urls in templates
@app.template_filter("escapeurl")
def escapeurl_filter(s):
    return urllib.parse.quote_plus(s)

# template filter "raw2html"
# it makes some replacements in raw database contents
# such as "<" -> "&lt;"; "\n" -> "<br>", etc
@app.template_filter("raw2html")
def raw2html_filter(s):
    s = html.escape(s)
    s = s.replace("\n", "<br>")
    return s

