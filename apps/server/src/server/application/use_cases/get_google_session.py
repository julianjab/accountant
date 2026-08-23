from datetime import UTC, datetime, timedelta

from server.domain.entities import GoogleSession
from server.domain.ports import GoogleOAuthClient, OAuthGrantRevoked, SessionRepository


class GetGoogleSession:
    """Loads a session by id, refreshing its access token when it has expired.

    This is what makes the login survive reloads: the browser only ever holds the
    session id, and the short-lived access token is renewed here from the stored
    refresh token.
    """

    def __init__(
        self, oauth: GoogleOAuthClient, sessions: SessionRepository, max_age: timedelta
    ) -> None:
        self._oauth = oauth
        self._sessions = sessions
        self._max_age = max_age

    def execute(self, session_id: str) -> GoogleSession | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None

        now = datetime.now(UTC)
        if now - session.created_at >= self._max_age:
            # An absolute cap, so a stolen session cannot be renewed forever.
            self._sessions.delete(session_id)
            return None

        if not session.is_expired(now):
            return session

        try:
            tokens = self._oauth.refresh(session.refresh_token)
        except OAuthGrantRevoked:
            self._sessions.delete(session_id)
            return None
        # Any other failure (timeout, 5xx, DNS) propagates: a network blip must
        # not cost the user their grant.

        refreshed = GoogleSession(
            id=session.id,
            user=session.user,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token or session.refresh_token,
            expires_at=tokens.expires_at,
            created_at=session.created_at,
        )
        self._sessions.save(refreshed)
        return refreshed
