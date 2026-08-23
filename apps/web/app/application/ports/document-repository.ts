import type { ClientDocument } from '~/domain/entities/document'

export interface DocumentRepository {
  listByClient: (clientId: string) => Promise<ClientDocument[]>
}
