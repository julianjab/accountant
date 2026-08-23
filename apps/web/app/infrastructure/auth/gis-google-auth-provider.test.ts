import { afterEach, describe, expect, it, vi } from 'vitest'
import { GoogleAuthError } from '~/domain/errors/google-auth-error'
import { GisGoogleAuthProvider } from '~/infrastructure/auth/gis-google-auth-provider'

interface TokenCallbackResponse {
  access_token?: string
  error?: string
}

function stubGoogleAccounts(options: {
  onRequestAccessToken?: (respond: (response: TokenCallbackResponse) => void, triggerError: () => void) => void
  revoke?: (accessToken: string) => void
  hasGrantedAllScopes?: () => boolean
} = {}) {
  const initTokenClient = vi.fn((config: {
    callback: (response: TokenCallbackResponse) => void
    error_callback?: () => void
  }) => ({
    requestAccessToken: () => {
      if (options.onRequestAccessToken) {
        options.onRequestAccessToken(config.callback, () => config.error_callback?.())
      } else {
        config.callback({ access_token: 'access-token-123' })
      }
    }
  }))

  vi.stubGlobal('window', {
    google: {
      accounts: {
        oauth2: {
          initTokenClient,
          revoke: options.revoke ?? vi.fn(),
          hasGrantedAllScopes: options.hasGrantedAllScopes ?? (() => true)
        }
      }
    }
  })
}

describe('GisGoogleAuthProvider', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('rejects with missingClientId when no client id is configured', async () => {
    stubGoogleAccounts()
    const provider = new GisGoogleAuthProvider('')

    await expect(provider.signIn()).rejects.toThrow(GoogleAuthError)
  })

  it('signs in, fetches the profile and notifies listeners', async () => {
    stubGoogleAccounts()
    vi.stubGlobal('$fetch', vi.fn().mockResolvedValue({ email: 'jane@example.com', name: 'Jane Doe', picture: 'pic.png' }))

    const provider = new GisGoogleAuthProvider('client-id')
    const onChange = vi.fn()
    provider.onChange(onChange)

    const session = await provider.signIn()

    expect(session).toEqual({
      user: { email: 'jane@example.com', name: 'Jane Doe', picture: 'pic.png' },
      accessToken: 'access-token-123'
    })
    expect(onChange).toHaveBeenCalledWith(session)
  })

  it('rejects with driveDenied when the user declines the Drive scope', async () => {
    stubGoogleAccounts({ hasGrantedAllScopes: () => false })

    const provider = new GisGoogleAuthProvider('client-id')

    await expect(provider.signIn()).rejects.toThrow(GoogleAuthError)
  })

  it('rejects with popupClosed when the token request is cancelled', async () => {
    stubGoogleAccounts({
      onRequestAccessToken: (_respond, triggerError) => triggerError()
    })

    const provider = new GisGoogleAuthProvider('client-id')

    await expect(provider.signIn()).rejects.toThrow(GoogleAuthError)
  })

  it('reuses the cached access token on subsequent getAccessToken calls', async () => {
    stubGoogleAccounts()
    vi.stubGlobal('$fetch', vi.fn().mockResolvedValue({ email: 'jane@example.com', name: 'Jane Doe' }))

    const provider = new GisGoogleAuthProvider('client-id')
    await provider.signIn()

    const token = await provider.getAccessToken()

    expect(token).toBe('access-token-123')
  })

  it('clears the token and notifies listeners on sign out', async () => {
    const revoke = vi.fn()
    stubGoogleAccounts({ revoke })
    vi.stubGlobal('$fetch', vi.fn().mockResolvedValue({ email: 'jane@example.com', name: 'Jane Doe' }))

    const provider = new GisGoogleAuthProvider('client-id')
    await provider.signIn()

    const onChange = vi.fn()
    provider.onChange(onChange)
    provider.signOut()

    expect(revoke).toHaveBeenCalledWith('access-token-123')
    expect(onChange).toHaveBeenCalledWith(null)
  })
})
