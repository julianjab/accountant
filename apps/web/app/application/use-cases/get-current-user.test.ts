import { describe, expect, it, vi } from 'vitest'
import { GetCurrentUser } from './get-current-user'
import type { GoogleAuthProvider } from '~/application/ports/google-auth-provider'

const USER = { email: 'a@b.com', name: 'A B', picture: null }

function makeProvider(user: typeof USER | null): GoogleAuthProvider {
  return {
    startSignIn: vi.fn(),
    getCurrentUser: vi.fn().mockResolvedValue(user),
    signOut: vi.fn()
  }
}

describe('GetCurrentUser', () => {
  it('returns the signed-in user', async () => {
    await expect(new GetCurrentUser(makeProvider(USER)).execute()).resolves.toEqual(USER)
  })

  it('returns null when there is no live session', async () => {
    await expect(new GetCurrentUser(makeProvider(null)).execute()).resolves.toBeNull()
  })
})
