import type { ReconciliationReport } from '~/domain/entities/reconciliation'
import type { ReconciliationRepository } from '~/application/ports/reconciliation-repository'

export class RunReconciliation {
  constructor(private readonly reconciliations: ReconciliationRepository) {}

  execute(kindId: string, clientId: string, period: string): Promise<ReconciliationReport> {
    return this.reconciliations.run(kindId, clientId, period)
  }
}
