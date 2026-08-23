from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class GoogleUser:
    email: str
    name: str
    picture: str | None


@dataclass(frozen=True, slots=True)
class GoogleSession:
    """A signed-in user's Drive grant, held server-side and addressed by an opaque id.

    ``access_token`` is short-lived and refreshed from ``refresh_token``; only the
    session id ever reaches the browser (as an httpOnly cookie).
    """

    id: str
    user: GoogleUser
    access_token: str
    refresh_token: str
    expires_at: datetime

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at
