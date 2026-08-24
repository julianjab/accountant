import { describe, expect, it } from 'vitest'
import type { DocumentType, DocumentTypeCreation, DocumentTypeUpdate } from '~/domain/entities/document-type'
import type { DocumentTypeProposal } from '~/domain/entities/document-type-proposal'
import type {
  CreateDocumentTypeInput,
  ProposeDocumentTypeInput,
  DocumentTypeRepository,
  UpdateDocumentTypeInput
} from '~/application/ports/document-type-repository'
import { UpdateDocumentType } from '~/application/use-cases/update-document-type'

const DOCUMENT_TYPE: DocumentType = {
  id: '1',
  name: 'Bancolombia certificate',
  description: 'Yearly bank certificate',
  fields: [],
  taxYears: [],
  sampleDocumentId: null,
  extractionPrompt: 'Extract the certificate fields',
  extractionSchema: { properties: { balance: { type: 'string' } } },
  active: true,
  createdAt: '2026-01-01'
}

class FakeDocumentTypeRepository implements DocumentTypeRepository {
  receivedId: string | null = null
  receivedChanges: UpdateDocumentTypeInput | null = null

  listActive(): Promise<DocumentType[]> {
    throw new Error('not implemented')
  }

  list(): Promise<DocumentType[]> {
    throw new Error('not implemented')
  }

  propose(_input: ProposeDocumentTypeInput): Promise<DocumentTypeProposal> {
    throw new Error('not implemented')
  }

  create(_input: CreateDocumentTypeInput): Promise<DocumentTypeCreation> {
    throw new Error('not implemented')
  }

  remove(_id: string): Promise<void> {
    return Promise.resolve()
  }

  update(id: string, changes: UpdateDocumentTypeInput): Promise<DocumentTypeUpdate> {
    this.receivedId = id
    this.receivedChanges = changes
    return Promise.resolve({
      documentType: { ...DOCUMENT_TYPE, ...changes },
      mappingChanges: [
        {
          kindId: 'exogena_dian',
          change: 'entry_dropped',
          path: 'gmf',
          fieldPath: 'gmf',
          conceptId: 'bank:cert_gmf_valor',
          reason: 'the schema no longer declares this field'
        }
      ]
    })
  }
}

describe('UpdateDocumentType', () => {
  it('forwards only the changed fields and returns the updated document type', async () => {
    const repository = new FakeDocumentTypeRepository()
    const useCase = new UpdateDocumentType(repository)

    const { documentType } = await useCase.execute('1', { extractionSchema: { properties: {} } })

    expect(repository.receivedId).toBe('1')
    expect(repository.receivedChanges).toEqual({ extractionSchema: { properties: {} } })
    expect(documentType.extractionSchema).toEqual({ properties: {} })
  })

  it('reports the mapping the server had to drop to follow the schema edit', async () => {
    const useCase = new UpdateDocumentType(new FakeDocumentTypeRepository())

    const { mappingChanges } = await useCase.execute('1', { extractionSchema: { properties: {} } })

    expect(mappingChanges[0]!.change).toBe('entry_dropped')
    expect(mappingChanges[0]!.fieldPath).toBe('gmf')
  })
})
