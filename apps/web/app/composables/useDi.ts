import { HttpClientRepository } from '~/infrastructure/http/http-client-repository'
import { HttpDocumentRepository } from '~/infrastructure/http/http-document-repository'
import { DriveApiRepository } from '~/infrastructure/http/drive-api-repository'
import { GisGoogleAuthProvider } from '~/infrastructure/auth/gis-google-auth-provider'
import { ListClients } from '~/application/use-cases/list-clients'
import { RegisterClient } from '~/application/use-cases/register-client'
import { GetDocument } from '~/application/use-cases/get-document'
import { GetDocumentExtractedData } from '~/application/use-cases/get-document-extracted-data'
import { SignInWithGoogle } from '~/application/use-cases/sign-in-with-google'
import { SignOut } from '~/application/use-cases/sign-out'
import type { GoogleAuthProvider } from '~/application/ports/google-auth-provider'
import type { DriveRepository } from '~/application/ports/drive-repository'
import type { DocumentRepository } from '~/application/ports/document-repository'

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

export function useDocumentRepository(): DocumentRepository {
  const config = useRuntimeConfig()
  return new HttpDocumentRepository(config.public.serverApiBase)
}

export function useGetDocumentUseCase() {
  return new GetDocument(useDocumentRepository())
}

export function useGetDocumentExtractedDataUseCase() {
  return new GetDocumentExtractedData(useDocumentRepository())
}

let googleAuthProvider: GoogleAuthProvider | null = null

export function useGoogleAuthProvider(): GoogleAuthProvider {
  if (!import.meta.client) {
    throw new Error('GoogleAuthProvider is only available on the client')
  }

  if (!googleAuthProvider) {
    const config = useRuntimeConfig()
    googleAuthProvider = new GisGoogleAuthProvider(config.public.googleClientId)
  }
  return googleAuthProvider
}

export function useDriveRepository(): DriveRepository {
  return new DriveApiRepository()
}

export function useSignInWithGoogleUseCase() {
  return new SignInWithGoogle(useGoogleAuthProvider())
}

export function useSignOutUseCase() {
  return new SignOut(useGoogleAuthProvider())
}
