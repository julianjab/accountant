import { describe, expect, it, vi } from 'vitest'
import { SignOut } from './sign-out'
import type { GoogleAuthProvider } from '~/application/ports/google-auth-provider'

describe('SignOut', () => {
  it('delegates to the provider', async () => {
    const provider: GoogleAuthProvider = {
      startSignIn: vi.fn(),
      getCurrentUser: vi.fn(),
      signOut: vi.fn().mockResolvedValue(undefined)
    }

    await new SignOut(provider).execute()

    expect(provider.signOut).toHaveBeenCalledOnce()
  })
})
