import { afterEach, describe, expect, it, vi } from 'vitest'
import { GoogleAuthError } from '~/domain/errors/google-auth-error'
import { DriveApiRepository } from '~/infrastructure/http/drive-api-repository'

describe('DriveApiRepository', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns the owner email from the Drive about endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ user: { emailAddress: 'jane@example.com' } })
    vi.stubGlobal('$fetch', fetchMock)

    const repository = new DriveApiRepository()
    const result = await repository.getCurrentUser('token-123')

    expect(result).toEqual({ email: 'jane@example.com' })
    expect(fetchMock).toHaveBeenCalledWith(
      'https://www.googleapis.com/drive/v3/about',
      expect.objectContaining({
        query: { fields: 'user' },
        headers: { Authorization: 'Bearer token-123' }
      })
    )
  })

  it('throws a GoogleAuthError when the request fails', async () => {
    vi.stubGlobal('$fetch', vi.fn().mockRejectedValue(new Error('401 Unauthorized')))

    const repository = new DriveApiRepository()

    await expect(repository.getCurrentUser('bad-token')).rejects.toThrow(GoogleAuthError)
  })
})
