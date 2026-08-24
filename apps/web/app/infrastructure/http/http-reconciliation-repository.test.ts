import { afterEach, describe, expect, it, vi } from 'vitest'
import { HttpReconciliationRepository } from '~/infrastructure/http/http-reconciliation-repository'

const REPORT_DTO = {
  id: 'c1__exogena_dian__2025',
  client_id: 'c1',
  kind_id: 'exogena_dian',
  period: '2025',
  generated_at: '2026-08-24T00:40:10Z',
  summary: {
    counts: { matched_within_tolerance: 1 },
    total_findings: 1,
    reconciled: 1,
    needing_attention: 0
  },
  findings: [
    {
      id: 'exogena.saldo_cuentas_bancarias|890903938|-',
      status: 'matched_within_tolerance',
      rule_id: 'exogena.saldo_cuentas_bancarias',
      label: 'Saldo de cuentas bancarias',
      reporter_tax_id: '890903938',
      reporter_name: 'BANCOLOMBIA S.A.',
      spine_amount: '2241275.00',
      evidence_amount: '2241275.17',
      delta: '-0.17',
      account: null,
      account_match: 'none',
      note: '',
      spine_facts: [
        {
          source_id: 'doc-exo',
          role: 'spine',
          reporter_tax_id: '890903938',
          reporter_name: 'BANCOLOMBIA S.A.',
          concept_id: 'dian:saldo-cuentas-bancarias',
          amount: '2135378.00',
          account: '87041292758',
          detail: 'Saldo cuentas bancarias',
          locator: 'row 38'
        }
      ],
      evidence_facts: []
    }
  ]
}

afterEach(() => {
  vi.unstubAllGlobals()
})

function stubFetch(handler: (path: string, options?: Record<string, unknown>) => unknown) {
  const fetcher = vi.fn(handler)
  vi.stubGlobal('$fetch', fetcher)
  return fetcher
}

describe('HttpReconciliationRepository', () => {
  it('maps a report into the shape the app reads', async () => {
    stubFetch(() => REPORT_DTO)

    const report = await new HttpReconciliationRepository('http://api').getReport(
      'exogena_dian',
      'c1',
      '2025'
    )

    expect(report?.summary.reconciled).toBe(1)
    const [finding] = report!.findings
    expect(finding!.reporterName).toBe('BANCOLOMBIA S.A.')
    // Amounts stay strings: they are exact decimals, and parsing them would
    // risk showing a discrepancy the engine never found.
    expect(finding!.delta).toBe('-0.17')
    expect(finding!.spineFacts[0]!.locator).toBe('row 38')
  })

  it('sends the session cookie', async () => {
    const fetcher = stubFetch(() => REPORT_DTO)

    await new HttpReconciliationRepository('http://api').getReport('exogena_dian', 'c1', '2025')

    expect(fetcher).toHaveBeenCalledWith(
      '/reconciliation/kinds/exogena_dian/clients/c1/periods/2025',
      expect.objectContaining({ credentials: 'include' })
    )
  })

  it('reads a never-reconciled period as null rather than failing', async () => {
    stubFetch(() => {
      throw Object.assign(new Error('not found'), { statusCode: 404 })
    })

    const report = await new HttpReconciliationRepository('http://api').getReport(
      'exogena_dian',
      'c1',
      '2025'
    )

    expect(report).toBeNull()
  })

  it('lets any other failure surface', async () => {
    stubFetch(() => {
      throw Object.assign(new Error('boom'), { statusCode: 500 })
    })

    await expect(
      new HttpReconciliationRepository('http://api').getReport('exogena_dian', 'c1', '2025')
    ).rejects.toThrow('boom')
  })

  it('runs a reconciliation with POST', async () => {
    const fetcher = stubFetch(() => REPORT_DTO)

    await new HttpReconciliationRepository('http://api').run('exogena_dian', 'c1', '2025')

    expect(fetcher).toHaveBeenCalledWith(
      '/reconciliation/kinds/exogena_dian/clients/c1/periods/2025',
      expect.objectContaining({ method: 'POST', credentials: 'include' })
    )
  })
})
