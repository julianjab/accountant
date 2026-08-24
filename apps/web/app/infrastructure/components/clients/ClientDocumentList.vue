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

/** Documents the exogena implies exist and the client has not provided.
 *
 * Listed greyed out beside the real ones, because a folder that merely looks
 * short tells the preparer nothing: the actionable fact is which party still
 * owes a certificate. One row per reporting party, not per claim — a bank with
 * seven unmatched rows is still one document to ask for. */
const awaited = computed(() => {
  const byReporter = new Map<string, { reporterName: string, claims: number }>()
  for (const finding of props.report?.findings ?? []) {
    if (finding.status !== 'missing_evidence') continue
    const existing = byReporter.get(finding.reporterTaxId)
    if (existing) {
      existing.claims += 1
      continue
    }
    byReporter.set(finding.reporterTaxId, { reporterName: finding.reporterName, claims: 1 })
  }
  return [...byReporter.entries()].map(([taxId, value]) => ({ taxId, ...value }))
})

const hasRows = computed(() => props.documents.length > 0 || awaited.value.length > 0)
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
      class="flex items-center gap-3 px-4 py-2.5"
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
    </li>

    <li
      v-for="expected in awaited"
      :key="`awaited-${expected.taxId}`"
      class="flex items-center gap-3 px-4 py-2.5 opacity-60"
      data-testid="awaited-document"
    >
      <UIcon
        name="i-lucide-file-question"
        class="size-4 shrink-0 text-muted"
      />

      <div class="min-w-0 flex-1 sm:max-w-[320px]">
        <div class="truncate text-[13.5px] font-medium text-toned">
          {{ expected.reporterName }}
        </div>
        <div class="mt-0.5 truncate text-[12px] text-muted">
          {{ t('clients.detail.documents.awaitedClaims', { count: expected.claims }) }}
        </div>
      </div>

      <UBadge
        :label="t('clients.detail.documents.awaited')"
        color="neutral"
        variant="subtle"
        class="shrink-0"
      />
    </li>
  </ul>
</template>
