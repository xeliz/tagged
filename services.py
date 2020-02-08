
# Some classes with business logic.
# Independent from flask.

import datetime

from . import common

class UserSearchException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class UserService:

    def __init__(self, con):
        self.con = con

    def get_by_id(self, userid):
        query = """SELECT id, username, passhash FROM users WHERE id = %s"""
        cur = self.con.cursor()
        cur.execute(query, (userid,))
        userdata = common.fetchall_as_dict(cur) 
        cur.close()
        if not userdata:
            raise UserSearchException()
        return userdata[0]

    def get_by_name(self, username):
        query = """SELECT id, username, passhash FROM users WHERE username = %s"""
        cur = self.con.cursor()
        cur.execute(query, (username,))
        userdata = common.fetchall_as_dict(cur) 
        cur.close()
        if not userdata:
            return None
        return userdata[0]

    def create_user(self, username, password):
        passhash = base64.b64encode(hashlib.md5(password1.encode("UTF-8")).digest()).decode("UTF-8")
        query = """INSERT INTO users (username, passhash) VALUES (%s, %s)"""
        cur = self.con.cursor()
        cur.execute(query, (username, passhash))
        self.con.commit()

class SessionService:

    def __init__(self, con):
        self.con = con

    def get_userid(self, token):
        query = """SELECT userid FROM sessions, users WHERE sessions.active = TRUE AND sessions.userid = users.id AND sessions.id = %s"""
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
        query = """SELECT * FROM sessions WHERE id = %s"""
        cur = self.con.cursor()
        cur.execute(query, (token,))
        if cur.fetchall():
            return True
        return False

    def create_session(self, userid, token):
        query = """INSERT INTO sessions (id, userid, active) VALUES (%s, %s, TRUE)"""
        cur = self.con.cursor()
        cur.execute(query, (token, userid))
        cur.close()

    def deactivate_session(self, token):
        query = """UPDATE sessions SET active = FALSE where id = %s"""
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
        query =  """SELECT id,title,contents,date_created,tags,date_modified FROM notes WHERE userid=%s ORDER BY date_modified DESC LIMIT %s"""
        cur = self.con.cursor()
        cur.execute(query, (userid, n))
        notes = common.fetchall_as_dict(cur)
        cur.close()
        return notes

    def get_all_notes(self, userid):
        query =  """SELECT id,title,contents,date_created,tags,date_modified FROM notes WHERE userid=%s ORDER BY date_modified DESC"""
        cur = self.con.cursor()
        cur.execute(query, (userid,))
        notes = common.fetchall_as_dict(cur)
        cur.close()
        return notes

    def get_note(self, userid, noteid):
        query = """SELECT id,title,tags,contents,date_created,date_modified FROM notes WHERE id=%s AND userid=%s"""
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
        queryParts = ["""SELECT id,title,contents,date_created,tags,date_modified FROM notes WHERE userid=%s """]
        if keywords:
            queryParts.append(" AND ")
            queryParts.append("(" + "OR".join(["(title LIKE %s OR contents LIKE %s)"] * len(keywords)) + ")")
        if tags:
            queryParts.append(" AND ")
            queryParts.append("(" + "OR".join(["(tags LIKE %s)"] * len(tags)) + ")")
        query = "".join(queryParts)

        cur = self.con.cursor()
        cur.execute(query, [userid] + keywordsLike + tagsLike)
        notes = common.fetchall_as_dict(cur)
        cur.close()
        return notes

    def delete_note(self, userid, noteid):
        query = """DELETE FROM notes WHERE id=%s and userid=%s"""
        cur = self.con.cursor()
        cur.execute(query, (noteid, userid))
        n = cur.rowcount
        self.con.commit()
        cur.close()
        return n == 1

    def create_note(self, userid, title, contents, tags):
        query = """INSERT INTO notes(title,contents,date_created,tags,date_modified,userid)VALUES(%s,%s,%s,%s,%s,%s)"""
        tags = " ".join(tags)
        curdt = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
        cur = self.con.cursor()
        cur.execute(query, (title, contents, curdt, tags, curdt, userid))
        noteid = cur.lastrowid
        cur.close()
        self.con.commit()
        return noteid

    def update_note(self, userid, noteid, title, contents, tags):
        query = "UPDATE notes SET title=%s,contents=%s,tags=%s,date_modified=%s WHERE id=%s"
        tags = " ".join(tags)
        curdt = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
        cur = self.con.cursor()
        cur.execute(query, (title, contents, tags, curdt, noteid))
        cur.close()
        self.con.commit()

    def find_all_tags(self, userid):
        query = "SELECT tags FROM notes where userid=%s"
        cur = self.con.cursor()
        cur.execute(query, (userid,))
        tags = common.fetchall_as_dict(cur)
        cur.close()
        tags = [tag["tags"] for tag in tags]
        tags = " ".join(tags).split(" ")
        tags = list(set(tags))
        tags.sort()
        return tags

