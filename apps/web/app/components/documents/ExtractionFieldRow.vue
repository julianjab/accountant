<script setup lang="ts">
import { confidenceBarColorClass, confidenceBarWidthPercent, confidenceValueColorClass } from '~/components/documents/confidence'

const props = defineProps<{
  fieldKey: string
  value: unknown
  confidence: number | null
}>()

const displayValue = computed(() => {
  if (props.value === null || props.value === undefined) {
    return '—'
  }
  if (typeof props.value === 'object') {
    return JSON.stringify(props.value)
  }
  return String(props.value)
})
</script>

<template>
  <div class="py-3">
    <div class="flex items-center justify-between gap-4">
      <span class="font-mono text-sm text-muted">{{ fieldKey }}</span>
      <span :class="confidenceValueColorClass(confidence)">{{ displayValue }}</span>
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
