<script setup lang="ts">
import { confidenceBarColorClass, confidenceBarWidthPercent } from '~/components/documents/confidence'
import ExtractionValue from '~/components/documents/ExtractionValue.vue'
import { humanizeFieldKey } from '~/utils/extraction-field-display'

const props = defineProps<{
  fieldKey: string
  value: unknown
  confidence: number | null
  /**
   * What the document calls this field, when its type recorded a name.
   * Preferred over the key: `saldo_final` is a guess at the document's words,
   * "Saldo a 31 de diciembre" is the document's words.
   */
  label?: string
}>()

const displayLabel = computed(() => props.label || humanizeFieldKey(props.fieldKey))

// The key is machine output and reads as such; a name taken from the document
// is prose and should not be set in a face that says "identifier".
const isDocumentLabel = computed(() => Boolean(props.label))
</script>

<template>
  <div class="py-3">
    <!-- `break-words`: an extracted value is arbitrary OCR output (a long IBAN, a URL) with
         no space to wrap at, so without it the row pushes the card past the viewport. -->
    <div class="flex flex-col gap-1.5 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
      <span
        class="text-sm text-muted sm:pt-0.5"
        :class="isDocumentLabel ? '' : 'font-mono'"
      >{{ displayLabel }}</span>

      <div class="w-full break-words sm:max-w-[70%] sm:text-right">
        <ExtractionValue
          :field-key="fieldKey"
          :value="value"
          :confidence="confidence"
        />
      </div>
    </div>
    <div
      v-if="confidence !== null"
      class="mt-2 h-[34px] w-full rounded bg-elevated"
    >
      <div
        class="h-full rounded"
        :class="confidenceBarColorClass(confidence)"
        :style="{ width: `${confidenceBarWidthPercent(confidence)}%` }"
      />
    </div>
  </div>
</template>
