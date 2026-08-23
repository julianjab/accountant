import { describe, expect, it } from 'vitest'
import type { DocumentType } from '~/domain/entities/document-type'
import type { DefineDocumentTypeInput, DocumentTypeRepository } from '~/application/ports/document-type-repository'
import { ListActiveDocumentTypes } from '~/application/use-cases/list-active-document-types'

class FakeDocumentTypeRepository implements DocumentTypeRepository {
  constructor(private readonly documentTypes: DocumentType[]) {}

  listActive(): Promise<DocumentType[]> {
    return Promise.resolve(this.documentTypes)
  }

  list(): Promise<DocumentType[]> {
    return Promise.resolve(this.documentTypes)
  }

  define(_input: DefineDocumentTypeInput): Promise<DocumentType> {
    throw new Error('not implemented')
  }
}

describe('ListActiveDocumentTypes', () => {
  it('returns the active document types from the repository', async () => {
    const documentTypes: DocumentType[] = [
      {
        id: '1',
        name: 'Bancolombia statement',
        description: 'Monthly bank statement',
        extractionPrompt: 'Extract the fields',
        extractionSchema: {},
        active: true,
        createdAt: '2026-01-01T00:00:00Z'
      }
    ]
    const useCase = new ListActiveDocumentTypes(new FakeDocumentTypeRepository(documentTypes))

    await expect(useCase.execute()).resolves.toEqual(documentTypes)
  })
})
