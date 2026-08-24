import { describe, expect, it } from 'vitest'
import type { DocumentType, DocumentTypeCreation, DocumentTypeUpdate, DocumentTypeField } from '~/domain/entities/document-type'
import type { DocumentTypeProposal } from '~/domain/entities/document-type-proposal'
import type {
  CreateDocumentTypeInput,
  DocumentTypeRepository,
  ProposeDocumentTypeInput,
  UpdateDocumentTypeInput
} from '~/application/ports/document-type-repository'
import { ProposeDocumentType } from '~/application/use-cases/propose-document-type'

const PROPOSAL: DocumentTypeProposal = {
  extractionPrompt: 'Extract it',
  extractionSchema: { type: 'object', properties: {} },
  fields: [
    { path: 'nit', label: 'NIT', role: 'identifier', sampleValue: '890903938', section: '' }
  ],
  fieldMappings: [],
  unmappedFields: [],
  kindId: 'exogena_dian',
  reporterPath: 'nit',
  reporterNamePath: null,
  periodPath: null
}

class FakeDocumentTypeRepository implements DocumentTypeRepository {
  receivedInput: ProposeDocumentTypeInput | null = null

  listActive(): Promise<DocumentType[]> {
    throw new Error('not implemented')
  }

  list(): Promise<DocumentType[]> {
    throw new Error('not implemented')
  }

  describeFields(): Promise<DocumentTypeField[]> {
    throw new Error('not implemented')
  }

  propose(input: ProposeDocumentTypeInput): Promise<DocumentTypeProposal> {
    this.receivedInput = input
    return Promise.resolve(PROPOSAL)
  }

  create(_input: CreateDocumentTypeInput): Promise<DocumentTypeCreation> {
    throw new Error('not implemented')
  }

  remove(_id: string): Promise<void> {
    return Promise.resolve()
  }

  update(_id: string, _changes: UpdateDocumentTypeInput): Promise<DocumentTypeUpdate> {
    throw new Error('not implemented')
  }
}

describe('ProposeDocumentType', () => {
  it('forwards the sample to the repository and returns the proposal', async () => {
    const repository = new FakeDocumentTypeRepository()
    const input: ProposeDocumentTypeInput = {
      name: 'Certificado GMF',
      sampleFile: new File(['sample'], 'sample.pdf', { type: 'application/pdf' })
    }

    await expect(new ProposeDocumentType(repository).execute(input)).resolves.toEqual(PROPOSAL)
    expect(repository.receivedInput).toEqual(input)
  })
})
