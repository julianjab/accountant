import type { GoogleUser } from '~/domain/entities/google-user'
import { GoogleAuthError } from '~/domain/errors/google-auth-error'
import type { GoogleAuthProvider } from '~/application/ports/google-auth-provider'

interface GoogleUserDto {
  email: string
  name: string
  picture: string | null
}

/**
 * Reads the login from the server's session cookie.
 *
 * The access token never reaches the browser: the server holds it along with the
 * refresh token, so the session survives reloads and this app only ever learns
 * who is signed in.
 */
export class ServerSessionAuthProvider implements GoogleAuthProvider {
  constructor(private readonly serverApiBase: string) {}

  startSignIn(): void {
    // A full-page redirect, not a popup: the callback needs to set an httpOnly
    // cookie on the server's origin.
    window.location.href = `${this.serverApiBase}/auth/google/login`
  }

  async getCurrentUser(): Promise<GoogleUser | null> {
    try {
      const dto = await $fetch<GoogleUserDto>(`${this.serverApiBase}/auth/google/me`, {
        credentials: 'include'
      })
      return { email: dto.email, name: dto.name, picture: dto.picture }
    } catch (error) {
      if ((error as { statusCode?: number }).statusCode === 401) {
        return null
      }
      throw new GoogleAuthError('sessionUnavailable')
    }
  }

  async signOut(): Promise<void> {
    await $fetch(`${this.serverApiBase}/auth/google/logout`, {
      method: 'POST',
      credentials: 'include'
    })
  }
}
