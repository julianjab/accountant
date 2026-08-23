import type { GoogleAuthProvider } from '~/application/ports/google-auth-provider'

export class SignOut {
  constructor(private readonly authProvider: GoogleAuthProvider) {}

  execute(): Promise<void> {
    return this.authProvider.signOut()
  }
}
