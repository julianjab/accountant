import { describe, expect, it } from 'vitest'
import { distinctRowWordings, foldLabel, listPrefixOf } from './table-rows'

const CERT_220 = {
  ingresos: [
    { concepto: 'Pagos por salarios', valor: 80000000 },
    { concepto: 'Pagos por prestaciones sociales', valor: 7000000 },
    { concepto: 'Auxilio de cesantía consignado al fondo', valor: 6500000 }
  ]
}

describe('distinctRowWordings', () => {
  it('reads what every row of the table actually said, in the order printed', () => {
    expect(distinctRowWordings(CERT_220, 'ingresos[].concepto')).toEqual([
      'Pagos por salarios',
      'Pagos por prestaciones sociales',
      'Auxilio de cesantía consignado al fondo'
    ])
  })

  it('asks once for two rows a reader would call the same row', () => {
    const fields = {
      ingresos: [{ concepto: 'Pagos por salarios' }, { concepto: 'PAGOS  POR SALARIOS ' }]
    }

    expect(distinctRowWordings(fields, 'ingresos[].concepto')).toEqual(['Pagos por salarios'])
  })

  it('skips rows that name nothing, which are not a question anyone can answer', () => {
    const fields = { ingresos: [{ concepto: '   ' }, { valor: 1 }, { concepto: 'Salarios' }] }

    expect(distinctRowWordings(fields, 'ingresos[].concepto')).toEqual(['Salarios'])
  })

  it('reads a document that never printed the table as no rows at all', () => {
    expect(distinctRowWordings({}, 'ingresos[].concepto')).toEqual([])
    expect(distinctRowWordings({ ingresos: 'nada' }, 'ingresos[].concepto')).toEqual([])
  })
})

describe('foldLabel', () => {
  it('matches the same wording past accents, casing and spacing', () => {
    expect(foldLabel('Auxilio de  CESANTÍA ')).toBe('auxilio de cesantia')
  })
})

describe('listPrefixOf', () => {
  it('reads the innermost block as the one whose rows are being told apart', () => {
    expect(listPrefixOf('a[].b[].c')).toBe('a[].b[]')
  })

  it('reads a field outside any list as belonging to no block', () => {
    expect(listPrefixOf('gmf')).toBeNull()
  })

  it('gives the fields of one block the same answer, which is what groups them', () => {
    expect(listPrefixOf('ingresos[].concepto')).toBe(listPrefixOf('ingresos[].valor'))
  })
})
