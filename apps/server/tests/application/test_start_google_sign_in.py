from server.application.use_cases import StartGoogleSignIn


class FakeOAuth:
    def __init__(self) -> None:
        self.states: list[str] = []

    def authorization_url(self, state: str) -> str:
        self.states.append(state)
        return f"https://accounts.google.com/auth?state={state}"

    def exchange_code(self, code): ...
    def refresh(self, refresh_token): ...
    def fetch_user(self, access_token): ...
    def revoke(self, token): ...


def test_returns_the_url_carrying_the_generated_state():
    oauth = FakeOAuth()

    redirect = StartGoogleSignIn(oauth).execute()

    assert oauth.states == [redirect.state]
    assert redirect.state in redirect.authorization_url


def test_each_sign_in_gets_a_fresh_state():
    oauth = FakeOAuth()
    use_case = StartGoogleSignIn(oauth)

    first = use_case.execute()
    second = use_case.execute()

    # A reused nonce would defeat the CSRF check in the callback.
    assert first.state != second.state
