import type { GoogleUser } from '~/domain/entities/google-user'

export function useGoogleAuth() {
  const user = useState<GoogleUser | null>('google-auth-user', () => null)
  const isLoading = useState<boolean>('google-auth-loading', () => true)

  const isAuthenticated = computed(() => user.value !== null)

  /** Restores the session from the server cookie; this is what survives a reload. */
  async function loadSession(): Promise<void> {
    isLoading.value = true
    try {
      user.value = await useGetCurrentUserUseCase().execute()
    } catch {
      user.value = null
    } finally {
      isLoading.value = false
    }
  }

  function signIn(): void {
    useSignInWithGoogleUseCase().execute()
  }

  async function signOut(): Promise<void> {
    await useSignOutUseCase().execute()
    user.value = null
  }

  return {
    user,
    isLoading,
    isAuthenticated,
    loadSession,
    signIn,
    signOut
  }
}
