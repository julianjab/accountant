import uuid
from datetime import UTC, datetime

from server.domain.entities import GoogleSession
from server.domain.ports import GoogleOAuthClient, SessionRepository


class MissingRefreshToken(Exception):
    """Google withheld a refresh token, so the session could not be persisted.

    Google only issues one on the first consent for a client; re-consent with
    ``prompt=consent`` is required to get another.
    """


class CompleteGoogleSignIn:
    """Turns an OAuth authorization code into a stored, server-side session."""

    def __init__(self, oauth: GoogleOAuthClient, sessions: SessionRepository) -> None:
        self._oauth = oauth
        self._sessions = sessions

    def execute(self, code: str) -> GoogleSession:
        tokens = self._oauth.exchange_code(code)
        if tokens.refresh_token is None:
            raise MissingRefreshToken

        user = self._oauth.fetch_user(tokens.access_token)
        # Each sign-in forces re-consent and yields a fresh refresh token, so
        # keeping the old ones would leave live Drive credentials lying around
        # with no way to reach them.
        self._sessions.delete_for_user(user.email)

        session = GoogleSession(
            id=uuid.uuid4().hex,
            user=user,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_at=tokens.expires_at,
            created_at=datetime.now(UTC),
        )
        self._sessions.save(session)
        return session
