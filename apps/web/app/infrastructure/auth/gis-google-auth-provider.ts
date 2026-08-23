import type { GoogleUser } from '~/domain/entities/google-user'
import { GoogleAuthError } from '~/domain/errors/google-auth-error'
import type { GoogleAuthProvider, GoogleAuthSession } from '~/application/ports/google-auth-provider'

const OAUTH_SCOPES = 'https://www.googleapis.com/auth/drive.readonly openid email profile'
const GIS_SCRIPT_SRC = 'https://accounts.google.com/gsi/client'
const USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'
const TOKEN_EXPIRY_BUFFER_MS = 60_000

interface TokenResponse {
  access_token?: string
  expires_in?: number
  error?: string
}

interface TokenClient {
  requestAccessToken: (options?: { prompt?: string }) => void
}

interface GoogleAccountsOauth2 {
  initTokenClient: (config: {
    client_id: string
    scope: string
    callback: (response: TokenResponse) => void
    error_callback?: (error: { type: string }) => void
  }) => TokenClient
  revoke: (accessToken: string, callback?: () => void) => void
}

declare global {
  interface Window {
    google?: {
      accounts: {
        oauth2: GoogleAccountsOauth2
      }
    }
  }
}

interface UserInfoDto {
  email: string
  name: string
  picture?: string
}

interface TokenResult {
  accessToken: string
  expiresAt: number
}

function toGoogleUser(dto: UserInfoDto): GoogleUser {
  return {
    email: dto.email,
    name: dto.name,
    picture: dto.picture ?? null
  }
}

let scriptLoadPromise: Promise<void> | null = null

function loadGisScript(): Promise<void> {
  if (window.google?.accounts?.oauth2) {
    return Promise.resolve()
  }

  if (!scriptLoadPromise) {
    scriptLoadPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.src = GIS_SCRIPT_SRC
      script.async = true
      script.defer = true
      script.onload = () => resolve()
      script.onerror = () => {
        scriptLoadPromise = null
        reject(new Error('Failed to load Google Identity Services script'))
      }
      document.head.appendChild(script)
    })
  }

  return scriptLoadPromise
}

export class GisGoogleAuthProvider implements GoogleAuthProvider {
  private accessToken: string | null = null
  private tokenExpiresAt: number | null = null
  private changeCallbacks: Array<(session: GoogleAuthSession | null) => void> = []
  private pendingTokenRequest: Promise<TokenResult> | null = null

  constructor(private readonly clientId: string) {}

  private async fetchUser(accessToken: string): Promise<GoogleUser> {
    try {
      const dto = await $fetch<UserInfoDto>(USERINFO_URL, {
        headers: { Authorization: `Bearer ${accessToken}` }
      })
      return toGoogleUser(dto)
    } catch {
      throw new GoogleAuthError('driveDenied')
    }
  }

  private requestToken(prompt: string): Promise<TokenResult> {
    if (this.pendingTokenRequest) {
      return this.pendingTokenRequest
    }

    const request = this.performTokenRequest(prompt).finally(() => {
      this.pendingTokenRequest = null
    })
    this.pendingTokenRequest = request
    return request
  }

  private async performTokenRequest(prompt: string): Promise<TokenResult> {
    if (!this.clientId) {
      throw new GoogleAuthError('missingClientId')
    }

    await loadGisScript()

    return new Promise<TokenResult>((resolve, reject) => {
      const tokenClient: TokenClient = window.google!.accounts.oauth2.initTokenClient({
        client_id: this.clientId,
        scope: OAUTH_SCOPES,
        callback: (response) => {
          if (response.error || !response.access_token) {
            reject(new GoogleAuthError(response.error === 'popup_closed' ? 'popupClosed' : 'driveDenied'))
            return
          }
          resolve({
            accessToken: response.access_token,
            expiresAt: Date.now() + (response.expires_in ?? 3600) * 1000
          })
        },
        error_callback: () => {
          reject(new GoogleAuthError('popupClosed'))
        }
      })
      tokenClient.requestAccessToken({ prompt })
    })
  }

  private hasValidToken(): boolean {
    return this.accessToken !== null && this.tokenExpiresAt !== null && Date.now() < this.tokenExpiresAt - TOKEN_EXPIRY_BUFFER_MS
  }

  async signIn(): Promise<GoogleAuthSession> {
    const { accessToken, expiresAt } = await this.requestToken('consent')

    let user: GoogleUser
    try {
      user = await this.fetchUser(accessToken)
    } catch (error) {
      this.accessToken = null
      this.tokenExpiresAt = null
      throw error
    }

    this.accessToken = accessToken
    this.tokenExpiresAt = expiresAt
    const session: GoogleAuthSession = { user, accessToken }
    this.notifyChange(session)
    return session
  }

  signOut(): void {
    const token = this.accessToken
    this.accessToken = null
    this.tokenExpiresAt = null
    this.notifyChange(null)

    if (token) {
      window.google?.accounts.oauth2.revoke(token)
    }
  }

  async getAccessToken(): Promise<string> {
    if (this.hasValidToken()) {
      return this.accessToken!
    }

    const { accessToken, expiresAt } = await this.requestToken('')
    this.accessToken = accessToken
    this.tokenExpiresAt = expiresAt
    return accessToken
  }

  onChange(callback: (session: GoogleAuthSession | null) => void): void {
    this.changeCallbacks.push(callback)
  }

  private notifyChange(session: GoogleAuthSession | null): void {
    this.changeCallbacks.forEach(callback => callback(session))
  }
}
