import { describe, expect, it } from 'vitest'
import type { DocumentType, DocumentTypeUpdate } from '~/domain/entities/document-type'
import type { DocumentTypeProposal } from '~/domain/entities/document-type-proposal'
import type {
  CreateDocumentTypeInput,
  ProposeDocumentTypeInput,
  DocumentTypeRepository,
  UpdateDocumentTypeInput
} from '~/application/ports/document-type-repository'
import { ListDocumentTypes } from '~/application/use-cases/list-document-types'

class FakeDocumentTypeRepository implements DocumentTypeRepository {
  constructor(private readonly documentTypes: DocumentType[]) {}

  listActive(): Promise<DocumentType[]> {
    throw new Error('not implemented')
  }

  list(): Promise<DocumentType[]> {
    return Promise.resolve(this.documentTypes)
  }

  propose(_input: ProposeDocumentTypeInput): Promise<DocumentTypeProposal> {
    throw new Error('not implemented')
  }

  create(_input: CreateDocumentTypeInput): Promise<DocumentTypeUpdate> {
    throw new Error('not implemented')
  }

  update(_id: string, _changes: UpdateDocumentTypeInput): Promise<DocumentTypeUpdate> {
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
        fields: [],
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
