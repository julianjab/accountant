import type { GoogleAuthProvider } from '~/application/ports/google-auth-provider'

export class SignInWithGoogle {
  constructor(private readonly authProvider: GoogleAuthProvider) {}

  execute(): void {
    this.authProvider.startSignIn()
  }
}
