import { describe, expect, it } from 'vitest'
import type { DocumentType } from '~/domain/entities/document-type'
import type { DocumentTypeRepository } from '~/application/ports/document-type-repository'
import { ListActiveDocumentTypes } from '~/application/use-cases/list-active-document-types'

class FakeDocumentTypeRepository implements DocumentTypeRepository {
  constructor(private readonly documentTypes: DocumentType[]) {}

  listActive(): Promise<DocumentType[]> {
    return Promise.resolve(this.documentTypes)
  }
}

describe('ListActiveDocumentTypes', () => {
  it('returns the active document types from the repository', async () => {
    const documentTypes: DocumentType[] = [{ id: '1', name: 'Bancolombia statement', active: true }]
    const useCase = new ListActiveDocumentTypes(new FakeDocumentTypeRepository(documentTypes))

    await expect(useCase.execute()).resolves.toEqual(documentTypes)
  })
})
