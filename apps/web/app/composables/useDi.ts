import { HttpClientRepository } from '~/infrastructure/http/http-client-repository'
import { ListClients } from '~/application/use-cases/list-clients'
import { RegisterClient } from '~/application/use-cases/register-client'

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
