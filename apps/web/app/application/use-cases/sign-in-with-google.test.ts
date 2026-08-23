import { describe, expect, it, vi } from 'vitest'
import { SignInWithGoogle } from './sign-in-with-google'
import type { GoogleAuthProvider } from '~/application/ports/google-auth-provider'

function makeProvider(): GoogleAuthProvider {
  return {
    startSignIn: vi.fn(),
    getCurrentUser: vi.fn(),
    signOut: vi.fn()
  }
}

describe('SignInWithGoogle', () => {
  it('hands the browser to the provider sign-in redirect', () => {
    const provider = makeProvider()

    new SignInWithGoogle(provider).execute()

    expect(provider.startSignIn).toHaveBeenCalledOnce()
  })
})
