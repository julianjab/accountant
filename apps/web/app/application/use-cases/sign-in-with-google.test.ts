import { describe, expect, it } from 'vitest'
import type { GoogleAuthSession, GoogleAuthProvider } from '~/application/ports/google-auth-provider'
import { SignInWithGoogle } from '~/application/use-cases/sign-in-with-google'

class FakeGoogleAuthProvider implements GoogleAuthProvider {
  constructor(private readonly session: GoogleAuthSession) {}

  signIn(): Promise<GoogleAuthSession> {
    return Promise.resolve(this.session)
  }

  signOut(): void {}

  getAccessToken(): Promise<string> {
    return Promise.resolve(this.session.accessToken)
  }

  onChange(): void {}
}

describe('SignInWithGoogle', () => {
  it('returns the session from the auth provider', async () => {
    const session: GoogleAuthSession = {
      user: { email: 'jane@example.com', name: 'Jane Doe', picture: null },
      accessToken: 'token-123'
    }
    const useCase = new SignInWithGoogle(new FakeGoogleAuthProvider(session))

    await expect(useCase.execute()).resolves.toEqual(session)
  })
})
