import type { GoogleUser } from '~/domain/entities/google-user'

export function useGoogleAuth() {
  const user = useState<GoogleUser | null>('google-auth-user', () => null)
  const accessToken = useState<string | null>('google-auth-token', () => null)

  const isAuthenticated = computed(() => user.value !== null)

  async function signIn(): Promise<void> {
    if (!import.meta.client) return

    const session = await useSignInWithGoogleUseCase().execute()
    user.value = session.user
    accessToken.value = session.accessToken
  }

  function signOut(): void {
    if (!import.meta.client) return

    useSignOutUseCase().execute()
    user.value = null
    accessToken.value = null
  }

  async function getAccessToken(): Promise<string> {
    if (!import.meta.client) {
      throw new Error('getAccessToken can only be called on the client')
    }

    const provider = useGoogleAuthProvider()
    const token = await provider.getAccessToken()
    accessToken.value = token
    return token
  }

  return {
    user,
    accessToken,
    isAuthenticated,
    signIn,
    signOut,
    getAccessToken
  }
}
