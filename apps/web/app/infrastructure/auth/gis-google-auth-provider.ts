import type { GoogleUser } from '~/domain/entities/google-user'
import { GoogleAuthError } from '~/domain/errors/google-auth-error'
import type { GoogleAuthProvider, GoogleAuthSession } from '~/application/ports/google-auth-provider'

const DRIVE_READONLY_SCOPE = 'https://www.googleapis.com/auth/drive.readonly'
const GIS_SCRIPT_SRC = 'https://accounts.google.com/gsi/client'
const USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'

interface TokenResponse {
  access_token?: string
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
      script.onerror = () => reject(new Error('Failed to load Google Identity Services script'))
      document.head.appendChild(script)
    })
  }

  return scriptLoadPromise
}

export class GisGoogleAuthProvider implements GoogleAuthProvider {
  private accessToken: string | null = null
  private changeCallbacks: Array<(session: GoogleAuthSession | null) => void> = []

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

  private async requestToken(prompt: string): Promise<string> {
    if (!this.clientId) {
      throw new GoogleAuthError('missingClientId')
    }

    await loadGisScript()

    return new Promise<string>((resolve, reject) => {
      const tokenClient: TokenClient = window.google!.accounts.oauth2.initTokenClient({
        client_id: this.clientId,
        scope: DRIVE_READONLY_SCOPE,
        callback: (response) => {
          if (response.error || !response.access_token) {
            reject(new GoogleAuthError(response.error === 'popup_closed' ? 'popupClosed' : 'driveDenied'))
            return
          }
          resolve(response.access_token)
        },
        error_callback: () => {
          reject(new GoogleAuthError('popupClosed'))
        }
      })
      tokenClient.requestAccessToken({ prompt })
    })
  }

  async signIn(): Promise<GoogleAuthSession> {
    const accessToken = await this.requestToken('consent')
    this.accessToken = accessToken

    const user = await this.fetchUser(accessToken)
    const session: GoogleAuthSession = { user, accessToken }
    this.notifyChange(session)
    return session
  }

  signOut(): void {
    const token = this.accessToken
    this.accessToken = null
    this.notifyChange(null)

    if (token) {
      window.google?.accounts.oauth2.revoke(token)
    }
  }

  async getAccessToken(): Promise<string> {
    if (this.accessToken) {
      return this.accessToken
    }

    const accessToken = await this.requestToken('')
    this.accessToken = accessToken
    return accessToken
  }

  onChange(callback: (session: GoogleAuthSession | null) => void): void {
    this.changeCallbacks.push(callback)
  }

  private notifyChange(session: GoogleAuthSession | null): void {
    this.changeCallbacks.forEach(callback => callback(session))
  }
}
