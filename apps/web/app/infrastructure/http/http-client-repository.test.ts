import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { HttpClientRepository } from './http-client-repository'

const BASE = 'http://server.test'
const fetchMock = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('$fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('HttpClientRepository', () => {
  it('maps the snake_case payload to the domain entity', async () => {
    fetchMock.mockResolvedValue([
      { id: '1', name: 'Jane', tax_id: '123', email: null, created_at: '2026-01-01' }
    ])

    await expect(new HttpClientRepository(BASE).list()).resolves.toEqual([
      { id: '1', name: 'Jane', taxId: '123', email: null, createdAt: '2026-01-01' }
    ])
  })

  it('sends the session cookie when listing, since the endpoint is authenticated', async () => {
    fetchMock.mockResolvedValue([])

    await new HttpClientRepository(BASE).list()

    expect(fetchMock).toHaveBeenCalledWith('/clients', {
      baseURL: BASE,
      credentials: 'include'
    })
  })

  it('sends the session cookie when registering', async () => {
    fetchMock.mockResolvedValue({
      id: '1', name: 'Jane', tax_id: '123', email: null, created_at: '2026-01-01'
    })

    await new HttpClientRepository(BASE).register({ name: 'Jane', taxId: '123', email: null })

    expect(fetchMock).toHaveBeenCalledWith('/clients', {
      baseURL: BASE,
      credentials: 'include',
      method: 'POST',
      body: { name: 'Jane', tax_id: '123', email: null }
    })
  })
})
