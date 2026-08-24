import { HttpClientRepository } from '~/infrastructure/http/http-client-repository'
import { HttpDocumentRepository } from '~/infrastructure/http/http-document-repository'
import { HttpDocumentTypeRepository } from '~/infrastructure/http/http-document-type-repository'
import { HttpSpreadsheetRepository } from '~/infrastructure/http/http-spreadsheet-repository'
import { HttpReconciliationRepository } from '~/infrastructure/http/http-reconciliation-repository'
import { HttpConceptMappingRepository } from '~/infrastructure/http/http-concept-mapping-repository'
import { ServerSessionAuthProvider } from '~/infrastructure/auth/server-session-auth-provider'
import { GetClient } from '~/application/use-cases/get-client'
import { ListClients } from '~/application/use-cases/list-clients'
import { ListClientDocuments } from '~/application/use-cases/list-client-documents'
import { ListActiveDocumentTypes } from '~/application/use-cases/list-active-document-types'
import { ListClientSheetRows } from '~/application/use-cases/list-client-sheet-rows'
import { ListInbox } from '~/application/use-cases/list-inbox'
import { RegisterClient } from '~/application/use-cases/register-client'
import { GetDocument } from '~/application/use-cases/get-document'
import { GetDocumentExtractedData } from '~/application/use-cases/get-document-extracted-data'
import { ImportClientsFromDrive } from '~/application/use-cases/import-clients-from-drive'
import { GetCurrentUser } from '~/application/use-cases/get-current-user'
import { ListDocumentTypes } from '~/application/use-cases/list-document-types'
import { DefineDocumentType } from '~/application/use-cases/define-document-type'
import { GetDocumentType } from '~/application/use-cases/get-document-type'
import { UpdateDocumentType } from '~/application/use-cases/update-document-type'
import { ListReconciliationKinds } from '~/application/use-cases/list-reconciliation-kinds'
import { GetConceptMapping } from '~/application/use-cases/get-concept-mapping'
import { SaveConceptMapping } from '~/application/use-cases/save-concept-mapping'
import { GetReconciliationReport } from '~/application/use-cases/get-reconciliation-report'
import { RunReconciliation } from '~/application/use-cases/run-reconciliation'
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

export function useSpreadsheetRepository() {
  const config = useRuntimeConfig()
  return new HttpSpreadsheetRepository(config.public.serverApiBase)
}

export function useReconciliationRepository() {
  const config = useRuntimeConfig()
  return new HttpReconciliationRepository(config.public.serverApiBase)
}

export function useConceptMappingRepository() {
  const config = useRuntimeConfig()
  return new HttpConceptMappingRepository(config.public.serverApiBase)
}

export function useGetReconciliationReportUseCase() {
  return new GetReconciliationReport(useReconciliationRepository())
}

export function useRunReconciliationUseCase() {
  return new RunReconciliation(useReconciliationRepository())
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

export function useListDocumentTypesUseCase() {
  return new ListDocumentTypes(useDocumentTypeRepository())
}

export function useDefineDocumentTypeUseCase() {
  return new DefineDocumentType(useDocumentTypeRepository())
}

export function useGetDocumentTypeUseCase() {
  return new GetDocumentType(useDocumentTypeRepository())
}

export function useUpdateDocumentTypeUseCase() {
  return new UpdateDocumentType(useDocumentTypeRepository())
}

export function useListReconciliationKindsUseCase() {
  return new ListReconciliationKinds(useConceptMappingRepository())
}

export function useGetConceptMappingUseCase() {
  return new GetConceptMapping(useConceptMappingRepository())
}

export function useSaveConceptMappingUseCase() {
  return new SaveConceptMapping(useConceptMappingRepository())
}

export function useListClientSheetRowsUseCase() {
  return new ListClientSheetRows(useSpreadsheetRepository())
}

export function useListInboxUseCase() {
  return new ListInbox(useDocumentRepository(), useClientRepository(), useDocumentTypeRepository())
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
