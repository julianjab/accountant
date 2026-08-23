import { HttpClientRepository } from '~/infrastructure/http/http-client-repository'
import { ServerSessionAuthProvider } from '~/infrastructure/auth/server-session-auth-provider'
import { ListClients } from '~/application/use-cases/list-clients'
import { RegisterClient } from '~/application/use-cases/register-client'
import { GetCurrentUser } from '~/application/use-cases/get-current-user'
import { SignInWithGoogle } from '~/application/use-cases/sign-in-with-google'
import { SignOut } from '~/application/use-cases/sign-out'
import type { GoogleAuthProvider } from '~/application/ports/google-auth-provider'

export function useClientRepository() {
  const config = useRuntimeConfig()
  return new HttpClientRepository(config.public.serverApiBase)
}

export function useListClientsUseCase() {
  return new ListClients(useClientRepository())
}

export function useRegisterClientUseCase() {
  return new RegisterClient(useClientRepository())
}

export function useGoogleAuthProvider(): GoogleAuthProvider {
  const config = useRuntimeConfig()
  return new ServerSessionAuthProvider(config.public.serverApiBase)
}

export function useGetCurrentUserUseCase() {
  return new GetCurrentUser(useGoogleAuthProvider())
}

export function useSignInWithGoogleUseCase() {
  return new SignInWithGoogle(useGoogleAuthProvider())
}

export function useSignOutUseCase() {
  return new SignOut(useGoogleAuthProvider())
}
