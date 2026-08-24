<script setup lang="ts">
import type { ClientDocument, DocumentStatus } from '~/domain/entities/document'
import { documentSourceLabelKey } from '~/domain/document-source'
import type { DocumentType } from '~/domain/entities/document-type'
import type { ExtractedData } from '~/domain/entities/extracted-data'
import type { ConceptMapping } from '~/domain/entities/concept-mapping'
import type { ReconciliationKind } from '~/domain/entities/reconciliation-kind'
import ExtractionFieldRow from '~/components/documents/ExtractionFieldRow.vue'
import MappedConceptList from '~/components/documents/MappedConceptList.vue'
import ProcessingTimeline from '~/components/documents/ProcessingTimeline.vue'
import { groupBySection, hasUsefulSections, labelFor } from '~/domain/field-sections'
import { mappedFieldGroups } from '~/domain/mapped-extraction'

const props = defineProps<{
  document: ClientDocument
  documentType: DocumentType | null
  extractedData: ExtractedData | null
  extractedDataError?: boolean
  approving?: boolean
  actionError?: string | null
  /** How this type's fields project onto the reconciliation, when it is
   * mapped. Null covers both "not mapped" and "not loaded", which render the
   * same: the transcription alone. */
  conceptMapping?: ConceptMapping | null
  /** The vocabulary the mapping's concept ids belong to, for their labels. */
  reconciliationKind?: ReconciliationKind | null
}>()

const emit = defineEmits<{ approve: [] }>()

const { t, te, locale } = useI18n()

// A non-technical accountant should never see `documentTypeId` (a raw uuid) as this card's
// title — the classified type's name is what tells them what they are looking at, falling
// back to the id only when the type could not be resolved (e.g. it was deleted since).
// A document read by a parser has no type to name it, so its source label is
// what tells the reader what they are looking at. Falling through to the raw
// uuid stays the last resort, for a type that was deleted since.
const sourceLabel = computed(() => {
  if (!props.document.sourceId) return null
  const key = documentSourceLabelKey(props.document.sourceId)
  return te(key) ? t(key) : props.document.sourceId
})

const title = computed(() =>
  props.documentType?.name
  ?? sourceLabel.value
  ?? props.document.sourceId
  ?? props.document.documentTypeId
  ?? t('documents.unknownType')
)

const formattedDate = computed(() => {
  const isoDate = props.document.processedAt ?? props.document.createdAt
  return new Intl.DateTimeFormat(locale.value, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(isoDate))
})

const STATUS_COLORS: Record<DocumentStatus, 'info' | 'success' | 'error'> = {
  pending: 'info',
  classifying: 'info',
  running_ocr: 'info',
  processed: 'success',
  approved: 'success',
  failed: 'error'
}

const STATUS_I18N_KEYS: Record<DocumentStatus, string> = {
  pending: 'documents.status.pending',
  classifying: 'documents.status.classifying',
  running_ocr: 'documents.status.runningOcr',
  processed: 'documents.status.processed',
  approved: 'documents.status.approved',
  failed: 'documents.status.failed'
}

// 'processed' and 'approved' both mean the OCR extraction is done — #11 wires up the actual
// approve action, but the server can already return a document that was approved before this
// screen existed (or by another client), so it must render like any other completed document.
const EXTRACTION_DONE_STATUSES: DocumentStatus[] = ['processed', 'approved']

// The backend's ExtractedDataResponse only carries a single document-level `confidence` —
// `fields` is a free-form dict shaped by the DocumentType's extraction_schema, with no
// per-field confidence. Until the server adds one (follow-up), a per-field confidence is
// read from `{ value, confidence }` shaped entries when present, falling back to the
// document-level confidence uniformly for every row and for the header average.
function isFieldWithConfidence(value: unknown): value is { value: unknown, confidence: number } {
  return (
    typeof value === 'object'
    && value !== null
    && 'value' in value
    && 'confidence' in value
    && typeof (value as { confidence: unknown }).confidence === 'number'
  )
}

interface FieldEntry {
  key: string
  value: unknown
  confidence: number | null
  /** The document's own name for this field, empty when its type has none. */
  label: string
}

const fieldEntries = computed<FieldEntry[]>(() => {
  if (!props.extractedData) {
    return []
  }
  const described = props.documentType?.fields ?? []
  return Object.entries(props.extractedData.fields).map(([key, raw]) => {
    // A top-level key is only described when it is a leaf; an extracted array
    // is described through its columns, so labelFor returns the key and the
    // row falls back to humanising it, which is right for a group heading.
    const label = labelFor(key, described) === key ? '' : labelFor(key, described)
    if (isFieldWithConfidence(raw)) {
      return { key, value: raw.value, confidence: raw.confidence, label }
    }
    return { key, value: raw, confidence: props.extractedData!.confidence, label }
  })
})

// The document is shown in its own blocks when its type records more than one.
// One section is a heading that separates nothing, and no sections at all is
// every type configured before they existed — both read better as a flat list.
const showSections = computed(() => hasUsefulSections(props.documentType?.fields ?? []))

const sections = computed(() =>
  groupBySection(fieldEntries.value, entry => entry.key, props.documentType?.fields ?? [])
)

// What this document contributes to the client's cross-check, ahead of the
// transcription. A type with no mapping yields nothing here and the card
// renders exactly as it did before.
const mapped = computed(() =>
  mappedFieldGroups(
    props.conceptMapping ?? null,
    props.extractedData?.fields ?? null,
    props.documentType?.fields ?? [],
    props.reconciliationKind ?? null
  )
)

const hasMappedConcepts = computed(() =>
  mapped.value.crossed.length > 0 || mapped.value.uncrossed.length > 0
)

const averageConfidence = computed<number | null>(() => {
  if (!props.extractedData) {
    return null
  }
  const perFieldConfidences = fieldEntries.value
    .map(entry => entry.confidence)
    .filter((confidence): confidence is number => confidence !== null)

  if (perFieldConfidences.length > 0) {
    return perFieldConfidences.reduce((sum, c) => sum + c, 0) / perFieldConfidences.length
  }
  return props.extractedData.confidence
})

// A document read by a parser is finished and has no `documentTypeId` by
// design, so the second clause has to look at `sourceId` too — without that,
// recognising the exogena would leave the screen still reporting a failure.
const hasExtractionError = computed(() =>
  props.document.status === 'failed'
  || (
    EXTRACTION_DONE_STATUSES.includes(props.document.status)
    && props.document.documentTypeId === null
    && props.document.sourceId === null
  )
)

const isApproved = computed(() => props.document.status === 'approved')

// Offered whatever state the document is in, because approving is what does
// the work: a document reaches this screen precisely when the pipeline could
// make nothing of it, so "not processed yet" is the normal case rather than a
// reason to withhold the button.
const canApprove = computed(() => !isApproved.value)

// Approving is synchronous: the request does the reading and comes back with
// the document already processed or already failed. So a *persisted*
// mid-pipeline status never means "work is happening" — it means a run died
// partway and nothing is going to finish it. `pending` cannot even be reached
// (the pipeline creates documents straight into `classifying`), which makes a
// document sitting in one of these the clearest case of all.
//
// Animating skeletons here was the bug: the screen promised progress for a
// document nothing was progressing, so it span forever with no way to tell
// that pressing the button was the way out.
const isStalled = computed(() =>
  (['pending', 'classifying', 'running_ocr'] as DocumentStatus[]).includes(props.document.status)
)

const hasExtractedDataLoadError = computed(() =>
  EXTRACTION_DONE_STATUSES.includes(props.document.status) && !hasExtractionError.value && props.extractedDataError
)

const isMissingExtraction = computed(() =>
  EXTRACTION_DONE_STATUSES.includes(props.document.status)
  && !hasExtractionError.value
  && !hasExtractedDataLoadError.value
  && !props.extractedData
)
</script>

<template>
  <UCard>
    <template #header>
      <div class="flex flex-col gap-3">
        <div class="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
          <div class="min-w-0">
            <h2 class="break-words text-lg font-semibold">
              {{ title }}
            </h2>
            <p class="truncate text-sm text-muted">
              {{ document.fileName }} · {{ formattedDate }}
            </p>
          </div>
          <UBadge
            :color="STATUS_COLORS[document.status]"
            variant="subtle"
          >
            {{ t(STATUS_I18N_KEYS[document.status]) }}
          </UBadge>
        </div>
        <div class="flex items-center gap-2 text-sm text-muted">
          <span>{{ t('documents.headerConfidence') }}:</span>
          <span :class="averageConfidence !== null && averageConfidence <= 0.9 ? 'text-warning' : 'text-highlighted'">
            {{ averageConfidence !== null ? `${Math.round(averageConfidence * 100)}%` : '—' }}
          </span>
        </div>
        <ProcessingTimeline
          v-if="isStalled || hasExtractionError"
          :status="document.status"
          :document-type-id="document.documentTypeId"
        />
      </div>
    </template>

    <UAlert
      v-if="hasExtractionError"
      color="error"
      :title="t('documents.errorTitle')"
      :description="document.error ?? t('documents.errorFallback')"
    />

    <UAlert
      v-if="isStalled"
      color="warning"
      :title="t('documents.stalledTitle')"
      :description="t('documents.stalledDescription')"
    />

    <UAlert
      v-else-if="hasExtractedDataLoadError"
      color="error"
      :title="t('documents.errorTitle')"
      :description="t('documents.extractedDataLoadError')"
    />

    <UAlert
      v-else-if="isMissingExtraction"
      color="warning"
      :description="t('documents.extractionMissing')"
    />

    <div v-else-if="extractedData">
      <!--
        Above the transcription, and in its own framed block, because these are
        not another way of reading the same page: they are the figures the
        client's cross-check compares against the exógena. Everything below is
        what the paper says; this is what the paper is being held to.
      -->
      <section
        v-if="hasMappedConcepts"
        class="mb-6 rounded-lg border border-default bg-elevated/40 p-3"
        data-testid="mapped-concepts"
      >
        <template v-if="mapped.crossed.length > 0">
          <h3 class="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">
            {{ t('documents.mapped.crossed') }}
          </h3>
          <MappedConceptList
            :fields="mapped.crossed"
            :confidence="extractedData.confidence"
          />
        </template>

        <template v-if="mapped.uncrossed.length > 0">
          <h3
            class="mb-1 text-xs font-semibold uppercase tracking-wide text-muted"
            :class="mapped.crossed.length > 0 ? 'mt-5' : ''"
          >
            {{ t('documents.mapped.uncrossed') }}
          </h3>
          <MappedConceptList
            :fields="mapped.uncrossed"
            :confidence="extractedData.confidence"
          />
        </template>
      </section>

      <div
        v-if="showSections"
        class="flex flex-col gap-6"
      >
        <section
          v-for="section in sections"
          :key="section.name || 'unsectioned'"
        >
          <h3 class="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">
            {{ section.name || t('documents.otherFields') }}
          </h3>
          <div class="divide-y divide-default">
            <ExtractionFieldRow
              v-for="entry in section.items"
              :key="entry.key"
              :field-key="entry.key"
              :value="entry.value"
              :confidence="entry.confidence"
              :label="entry.label"
            />
          </div>
        </section>
      </div>

      <div
        v-else
        class="divide-y divide-default"
      >
        <ExtractionFieldRow
          v-for="entry in fieldEntries"
          :key="entry.key"
          :field-key="entry.key"
          :value="entry.value"
          :confidence="entry.confidence"
          :label="entry.label"
        />
      </div>
    </div>

    <template #footer>
      <!--
        The only control on this screen. It reads the document — by its own
        parser or by OCR against the configured types, whichever the file calls
        for — signs off on the result, and rebuilds the client's cross-check
        from it. Pressing it again redoes all of that, which is how a document
        gets re-read once a type has been configured for it.
      -->
      <UButton
        :disabled="!canApprove"
        :loading="approving"
        block
        class="sm:w-auto"
        @click="emit('approve')"
      >
        {{ isApproved ? t('documents.status.approved') : t('documents.approveAndSend') }}
      </UButton>
      <p
        v-if="actionError"
        class="mt-2 text-sm text-error"
      >
        {{ actionError }}
      </p>
    </template>
  </UCard>
</template>
