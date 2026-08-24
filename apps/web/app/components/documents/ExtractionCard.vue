<script setup lang="ts">
import type { ClientDocument, DocumentStatus } from '~/domain/entities/document'
import type { DocumentSource } from '~/domain/entities/document-source'
import type { DocumentType } from '~/domain/entities/document-type'
import type { ExtractedData } from '~/domain/entities/extracted-data'
import ExtractionFieldRow from '~/components/documents/ExtractionFieldRow.vue'
import ProcessingTimeline from '~/components/documents/ProcessingTimeline.vue'
import { groupBySection, hasUsefulSections, labelFor } from '~/domain/field-sections'

const props = defineProps<{
  document: ClientDocument
  documentType: DocumentType | null
  extractedData: ExtractedData | null
  extractedDataError?: boolean
  /** The formats this file could be declared to be, already narrowed to ones
   * whose parser accepts its media type. Empty means there is nothing to
   * offer, and the picker stays hidden rather than showing an empty select. */
  sources?: DocumentSource[]
  recognizing?: boolean
  approving?: boolean
  reopening?: boolean
  actionError?: string | null
}>()

const emit = defineEmits<{
  recognize: [sourceId: string]
  approve: []
  reopen: []
}>()

// Preselected with whatever the document was already read as, so the control
// states the current answer rather than asking again from blank.
const chosenSource = ref<string | undefined>(props.document.sourceId ?? undefined)
watch(() => props.document.sourceId, (sourceId) => {
  chosenSource.value = sourceId ?? undefined
})

const { t, locale } = useI18n()

// A non-technical accountant should never see `documentTypeId` (a raw uuid) as this card's
// title — the classified type's name is what tells them what they are looking at, falling
// back to the id only when the type could not be resolved (e.g. it was deleted since).
// A document read by a parser has no type to name it, so its source label is
// what tells the reader what they are looking at. Falling through to the raw
// uuid stays the last resort, for a type that was deleted since.
const sourceLabel = computed(() =>
  props.sources?.find(source => source.id === props.document.sourceId)?.label ?? null
)

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

const sourceOptions = computed(() =>
  (props.sources ?? []).map(source => ({ label: source.label, value: source.id }))
)

const isApproved = computed(() => props.document.status === 'approved')

// Offered on a document that already has a source too, not only on a failed
// one: someone who picked the wrong format has no other way back, and the
// picker is the only place that answer lives. Withheld while an approval
// stands — the server refuses it, and offering a control that cannot work
// reads as a bug.
const canDeclareSource = computed(() =>
  sourceOptions.value.length > 0
  && !isApproved.value
  && (hasExtractionError.value || props.document.sourceId !== null)
)

// Already the current answer, so acting on it would rewrite the document with
// what it already says.
const wouldChangeSource = computed(() =>
  !!chosenSource.value && (hasExtractionError.value || chosenSource.value !== props.document.sourceId)
)

const canApprove = computed(() => props.document.status === 'processed')

const isProcessing = computed(() =>
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
          v-if="isProcessing || hasExtractionError"
          :status="document.status"
          :document-type-id="document.documentTypeId"
        />
      </div>
    </template>

    <div
      v-if="hasExtractionError || canDeclareSource"
      class="flex flex-col gap-4"
    >
      <UAlert
        v-if="hasExtractionError"
        color="error"
        :title="t('documents.errorTitle')"
        :description="document.error ?? t('documents.errorFallback')"
      />

      <!--
        Offered because the classifier structurally cannot reach these: they
        are read by a parser instead of being configured as document types, so
        a file of one of those formats always lands here. Naming it by hand is
        the only way it ever gets read — and the only way a wrong answer gets
        corrected.
      -->
      <section
        v-if="canDeclareSource"
        class="rounded-lg border border-default p-4"
      >
        <h3 class="text-sm font-semibold">
          {{ document.sourceId ? t('documents.declareSource.changeTitle') : t('documents.declareSource.title') }}
        </h3>
        <p class="mt-1 text-sm text-muted">
          {{ document.sourceId ? t('documents.declareSource.changeDescription') : t('documents.declareSource.description') }}
        </p>
        <div class="mt-3 flex flex-col gap-2 sm:flex-row">
          <USelectMenu
            v-model="chosenSource"
            :items="sourceOptions"
            value-key="value"
            :placeholder="t('documents.declareSource.placeholder')"
            class="sm:flex-1"
          />
          <UButton
            :disabled="!wouldChangeSource"
            :loading="recognizing"
            @click="chosenSource && emit('recognize', chosenSource)"
          >
            {{ document.sourceId ? t('documents.declareSource.reread') : t('documents.declareSource.action') }}
          </UButton>
        </div>
        <p
          v-if="actionError"
          class="mt-2 text-sm text-error"
        >
          {{ actionError }}
        </p>
      </section>
    </div>

    <div
      v-if="isProcessing"
      class="space-y-4"
    >
      <USkeleton
        v-for="i in 4"
        :key="i"
        class="h-12 w-full"
      />
    </div>

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

    <div
      v-else-if="extractedData && showSections"
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
      v-else-if="extractedData"
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

    <template #footer>
      <!--
        Approval is what puts the document in the spreadsheet export, and what
        stops a re-import from reprocessing it. Withdrawing it therefore sits
        right beside it rather than somewhere else: it is the only way back to
        changing anything about this document.
      -->
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
        <UButton
          v-if="!isApproved"
          :disabled="!canApprove"
          :loading="approving"
          block
          class="sm:w-auto"
          :title="canApprove ? undefined : t('documents.approveDisabledHint')"
          @click="emit('approve')"
        >
          {{ t('documents.approveAndSend') }}
        </UButton>
        <template v-else>
          <p class="text-sm text-muted">
            {{ t('documents.approvedNote') }}
          </p>
          <UButton
            variant="outline"
            size="sm"
            :loading="reopening"
            class="sm:ml-auto"
            @click="emit('reopen')"
          >
            {{ t('documents.reopen') }}
          </UButton>
        </template>
      </div>
      <p
        v-if="actionError && !canDeclareSource"
        class="mt-2 text-sm text-error"
      >
        {{ actionError }}
      </p>
    </template>
  </UCard>
</template>
