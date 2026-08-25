import { describe, expect, it } from 'vitest'
import { isRepeatedPath, listSchemaFields, pruneSchema } from '~/domain/extraction-schema'

const SCHEMA: Record<string, unknown> = {
  type: 'object',
  required: ['tax_id', 'accounts'],
  properties: {
    tax_id: { type: 'string', description: 'NIT of the bank' },
    period: { type: 'string' },
    accounts: {
      type: 'array',
      items: {
        type: 'object',
        required: ['number'],
        properties: {
          number: { type: 'string' },
          balance: { type: 'string' },
          holder: {
            type: 'object',
            properties: { name: { type: 'string' } }
          }
        }
      }
    }
  }
}

describe('listSchemaFields', () => {
  it('names a field inside a list the way the server resolves it', () => {
    const paths = listSchemaFields(SCHEMA).map(field => field.path)

    expect(paths).toEqual([
      'tax_id',
      'period',
      'accounts[].number',
      'accounts[].balance',
      'accounts[].holder.name'
    ])
  })

  it('reports each field type, description and whether the schema requires it', () => {
    const [taxId, period] = listSchemaFields(SCHEMA)

    expect(taxId).toEqual({
      path: 'tax_id',
      name: 'tax_id',
      type: 'string',
      description: 'NIT of the bank',
      required: true
    })
    expect(period!.required).toBe(false)
  })

  it('returns nothing for a schema that declares no properties', () => {
    expect(listSchemaFields({ type: 'object' })).toEqual([])
  })
})

describe('pruneSchema', () => {
  it('keeps only the fields the user checked', () => {
    const pruned = pruneSchema(SCHEMA, new Set(['tax_id', 'accounts[].balance']))

    expect(pruned).toEqual({
      type: 'object',
      required: ['tax_id', 'accounts'],
      properties: {
        tax_id: { type: 'string', description: 'NIT of the bank' },
        accounts: {
          type: 'array',
          items: {
            type: 'object',
            required: [],
            properties: { balance: { type: 'string' } }
          }
        }
      }
    })
  })

  it('drops a container whose every field was dropped', () => {
    const pruned = pruneSchema(SCHEMA, new Set(['tax_id']))

    expect(Object.keys(pruned.properties as Record<string, unknown>)).toEqual(['tax_id'])
  })

  it('stops requiring a field it just removed', () => {
    const pruned = pruneSchema(SCHEMA, new Set(['period']))

    expect(pruned.required).toEqual([])
  })
})

describe('isRepeatedPath', () => {
  it('knows a column of a table from a single figure', () => {
    // `obligaciones_a_cargo[].capital` is not one value: the certificate
    // prints one per row, and a screen showing a lone figure under it reads as
    // an extraction that found a single row.
    expect(isRepeatedPath('obligaciones_a_cargo[].capital')).toBe(true)
    expect(isRepeatedPath('componente_inflacionario.porcentaje')).toBe(false)
  })
})
