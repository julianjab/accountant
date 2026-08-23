import { describe, expect, it } from 'vitest'
import type { DocumentType } from '~/domain/entities/document-type'
import type { DefineDocumentTypeInput, DocumentTypeRepository } from '~/application/ports/document-type-repository'
import { ListDocumentTypes } from '~/application/use-cases/list-document-types'

class FakeDocumentTypeRepository implements DocumentTypeRepository {
  constructor(private readonly documentTypes: DocumentType[]) {}

  list(): Promise<DocumentType[]> {
    return Promise.resolve(this.documentTypes)
  }

  define(_input: DefineDocumentTypeInput): Promise<DocumentType> {
    throw new Error('not implemented')
  }
}

describe('ListDocumentTypes', () => {
  it('returns the document types from the repository', async () => {
    const documentTypes: DocumentType[] = [
      {
        id: '1',
        name: 'Bancolombia statement',
        description: 'Monthly bank statement',
        extractionPrompt: 'Extract the statement fields',
        extractionSchema: { properties: { balance: { type: 'number' } } },
        active: true,
        createdAt: '2026-01-01'
      }
    ]
    const useCase = new ListDocumentTypes(new FakeDocumentTypeRepository(documentTypes))

    await expect(useCase.execute()).resolves.toEqual(documentTypes)
  })
})
