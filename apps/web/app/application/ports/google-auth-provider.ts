import type { GoogleUser } from '~/domain/entities/google-user'

export interface GoogleAuthSession {
  user: GoogleUser
  accessToken: string
}

export interface GoogleAuthProvider {
  signIn: () => Promise<GoogleAuthSession>
  signOut: () => void
  getAccessToken: () => Promise<string>
  onChange: (callback: (session: GoogleAuthSession | null) => void) => void
}
