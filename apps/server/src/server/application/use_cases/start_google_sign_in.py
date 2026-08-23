import secrets
from dataclasses import dataclass

from server.domain.ports import GoogleOAuthClient


@dataclass(frozen=True, slots=True)
class SignInRedirect:
    authorization_url: str
    state: str


class StartGoogleSignIn:
    """Builds the consent-screen redirect and the CSRF nonce that guards it.

    The nonce is returned rather than stored: where it is kept between the two
    legs of the flow (a cookie, today) is a delivery detail.
    """

    def __init__(self, oauth: GoogleOAuthClient) -> None:
        self._oauth = oauth

    def execute(self) -> SignInRedirect:
        state = secrets.token_urlsafe(32)
        return SignInRedirect(authorization_url=self._oauth.authorization_url(state), state=state)
