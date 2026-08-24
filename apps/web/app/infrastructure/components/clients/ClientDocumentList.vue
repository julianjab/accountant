<script setup lang="ts">
import type { ClientDocument, DocumentStatus } from '~/domain/entities/document'
import type { DocumentType } from '~/domain/entities/document-type'
import type { ReconciliationReport } from '~/domain/entities/reconciliation'

const props = defineProps<{
  documents: ClientDocument[]
  types: DocumentType[]
  /** Used to list what the exogena says should be here and is not. */
  report?: ReconciliationReport | null
}>()

const { t, locale } = useI18n()

const STATUS_COLOR: Record<DocumentStatus, 'warning' | 'info' | 'primary' | 'success' | 'error'> = {
  pending: 'warning',
  classifying: 'info',
  running_ocr: 'primary',
  processed: 'success',
  approved: 'success',
  failed: 'error'
}

function typeName(documentTypeId: string | null): string {
  const type = documentTypeId ? props.types.find(t => t.id === documentTypeId) : undefined
  return type?.name ?? t('clients.detail.documents.unclassified')
}

function formattedTime(createdAt: string): string {
  return new Intl.DateTimeFormat(locale.value, { hour: '2-digit', minute: '2-digit' }).format(
    new Date(createdAt)
  )
}

interface AwaitedValue {
  key: string
  detail: string
  amount: string
  account: string | null
}

/** Documents the exogena implies exist and the client has not provided.
 *
 * Grouped by reporting party, because that is the unit of the ask — a bank
 * with seven unmatched rows is still one person to write to. The rows behind
 * the count are what makes the ask specific, so the party expands into the
 * exact figures it has not certified. */
const awaited = computed(() => {
  const byReporter = new Map<
    string,
    { reporterName: string, values: AwaitedValue[] }
  >()
  for (const finding of props.report?.findings ?? []) {
    if (finding.status !== 'missing_evidence') continue
    const entry = byReporter.get(finding.reporterTaxId)
      ?? { reporterName: finding.reporterName, values: [] }
    for (const fact of finding.spineFacts) {
      entry.values.push({
        key: `${finding.id}-${fact.locator}`,
        detail: fact.detail || finding.label,
        amount: fact.amount,
        account: fact.account
      })
    }
    byReporter.set(finding.reporterTaxId, entry)
  }
  return [...byReporter.entries()].map(([taxId, value]) => ({ taxId, ...value }))
})

const expanded = ref<Record<string, boolean>>({})
function toggle(taxId: string) {
  expanded.value = { ...expanded.value, [taxId]: !expanded.value[taxId] }
}

const hasRows = computed(() => props.documents.length > 0 || awaited.value.length > 0)

/** Starts the define-a-type flow knowing both who issues the document and
 * which figure is being chased.
 *
 * Offered per value rather than per party: a bank certifies its GMF and its
 * investment balances on separate forms, so which type to define depends on
 * the figure, not on the sender. */
function defineTypeLink(reporterName: string, detail: string): string {
  const issuer = encodeURIComponent(reporterName)
  return `/document-types/new?issuer=${issuer}&claim=${encodeURIComponent(detail)}`
}
</script>

<template>
  <p
    v-if="!hasRows"
    class="p-4 text-[13px] text-toned"
  >
    {{ t('clients.detail.documents.empty') }}
  </p>

  <ul
    v-else
    class="divide-y divide-default"
  >
    <li
      v-for="doc in documents"
      :key="doc.id"
    >
      <NuxtLink
        :to="`/documents/${doc.id}`"
        class="flex items-center gap-3 px-4 py-2.5 transition-colors duration-[120ms] hover:bg-elevated/60"
      >
        <UIcon
          name="i-lucide-file-text"
          class="size-4 shrink-0 text-muted"
        />

        <!-- The 320px cap keeps the desktop list from stretching a long file name across the
             whole card; on a phone the row is already narrower than that. -->
        <div class="min-w-0 flex-1 sm:max-w-[320px]">
          <div class="truncate text-[13.5px] font-medium text-highlighted">
            {{ doc.fileName }}
          </div>
          <div class="mt-0.5 truncate text-[12px] text-muted">
            {{ typeName(doc.documentTypeId) }} · {{ formattedTime(doc.createdAt) }}
          </div>
        </div>

        <UBadge
          :label="t(`documents.status.${doc.status}`)"
          :color="STATUS_COLOR[doc.status]"
          variant="subtle"
          class="shrink-0"
        />
      </NuxtLink>
    </li>

    <li
      v-for="expected in awaited"
      :key="`awaited-${expected.taxId}`"
      data-testid="awaited-document"
    >
      <button
        type="button"
        class="flex w-full items-center gap-3 px-4 py-2.5 text-left opacity-70 transition-colors duration-[120ms] hover:bg-elevated/60 hover:opacity-100"
        :aria-expanded="Boolean(expanded[expected.taxId])"
        @click="toggle(expected.taxId)"
      >
        <UIcon
          :name="expanded[expected.taxId] ? 'i-lucide-chevron-down' : 'i-lucide-chevron-right'"
          class="size-4 shrink-0 text-muted"
        />

        <div class="min-w-0 flex-1 sm:max-w-[320px]">
          <div class="truncate text-[13.5px] font-medium text-toned">
            {{ expected.reporterName }}
          </div>
          <div class="mt-0.5 truncate text-[12px] text-muted">
            {{ t('clients.detail.documents.awaitedClaims', { count: expected.values.length }) }}
          </div>
        </div>

        <UBadge
          :label="t('clients.detail.documents.awaited')"
          color="neutral"
          variant="subtle"
          class="shrink-0"
        />
      </button>

      <!-- The figures the party has not certified. Naming them is what turns
           "a document is missing" into something the preparer can actually
           ask for. -->
      <ul
        v-if="expanded[expected.taxId]"
        class="border-t border-default bg-elevated/30"
      >
        <li
          v-for="value in expected.values"
          :key="value.key"
          class="flex items-center gap-3 py-1.5 pl-11 pr-4"
        >
          <div class="min-w-0 flex-1">
            <div class="truncate text-[12.5px] text-toned">
              {{ value.detail }}
            </div>
            <div
              v-if="value.account"
              class="truncate font-mono text-[11px] text-muted"
            >
              {{ value.account }}
            </div>
          </div>

          <span class="shrink-0 font-mono text-[12px] tabular-nums text-highlighted">
            {{ value.amount }}
          </span>

          <UButton
            :label="t('clients.detail.documents.defineType')"
            icon="i-lucide-plus"
            size="xs"
            variant="ghost"
            class="shrink-0"
            data-testid="define-type-for-value"
            :to="defineTypeLink(expected.reporterName, value.detail)"
          />
        </li>
      </ul>
    </li>
  </ul>
</template>
