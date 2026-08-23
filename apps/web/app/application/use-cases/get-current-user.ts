import type { GoogleUser } from '~/domain/entities/google-user'
import type { GoogleAuthProvider } from '~/application/ports/google-auth-provider'

export class GetCurrentUser {
  constructor(private readonly authProvider: GoogleAuthProvider) {}

  execute(): Promise<GoogleUser | null> {
    return this.authProvider.getCurrentUser()
  }
}
