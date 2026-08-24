<script setup lang="ts">
import type {
  FindingStatus,
  ReconciliationFinding,
  ReconciliationReport
} from '~/domain/entities/reconciliation'
import { FINDING_ORDER } from '~/domain/entities/reconciliation'

const props = defineProps<{ clientId: string }>()

const { t } = useI18n()
const getReport = useGetReconciliationReportUseCase()
const runReconciliation = useRunReconciliationUseCase()

// One reconciliation model and one tax year for now, so neither is a choice
// the screen has to offer.
const KIND_ID = 'exogena_dian'
const PERIOD = '2025'

const running = ref(false)
const error = ref<string | null>(null)

const { data: report, refresh } = await useAsyncData<ReconciliationReport | null>(
  `reconciliation:${props.clientId}`,
  () => getReport.execute(KIND_ID, props.clientId, PERIOD),
  { server: false, default: () => null }
)

async function run() {
  running.value = true
  error.value = null
  try {
    report.value = await runReconciliation.execute(KIND_ID, props.clientId, PERIOD)
  } catch {
    error.value = t('reconciliation.runFailed')
    await refresh()
  } finally {
    running.value = false
  }
}

const STATUS_STYLE: Record<FindingStatus, string> = {
  mismatch: 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300',
  missing_evidence: 'bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-300',
  unsupported_by_spine: 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
  matched_within_tolerance: 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300',
  matched: 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300',
  out_of_scope: 'bg-elevated text-muted'
}

/** Grouped by outcome and kept in the engine's order: what needs acting on
 * first, what already reconciles below it, and what was never validated last. */
const groups = computed(() => {
  const findings = report.value?.findings ?? []
  return FINDING_ORDER
    .map(status => ({
      status,
      findings: findings.filter((f: ReconciliationFinding) => f.status === status)
    }))
    .filter(group => group.findings.length > 0)
})

const expanded = ref<Record<string, boolean>>({})
function toggle(id: string) {
  expanded.value = { ...expanded.value, [id]: !expanded.value[id] }
}

/** A delta of zero is not worth the ink; anything else is the whole point. */
function isMeaningful(delta: string): boolean {
  return Number.parseFloat(delta) !== 0
}
</script>

<template>
  <div class="p-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h3 class="text-[13px] font-semibold text-highlighted">
          {{ t('reconciliation.title', { period: PERIOD }) }}
        </h3>
        <p
          v-if="report"
          class="text-[12px] text-muted"
        >
          {{ t('reconciliation.summary', {
            total: report.summary.totalFindings,
            reconciled: report.summary.reconciled,
            attention: report.summary.needingAttention
          }) }}
        </p>
      </div>
      <UButton
        :label="report ? t('reconciliation.rerun') : t('reconciliation.run')"
        icon="i-lucide-scale"
        size="sm"
        variant="outline"
        :loading="running"
        data-testid="reconciliation-run"
        @click="run"
      />
    </div>

    <p
      v-if="error"
      class="mt-3 text-[13px] text-red-600"
      data-testid="reconciliation-error"
    >
      {{ error }}
    </p>

    <p
      v-if="!report"
      class="mt-4 text-[13px] text-toned"
      data-testid="reconciliation-empty"
    >
      {{ t('reconciliation.notRunYet') }}
    </p>

    <div
      v-else
      class="mt-4 flex flex-col gap-5"
    >
      <section
        v-for="group in groups"
        :key="group.status"
      >
        <h4 class="mb-2 flex items-center gap-2 text-[12px] font-semibold text-highlighted">
          <span
            class="rounded px-1.5 py-0.5 text-[11px] font-medium"
            :class="STATUS_STYLE[group.status]"
          >{{ t(`reconciliation.status.${group.status}`) }}</span>
          <span class="text-muted">{{ group.findings.length }}</span>
        </h4>

        <ul class="flex flex-col divide-y divide-default rounded border border-default">
          <li
            v-for="finding in group.findings"
            :key="finding.id"
          >
            <button
              type="button"
              class="flex w-full flex-col gap-1 px-3 py-2 text-left hover:bg-elevated/60"
              @click="toggle(finding.id)"
            >
              <div class="flex items-baseline justify-between gap-3">
                <span class="text-[13px] text-highlighted">{{ finding.label }}</span>
                <span
                  v-if="isMeaningful(finding.delta)"
                  class="shrink-0 font-mono text-[12px] tabular-nums text-toned"
                >Δ {{ finding.delta }}</span>
              </div>
              <div class="flex flex-wrap items-baseline gap-x-3 text-[11px] text-muted">
                <span>{{ finding.reporterName }}</span>
                <span v-if="finding.account">· {{ finding.account }}</span>
              </div>
            </button>

            <!-- The two sides side by side: what the exogena claims against
                 what the certificate evidences, with the facts behind each so
                 a figure can be traced back to the document it came from. -->
            <div
              v-if="expanded[finding.id]"
              class="grid grid-cols-1 gap-3 border-t border-default bg-elevated/40 px-3 py-2 sm:grid-cols-2"
            >
              <div>
                <p class="mb-1 text-[11px] font-semibold uppercase text-muted">
                  {{ t('reconciliation.spine') }}
                  <span class="ml-1 font-mono tabular-nums">{{ finding.spineAmount }}</span>
                </p>
                <p
                  v-for="fact in finding.spineFacts"
                  :key="`${fact.sourceId}-${fact.locator}-${fact.conceptId}`"
                  class="text-[11px] text-toned"
                >
                  <span class="font-mono tabular-nums">{{ fact.amount }}</span>
                  · {{ fact.detail || fact.conceptId }}
                  <span class="text-muted">({{ fact.locator }})</span>
                </p>
              </div>
              <div>
                <p class="mb-1 text-[11px] font-semibold uppercase text-muted">
                  {{ t('reconciliation.evidence') }}
                  <span class="ml-1 font-mono tabular-nums">{{ finding.evidenceAmount }}</span>
                </p>
                <p
                  v-for="fact in finding.evidenceFacts"
                  :key="`${fact.sourceId}-${fact.locator}-${fact.conceptId}`"
                  class="text-[11px] text-toned"
                >
                  <span class="font-mono tabular-nums">{{ fact.amount }}</span>
                  · {{ fact.detail || fact.conceptId }}
                </p>
                <p
                  v-if="finding.evidenceFacts.length === 0"
                  class="text-[11px] text-toned"
                >
                  {{ t('reconciliation.noEvidence') }}
                </p>
              </div>
              <p
                v-if="finding.note"
                class="text-[11px] text-muted sm:col-span-2"
              >
                {{ finding.note }}
              </p>
            </div>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
