import { HttpClientRepository } from '~/infrastructure/http/http-client-repository'
import { HttpDocumentRepository } from '~/infrastructure/http/http-document-repository'
import { HttpDocumentTypeRepository } from '~/infrastructure/http/http-document-type-repository'
import { ServerSessionAuthProvider } from '~/infrastructure/auth/server-session-auth-provider'
import { GetClient } from '~/application/use-cases/get-client'
import { ListClients } from '~/application/use-cases/list-clients'
import { ListClientDocuments } from '~/application/use-cases/list-client-documents'
import { ListActiveDocumentTypes } from '~/application/use-cases/list-active-document-types'
import { RegisterClient } from '~/application/use-cases/register-client'
import { GetDocument } from '~/application/use-cases/get-document'
import { GetDocumentExtractedData } from '~/application/use-cases/get-document-extracted-data'
import { ImportClientsFromDrive } from '~/application/use-cases/import-clients-from-drive'
import { GetCurrentUser } from '~/application/use-cases/get-current-user'
import { SignInWithGoogle } from '~/application/use-cases/sign-in-with-google'
import { SignOut } from '~/application/use-cases/sign-out'
import type { GoogleAuthProvider } from '~/application/ports/google-auth-provider'

export function useClientRepository() {
  const config = useRuntimeConfig()
  return new HttpClientRepository(config.public.serverApiBase)
}

export function useDocumentRepository() {
  const config = useRuntimeConfig()
  return new HttpDocumentRepository(config.public.serverApiBase)
}

export function useDocumentTypeRepository() {
  const config = useRuntimeConfig()
  return new HttpDocumentTypeRepository(config.public.serverApiBase)
}

export function useListClientsUseCase() {
  return new ListClients(useClientRepository())
}

export function useGetClientUseCase() {
  return new GetClient(useClientRepository())
}

export function useListClientDocumentsUseCase() {
  return new ListClientDocuments(useDocumentRepository())
}

export function useListActiveDocumentTypesUseCase() {
  return new ListActiveDocumentTypes(useDocumentTypeRepository())
}

export function useRegisterClientUseCase() {
  return new RegisterClient(useClientRepository())
}

export function useGetDocumentUseCase() {
  return new GetDocument(useDocumentRepository())
}

export function useGetDocumentExtractedDataUseCase() {
  return new GetDocumentExtractedData(useDocumentRepository())
}

export function useImportClientsUseCase() {
  return new ImportClientsFromDrive(useClientRepository())
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
