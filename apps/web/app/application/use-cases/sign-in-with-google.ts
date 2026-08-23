import type { GoogleAuthSession, GoogleAuthProvider } from '~/application/ports/google-auth-provider'

export class SignInWithGoogle {
  constructor(private readonly authProvider: GoogleAuthProvider) {}

  execute(): Promise<GoogleAuthSession> {
    return this.authProvider.signIn()
  }
}
