import { describe, expect, it } from 'vitest'
import type { DocumentType, DocumentTypeUpdate } from '~/domain/entities/document-type'
import type { DocumentTypeProposal } from '~/domain/entities/document-type-proposal'
import type {
  CreateDocumentTypeInput,
  ProposeDocumentTypeInput,
  DocumentTypeRepository,
  UpdateDocumentTypeInput
} from '~/application/ports/document-type-repository'
import { GetDocumentType } from '~/application/use-cases/get-document-type'

const DOCUMENT_TYPE: DocumentType = {
  id: '1',
  name: 'Bancolombia certificate',
  description: 'Yearly bank certificate',
  fields: [],
  extractionPrompt: 'Extract the certificate fields',
  extractionSchema: { properties: { balance: { type: 'string' } } },
  active: true,
  createdAt: '2026-01-01'
}

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

describe('GetDocumentType', () => {
  it('returns the document type with the given id', async () => {
    const useCase = new GetDocumentType(new FakeDocumentTypeRepository([DOCUMENT_TYPE]))

    await expect(useCase.execute('1')).resolves.toEqual(DOCUMENT_TYPE)
  })

  it('returns null when no document type has that id', async () => {
    const useCase = new GetDocumentType(new FakeDocumentTypeRepository([DOCUMENT_TYPE]))

    await expect(useCase.execute('missing')).resolves.toBeNull()
  })
})
