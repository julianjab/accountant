import { describe, expect, it } from 'vitest'
import type { GoogleAuthSession, GoogleAuthProvider } from '~/application/ports/google-auth-provider'
import { SignOut } from '~/application/use-cases/sign-out'

class FakeGoogleAuthProvider implements GoogleAuthProvider {
  signOutCalled = false

  signIn(): Promise<GoogleAuthSession> {
    throw new Error('not implemented')
  }

  signOut(): void {
    this.signOutCalled = true
  }

  getAccessToken(): Promise<string> {
    throw new Error('not implemented')
  }

  onChange(): void {}
}

describe('SignOut', () => {
  it('delegates to the auth provider', () => {
    const provider = new FakeGoogleAuthProvider()
    const useCase = new SignOut(provider)

    useCase.execute()

    expect(provider.signOutCalled).toBe(true)
  })
})
