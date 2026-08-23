import contextlib

from server.domain.ports import GoogleOAuthClient, SessionRepository


class SignOutGoogle:
    """Drops the stored session and revokes the grant with Google."""

    def __init__(self, oauth: GoogleOAuthClient, sessions: SessionRepository) -> None:
        self._oauth = oauth
        self._sessions = sessions

    def execute(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        self._sessions.delete(session_id)

        if session is not None:
            # Revocation is best-effort: the local session is already gone.
            with contextlib.suppress(Exception):
                self._oauth.revoke(session.refresh_token)
