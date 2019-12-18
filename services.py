
# Some classes with business logic.
# Independent from flask.

from . import common

class UserService:

    def __init__(self, con=None):
        if con is None:
            self.con = common.get_connection()
        else:
            self.con = con

    def close_connection(self):
        self.con.close()

    def get_by_id(self, userid):
        query = """SELECT id, username, passhash FROM users WHERE id = %s"""
        cur = self.con.cursor()
        cur.execute(query, (userid,))
        userdata = common.fetchall_as_dict(cur) 
        cur.close()
        if not userdata:
            return None
        return userdata

    def get_by_name(self, username):
        query = """SELECT id, username, passhash FROM users WHERE username = %s"""
        cur = self.con.cursor()
        cur.execute(query, (userid,))
        userdata = common.fetchall_as_dict(cur) 
        cur.close()
        if not userdata:
            return None
        return userdata

class SessionService:

    def __init__(self, con=None):
        if con is None:
            self.con = common.get_connection()
        else:
            self.con = con

    def close(self):
        self.con.close()

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

    def deactivate_session(self, token):
        query = """UPDATE sessions SET active = FALSE where id = %s"""
        cur = self.con.cursor()
        cur.execute(query, (token,))
        cur.close()

class NoteService:

    def __init__(self, con=None):
        if con is None:
            self.con = common.get_connection()
        else:
            self.con = con

    def close(self):
        self.con.close()

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

