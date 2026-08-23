import type { GoogleUser } from '~/domain/entities/google-user'

export interface GoogleAuthProvider {
  /** Leaves the app: the browser is handed to Google's consent screen. */
  startSignIn: () => void
  /** The signed-in user, or null when there is no live session. */
  getCurrentUser: () => Promise<GoogleUser | null>
  signOut: () => Promise<void>
}
