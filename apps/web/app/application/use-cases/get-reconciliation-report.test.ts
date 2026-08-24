import { describe, expect, it } from 'vitest'
import type { ReconciliationReport } from '~/domain/entities/reconciliation'
import type { ReconciliationRepository } from '~/application/ports/reconciliation-repository'
import { GetReconciliationReport } from '~/application/use-cases/get-reconciliation-report'
import { RunReconciliation } from '~/application/use-cases/run-reconciliation'

const REPORT: ReconciliationReport = {
  id: 'c1__exogena_dian__2025',
  clientId: 'c1',
  kindId: 'exogena_dian',
  period: '2025',
  generatedAt: '2026-08-24T00:40:10Z',
  summary: { counts: { matched: 1 }, totalFindings: 1, reconciled: 1, needingAttention: 0 },
  findings: []
}

class FakeReconciliationRepository implements ReconciliationRepository {
  readonly calls: string[] = []

  constructor(private readonly report: ReconciliationReport | null) {}

  getReport(kindId: string, clientId: string, period: string) {
    this.calls.push(`get:${kindId}:${clientId}:${period}`)
    return Promise.resolve(this.report)
  }

  run(kindId: string, clientId: string, period: string) {
    this.calls.push(`run:${kindId}:${clientId}:${period}`)
    return Promise.resolve(REPORT)
  }
}

describe('GetReconciliationReport', () => {
  it('returns the stored report for a client and period', async () => {
    const repository = new FakeReconciliationRepository(REPORT)

    const report = await new GetReconciliationReport(repository).execute(
      'exogena_dian',
      'c1',
      '2025'
    )

    expect(report).toEqual(REPORT)
    expect(repository.calls).toEqual(['get:exogena_dian:c1:2025'])
  })

  it('returns null when nothing has been reconciled yet', async () => {
    // The screen shows this as an invitation to run one, not as an error.
    const report = await new GetReconciliationReport(
      new FakeReconciliationRepository(null)
    ).execute('exogena_dian', 'c1', '2025')

    expect(report).toBeNull()
  })
})

describe('RunReconciliation', () => {
  it('asks for a rebuild and returns the fresh report', async () => {
    const repository = new FakeReconciliationRepository(null)

    const report = await new RunReconciliation(repository).execute('exogena_dian', 'c1', '2025')

    expect(report).toEqual(REPORT)
    expect(repository.calls).toEqual(['run:exogena_dian:c1:2025'])
  })
})
