<script setup lang="ts">
import { confidenceBarColorClass, confidenceBarWidthPercent } from '~/components/documents/confidence'
import ExtractionValue from '~/components/documents/ExtractionValue.vue'
import { humanizeFieldKey } from '~/utils/extraction-field-display'

const props = defineProps<{
  fieldKey: string
  value: unknown
  confidence: number | null
}>()

const label = computed(() => humanizeFieldKey(props.fieldKey))
</script>

<template>
  <div class="py-3">
    <!-- `break-words`: an extracted value is arbitrary OCR output (a long IBAN, a URL) with
         no space to wrap at, so without it the row pushes the card past the viewport. -->
    <div class="flex flex-col gap-1.5 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
      <span class="font-mono text-sm text-muted sm:pt-0.5">{{ label }}</span>

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
