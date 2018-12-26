import flask
import mysql.connector
import html
import datetime
import urllib.parse

con = mysql.connector.connect(
	host="localhost",
	user="root",
	passwd="1234",
	database="tagged"
)
cur = con.cursor()

app = flask.Flask(__name__)

@app.template_filter("escapeurl")
def escapeurl_filter(s):
	return urllib.parse.quote_plus(s)

def validate_tag(tag):
	if not len(tag):
		return False
	for c in tag:
		if not (c in "_-" or c.isalnum()):
			return False
	return True

# main page: recent notes
@app.route("/")
def index_page():
	result = cur.execute("SELECT id,title,contents,date_created,tags,date_modified FROM notes ORDER BY date_modified DESC LIMIT 10");
	notes = cur.fetchall()
	return flask.render_template("index.html", notes=notes)

# new note page: add new note
@app.route("/new", methods=["GET", "POST"])
def new_page():
	if flask.request.method == "GET":
		return flask.render_template("new.html")
	elif flask.request.method == "POST":
		title = html.escape(flask.request.form.get("title", ""))
		contents = html.escape(flask.request.form.get("contents", "")).replace("\n", "<br>")
		rawTags = html.escape(flask.request.form.get("tags", "")).strip()
		tagList = rawTags.split()
		for tag in tagList:
			if not validate_tag(tag):
				return flask.render_template("message.html", message="Ошибка: метка может содержать только буквы, цифры, нижнее подчёркивание (_) или дефис(-).")
		tags = " ".join(tagList)
		curdt = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
		query = "INSERT INTO notes(title,contents,date_created,tags,date_modified)VALUES(%s,%s,%s,%s,%s)"
		cur.execute(query, (title, contents, curdt, tags, curdt))
		con.commit()
		return flask.render_template("message.html", message="Запись успешно добавлена")
	else:
		return flask.render_template("message.html", message="Метод не поддерживается")

# all notes page
@app.route("/all")
def all_page():
	result = cur.execute("SELECT id,title,contents,date_created,tags,date_modified FROM notes ORDER BY date_modified DESC");
	notes = cur.fetchall()
	return flask.render_template("all.html", notes=notes)

# search page
@app.route("/search")
def search_page():
	return flask.render_template("search.html")

# search results page
@app.route("/search/results")
def search_results_page():
	rawKeywords = flask.request.args.get("keywords", "").strip()
	rawTags = flask.request.args.get("tags", "").strip()
	if rawKeywords == "" and rawTags == "":
		return flask.render_template("message.html", message="Неправильные параметры поиска")
	keywords = rawKeywords.split()
	tags = rawTags.split()
	for tag in tags:
		if not validate_tag(tag):
			return flask.render_template("message.html", message="Неправильные параметры поиска")
	for keyword in keywords :
		if not validate_tag(keyword):
			return flask.render_template("message.html", message="Неправильные параметры поиска")
	keywordsLike = list(map(lambda k: ["%" + k + "%"]*2, keywords))
	keywordsLike1 = []
	for keywordLike in keywordsLike:
		keywordsLike1.extend(keywordLike)
	keywordsLike = keywordsLike1
	tagsLike = list(map(lambda t: "%" + t + "%", tags))
	queryParts = ["SELECT id,title,contents,date_created,tags,date_modified FROM notes WHERE "]
	if keywords:
		queryParts.append("(" + "OR".join(["(title LIKE %s OR contents LIKE %s)"] * len(keywords)) + ")")
		if tags:
			queryParts.append(" AND ")
	if tags:
		queryParts.append("(" + "OR".join(["(tags LIKE %s)"] * len(tags)) + ")")
	query = "".join(queryParts)
	cur.execute(query, keywordsLike + tagsLike)
	notes = cur.fetchall()
	return flask.render_template("search_results.html", keywords=keywords, tags=tags, notes=notes)

# delete page
@app.route("/delete/<int:noteid>", methods=["GET", "POST"])
def delete_noteid_page(noteid):
	if flask.request.method == "GET":
		return flask.render_template("delete_noteid.html", noteid=noteid)
	elif flask.request.method == "POST":
		query = "DELETE FROM notes WHERE id={}".format(noteid)
		cur.execute(query)
		con.commit()
		return flask.render_template("message.html", message="Удалено")
	else:
		return flask.render_template("message.html", message="Метод не поддерживается")

# specific note page
@app.route("/note/<int:noteid>")
def note_noteid_page(noteid):
	query = "SELECT id,title,tags,contents,date_created,date_modified FROM notes WHERE id={}".format(noteid)
	cur.execute(query)
	note = cur.fetchone()
	return flask.render_template("note_noteid.html", note=note)

# note editing page
@app.route("/edit/<int:noteid>", methods=["GET", "POST"])
def edit_noteid_page(noteid):
	if flask.request.method == "GET":
		query = "SELECT title,contents,tags FROM notes WHERE id={}".format(noteid)
		cur.execute(query)
		note = list(cur.fetchone())
		note[1] = note[1].replace("<br>", "\n")
		return flask.render_template("edit_noteid.html", note=note)
	elif flask.request.method == "POST":
		title = html.escape(flask.request.form.get("title", ""))
		contents = html.escape(flask.request.form.get("contents", "")).replace("\n", "<br>")
		rawTags = html.escape(flask.request.form.get("tags", "")).strip()
		tagList = rawTags.split()
		for tag in tagList:
			if not validate_tag(tag):
				return flask.render_template("message.html", message="Ошибка: метка может содержать только буквы, цифры, нижнее подчёркивание (_) или дефис(-).")
		tags = " ".join(tagList)
		curdt = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
		query = "UPDATE notes SET title=%s,contents=%s,tags=%s,date_modified=%s WHERE id={}".format(noteid)
		cur.execute(query, (title, contents, tags, curdt))
		con.commit()
		return flask.redirect(flask.url_for("note_noteid_page", noteid=noteid))
	else:
		return flask.render_template("message.html", message="Метод не поддерживается")
