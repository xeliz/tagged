
# Some classes with business logic.
# Independent from flask.

import datetime
import base64
import hashlib

from . import common

class UserSearchException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class UserService:

    def __init__(self, con):
        self.con = con

    def get_by_id(self, userid):
        query = """SELECT id, username, passhash FROM users WHERE id = ?"""
        cur = self.con.cursor()
        cur.execute(query, (userid,))
        userdata = common.fetchall_as_dict(cur) 
        cur.close()
        if not userdata:
            raise UserSearchException()
        return userdata[0]

    def get_by_name(self, username):
        query = """SELECT id, username, passhash FROM users WHERE username = ?"""
        cur = self.con.cursor()
        cur.execute(query, (username,))
        userdata = common.fetchall_as_dict(cur) 
        cur.close()
        if not userdata:
            return None
        return userdata[0]

    def create_user(self, username, password):
        passhash = base64.b64encode(hashlib.md5(password.encode("UTF-8")).digest()).decode("UTF-8")
        query = """INSERT INTO users (username, passhash) VALUES (?, ?)"""
        cur = self.con.cursor()
        cur.execute(query, (username, passhash))
        self.con.commit()

class SessionService:

    def __init__(self, con):
        self.con = con

    def get_userid(self, token):
        query = """SELECT userid FROM sessions, users WHERE sessions.active = TRUE AND sessions.userid = users.id AND sessions.id = ?"""
        cur = self.con.cursor()
        cur.execute(query, (token,))
        userids = cur.fetchall()
        cur.close()
        # if token was wrong, no rows are returned
        if not userids:
            return None
        # otherwise, a single row is returned
        return userids[0][0]

    def session_exists(self, token):
        query = """SELECT * FROM sessions WHERE id = ?"""
        cur = self.con.cursor()
        cur.execute(query, (token,))
        if cur.fetchall():
            return True
        return False

    def create_session(self, userid, token):
        query = """INSERT INTO sessions (id, userid, active) VALUES (?, ?, TRUE)"""
        cur = self.con.cursor()
        cur.execute(query, (token, userid))
        cur.close()

    def deactivate_session(self, token):
        query = """UPDATE sessions SET active = FALSE where id = ?"""
        cur = self.con.cursor()
        cur.execute(query, (token,))
        cur.close()

class NoteSearchException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class NoteService:

    def __init__(self, con):
        self.con = con

    def get_last_notes(self, userid, n=10):
        query =  """SELECT id,title,contents,date_created,tags,date_modified FROM notes WHERE userid=? ORDER BY date(date_modified) DESC LIMIT ?"""
        cur = self.con.cursor()
        cur.execute(query, (userid, n))
        notes = common.fetchall_as_dict(cur)
        cur.close()
        return notes

    def get_all_notes(self, userid):
        query =  """SELECT id,title,contents,date_created,tags,date_modified FROM notes WHERE userid=? ORDER BY date(date_modified) DESC"""
        cur = self.con.cursor()
        cur.execute(query, (userid,))
        notes = common.fetchall_as_dict(cur)
        cur.close()
        return notes

    def get_note(self, userid, noteid):
        query = """SELECT id,title,tags,contents,date_created,date_modified FROM notes WHERE id=? AND userid=?"""
        cur = self.con.cursor()
        cur.execute(query, (noteid, userid))
        result = common.fetchall_as_dict(cur)
        cur.close()
        if not result:
            raise NoteSearchException()
        return result[0]

    def search_notes(self, userid, keywords, tags):
        if not keywords and not tags:
            raise NoteSearchException()
        if not all(map(common.validate_tag, tags)):
            raise NoteSearchException()
        if not all(map(common.validate_tag, keywords)):
            raise NoteSearchException()
        keywordsLike = list(map(lambda k: ["%" + k + "%"]*2, keywords))
        keywordsLike = sum(keywordsLike, [])
        tagsLike = list(map(lambda t: "%" + t + "%", tags))
        queryParts = ["""SELECT id,title,contents,date_created,tags,date_modified FROM notes WHERE userid=? """]
        if keywords:
            queryParts.append(" AND ")
            queryParts.append("(" + "OR".join(["(title LIKE ? OR contents LIKE ?)"] * len(keywords)) + ")")
        if tags:
            queryParts.append(" AND ")
            queryParts.append("(" + "OR".join(["(tags LIKE ?)"] * len(tags)) + ")")
        query = "".join(queryParts)

        cur = self.con.cursor()
        cur.execute(query, [userid] + keywordsLike + tagsLike)
        notes = common.fetchall_as_dict(cur)
        cur.close()
        return notes

    def delete_note(self, userid, noteid):
        query = """DELETE FROM notes WHERE id=? and userid=?"""
        cur = self.con.cursor()
        cur.execute(query, (noteid, userid))
        n = cur.rowcount
        self.con.commit()
        cur.close()
        return n == 1

    def create_note(self, userid, title, contents, tags):
        query = """INSERT INTO notes(title,contents,date_created,tags,date_modified,userid)VALUES(?,?,?,?,?,?)"""
        tags = " ".join(tags)
        curdt = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
        cur = self.con.cursor()
        cur.execute(query, (title, contents, curdt, tags, curdt, userid))
        noteid = cur.lastrowid
        cur.close()
        self.con.commit()
        return noteid

    def update_note(self, userid, noteid, title, contents, tags):
        query = "UPDATE notes SET title=?,contents=?,tags=?,date_modified=? WHERE id=?"
        tags = " ".join(tags)
        curdt = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
        cur = self.con.cursor()
        cur.execute(query, (title, contents, tags, curdt, noteid))
        cur.close()
        self.con.commit()

    def find_all_tags(self, userid):
        query = "SELECT tags FROM notes where userid=?"
        cur = self.con.cursor()
        cur.execute(query, (userid,))
        tags = common.fetchall_as_dict(cur)
        cur.close()
        tags = [tag["tags"] for tag in tags]
        tags = " ".join(tags).split(" ")
        tags = list(set(tags))
        tags.sort()
        return tags

    def upload(self, userid, notes):
        query = """INSERT INTO notes(title,contents,date_created,tags,date_modified,userid)VALUES(?,?,?,?,?,?)"""
        cur = self.con.cursor()
        for note in notes:
            cur.execute(query, (
                note["title"],
                note["contents"],
                note["date_created"],
                note["tags"],
                note["date_modified"],
                userid,
            ))
        cur.close()
        self.con.commit()

