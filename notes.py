# routes for site pages related to notes: viewing, editing, etc.

import flask

from . import common
from . import flask_utils 
from .services import NoteService, NoteSearchException

notesapp = flask.Blueprint("notesapp", __name__, template_folder="templates")

# main page: recent notes
@notesapp.route("/")
def index_page():
    with common.get_con() as con:
        try:
            userid = flask_utils.get_logined_user_id(con)
            ns = NoteService(con)
            notes = ns.get_last_notes(userid)
            all_tags = ns.find_all_tags(userid)
            return flask.render_template("index.html", notes=notes)
        except flask_utils.NotAuthorized:
            return flask_utils.unlogin_user(con)

# all notes page
@notesapp.route("/all")
def all_page():
    with common.get_con() as con:
        try:
            userid = flask_utils.get_logined_user_id(con)
            ns = NoteService(con)
            notes = ns.get_all_notes(userid)
            return flask.render_template("all_notes.html", notes=notes)
        except flask_utils.NotAuthorized:
            return flask_utils.unlogin_user(con)

# search results page
@notesapp.route("/search/results")
def search_results_page():
    with common.get_con() as con:
        try:
            userid = flask_utils.get_logined_user_id(con)
            ns = NoteService(con)
            keywords = flask.request.args.get("keywords", "").strip().split()
            tags = flask.request.args.get("tags", "").strip().split()
            notes = ns.search_notes(userid, keywords, tags)
            return flask.render_template("search_results.html", keywords=keywords, tags=tags, notes=notes)
        except flask_utils.NotAuthorized:
            return flask_utils.unlogin_user(con)
        except NoteSearchException:
            return flask.render_template("message.html", message="Неправильные параметры поиска")

# delete page
@notesapp.route("/delete/<int:noteid>", methods=["GET", "POST"])
def delete_noteid_page(noteid):
    with common.get_con() as con:
        try:
            userid = flask_utils.get_logined_user_id(con)
            ns = NoteService(con)
            if flask.request.method != "POST":
                return flask.render_template("delete_noteid.html", noteid=noteid)
            if ns.delete_note(userid, noteid):
                return flask.render_template("message.html", message="Удалено")
        except NoteSearchException:
            return flask.render_template("message.html", message="Неправильные параметры поиска")

# specific note page
@notesapp.route("/note/<int:noteid>")
def note_noteid_page(noteid):
    with common.get_con() as con:
        try:
            userid = flask_utils.get_logined_user_id(con)
            ns = NoteService(con)
            note = ns.get_note(userid, noteid)
            return flask.render_template("note_noteid.html", note=note)
        except flask_utils.NotAuthorized:
            return flask_utils.unlogin_user(con)
        except NoteSearchException:
            return flask.render_template("message.html", message="Заметка не существует")

# new note page: add new note
@notesapp.route("/new", methods=["GET", "POST"])
def new_page():
    with common.get_con() as con:
        try:
            userid = flask_utils.get_logined_user_id(con)
            if flask.request.method != "POST":
                return flask.render_template("new.html")
            if not common.contains_all(flask.request.form, ("title", "contents", "tags")):
                return flask.render_template("message.html", message="Неправильный запрос")
            title = flask.request.form.get("title", "")
            contents = flask.request.form.get("contents", "")
            tags = flask.request.form.get("tags", "").strip().split()
            if not all(map(common.validate_tag, tags)):
                return flask.render_template("message.html", message="Ошибка: метка может содержать только буквы, цифры, нижнее подчёркивание (_) или дефис(-)")
            ns = NoteService(con)
            noteid = ns.create_note(userid, title, contents, tags)
            return flask.redirect(flask.url_for(".note_noteid_page", noteid=noteid))
        except flask_utils.NotAuthorized:
            return flask_utils.unlogin_user(con)

# note editing page
@notesapp.route("/edit/<int:noteid>", methods=["GET", "POST"])
def edit_noteid_page(noteid):
    with common.get_con() as con:
        try:
            userid = flask_utils.get_logined_user_id(con)
            ns = NoteService(con)
            if flask.request.method != "POST":
                note = ns.get_note(userid, noteid)
                return flask.render_template("edit_noteid.html", note=note)
            if not common.contains_all(flask.request.form, ("title", "contents", "tags")):
                return flask.render_template("message.html", message="Неправильный запрос")
            title = flask.request.form.get("title", "")
            contents = flask.request.form.get("contents", "")
            tags = flask.request.form.get("tags", "").strip().split()
            if not all(map(common.validate_tag, tags)):
                return flask.render_template("message.html", message="Ошибка: метка может содержать только буквы, цифры, нижнее подчёркивание (_) или дефис(-)")
            ns.update_note(userid, noteid, title, contents, tags)
            return flask.redirect(flask.url_for(".note_noteid_page", noteid=noteid))
        except flask_utils.NotAuthorized:
            return flask_utils.unlogin_user(con)
        except NoteSearchException:
            return flask.render_template("message.html", message="Заметка не существует")

# page with all tags
@notesapp.route("/all_tags")
def all_tags():
    with common.get_con() as con:
        try:
            userid = flask_utils.get_logined_user_id(con)
            ns = NoteService(con)
            all_tags = ns.find_all_tags(userid)
            return flask.render_template("all_tags.html", all_tags=all_tags)
        except flask_utils.NotAuthorized:
            return flask_utils.unlogin_user(con)

