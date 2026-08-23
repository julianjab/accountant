<script setup lang="ts">
import type { ClientDocument, DocumentStatus } from '~/domain/entities/document'
import type { ExtractedData } from '~/domain/entities/extracted-data'
import ExtractionFieldRow from '~/components/documents/ExtractionFieldRow.vue'
import ProcessingTimeline from '~/components/documents/ProcessingTimeline.vue'

const props = defineProps<{
  document: ClientDocument
  extractedData: ExtractedData | null
}>()

const { t } = useI18n()

const STATUS_COLORS: Record<DocumentStatus, 'info' | 'success' | 'error'> = {
  pending: 'info',
  classifying: 'info',
  running_ocr: 'info',
  processed: 'success',
  failed: 'error'
}

const STATUS_I18N_KEYS: Record<DocumentStatus, string> = {
  pending: 'documents.status.pending',
  classifying: 'documents.status.classifying',
  running_ocr: 'documents.status.runningOcr',
  processed: 'documents.status.processed',
  failed: 'documents.status.failed'
}

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
}

const fieldEntries = computed<FieldEntry[]>(() => {
  if (!props.extractedData) {
    return []
  }
  return Object.entries(props.extractedData.fields).map(([key, raw]) => {
    if (isFieldWithConfidence(raw)) {
      return { key, value: raw.value, confidence: raw.confidence }
    }
    return { key, value: raw, confidence: props.extractedData!.confidence }
  })
})

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

const hasExtractionError = computed(() =>
  props.document.status === 'failed'
  || (props.document.status === 'processed' && props.document.documentTypeId === null)
)

const isProcessing = computed(() =>
  (['pending', 'classifying', 'running_ocr'] as DocumentStatus[]).includes(props.document.status)
)

const isMissingExtraction = computed(() =>
  props.document.status === 'processed' && !hasExtractionError.value && !props.extractedData
)
</script>

<template>
  <UCard>
    <template #header>
      <div class="flex flex-col gap-3">
        <div class="flex items-center justify-between gap-4">
          <h2 class="text-lg font-semibold">
            {{ document.documentTypeId ?? t('documents.unknownType') }}
          </h2>
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

    <UAlert
      v-if="hasExtractionError"
      color="error"
      :title="t('documents.errorTitle')"
      :description="document.error ?? t('documents.errorFallback')"
    />

    <div
      v-else-if="isProcessing"
      class="space-y-4"
    >
      <USkeleton
        v-for="i in 4"
        :key="i"
        class="h-12 w-full"
      />
    </div>

    <UAlert
      v-else-if="isMissingExtraction"
      color="warning"
      :description="t('documents.extractionMissing')"
    />

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
      />
    </div>

    <template #footer>
      <UButton
        disabled
        :title="t('documents.approveDisabledHint')"
      >
        {{ t('documents.approveAndSend') }}
      </UButton>
    </template>
  </UCard>
</template>
