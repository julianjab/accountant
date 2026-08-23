import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ServerSessionAuthProvider } from './server-session-auth-provider'
import { GoogleAuthError } from '~/domain/errors/google-auth-error'

const BASE = 'http://server.test'

const fetchMock = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('$fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('ServerSessionAuthProvider', () => {
  describe('startSignIn', () => {
    it('sends the browser to the server login endpoint', () => {
      const location = { href: '' }
      vi.stubGlobal('window', { location })

      new ServerSessionAuthProvider(BASE).startSignIn()

      expect(location.href).toBe(`${BASE}/auth/google/login`)
    })
  })

  describe('getCurrentUser', () => {
    it('returns the user described by the session cookie', async () => {
      fetchMock.mockResolvedValue({ email: 'a@b.com', name: 'A B', picture: 'p.png' })

      const user = await new ServerSessionAuthProvider(BASE).getCurrentUser()

      expect(user).toEqual({ email: 'a@b.com', name: 'A B', picture: 'p.png' })
      expect(fetchMock).toHaveBeenCalledWith(`${BASE}/auth/google/me`, {
        credentials: 'include'
      })
    })

    it('returns null when the server reports no session', async () => {
      fetchMock.mockRejectedValue({ statusCode: 401 })

      await expect(new ServerSessionAuthProvider(BASE).getCurrentUser()).resolves.toBeNull()
    })

    it('raises when the server is unreachable, to keep it distinct from being signed out', async () => {
      fetchMock.mockRejectedValue({ statusCode: 500 })

      await expect(new ServerSessionAuthProvider(BASE).getCurrentUser()).rejects.toBeInstanceOf(
        GoogleAuthError
      )
    })
  })

  describe('signOut', () => {
    it('posts to the server logout endpoint with the session cookie', async () => {
      fetchMock.mockResolvedValue(undefined)

      await new ServerSessionAuthProvider(BASE).signOut()

      expect(fetchMock).toHaveBeenCalledWith(`${BASE}/auth/google/logout`, {
        method: 'POST',
        credentials: 'include'
      })
    })
  })
})
