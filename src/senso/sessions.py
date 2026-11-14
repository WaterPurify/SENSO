"""Persistent authorization at the repository boundary, including transaction lifetime."""

from contextlib import contextmanager
from weakref import WeakSet

from senso.auth import AuthError
from senso.db.database import open_database

_active = WeakSet()


class DataSession:
    def __init__(self, store, user):
        self.store, self.user = store, user
        self.closed = False
        self.on_revoke = None
        self._transaction = None
        with self.access():
            directory = user.directory(store.root)
            self._conn = open_database(directory / "senso.db")
        _active.add(self)

    @contextmanager
    def access(self):
        # The accounts read lock prevents password/deletion commits while a data
        # operation is in progress, including a photo + repository save.
        try:
            with self.store.connection() as auth:
                auth.execute("BEGIN")
                row = auth.execute(
                    "SELECT session_version, deleting FROM users WHERE id = ?", (self.user.id,)
                ).fetchone()
                if (
                    self.closed
                    or not row
                    or row["deleting"]
                    or (row["session_version"] != self.user.session_version)
                ):
                    raise AuthError("로그인이 만료됐어요. 다시 로그인해 주세요.")
                yield
        except AuthError:
            # Release the accounts read lock before rebuilding the login UI.
            if self.on_revoke and not self.closed:
                self.on_revoke()
            raise

    def execute(self, sql, parameters=()):
        with self.access():
            return self._conn.execute(sql, parameters)

    def __enter__(self):
        self._transaction = self.access()
        self._transaction.__enter__()
        return self

    def __exit__(self, *exc):
        try:
            return self._conn.__exit__(*exc)
        finally:
            self._transaction.__exit__(*exc)
            self._transaction = None

    def close(self):
        if not self.closed:
            self.closed = True
            self._conn.close()
            _active.discard(self)

    def revoke_others(self, *, include_self=False):
        # Called on the UI event loop, never from the password-hashing worker.
        for session in list(_active):
            if session.user.id == self.user.id and (include_self or session is not self):
                if session.on_revoke:
                    session.on_revoke()
                else:
                    session.close()
