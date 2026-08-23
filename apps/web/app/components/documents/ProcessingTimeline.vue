<script setup lang="ts">
import type { DocumentStatus } from '~/domain/entities/document'

// The pipeline (process_uploaded_document.py) never persists 'pending' — it creates the
// Document directly in 'classifying'. The enum still allows it, so it renders here the same
// way as 'classifying' not yet completed (defensive, in case a future caller emits it).
const props = defineProps<{
  status: DocumentStatus
  documentTypeId: string | null
}>()

const { t } = useI18n()

type StepKey = 'detected' | 'classified' | 'ocr' | 'ready'

const failedAt = computed<'classified' | 'ocr' | null>(() => {
  if (props.status !== 'failed') {
    return null
  }
  return props.documentTypeId === null ? 'classified' : 'ocr'
})

const completed = computed<Record<StepKey, boolean>>(() => ({
  detected: true,
  classified: ['running_ocr', 'processed', 'approved'].includes(props.status)
    || (props.status === 'failed' && props.documentTypeId !== null),
  ocr: ['processed', 'approved'].includes(props.status),
  ready: ['processed', 'approved'].includes(props.status)
}))

const steps = computed(() => (['detected', 'classified', 'ocr', 'ready'] as StepKey[]).map(key => ({
  key,
  label: t(`documents.pipeline.${key}`),
  isCompleted: completed.value[key],
  isFailed: failedAt.value === key
})))
</script>

<template>
  <ol class="flex flex-wrap items-center gap-x-4 gap-y-2">
    <li
      v-for="step in steps"
      :key="step.key"
      class="flex items-center gap-2"
    >
      <UIcon
        v-if="step.isFailed"
        name="i-lucide-x-circle"
        class="text-error"
      />
      <UIcon
        v-else-if="step.isCompleted"
        name="i-lucide-check-circle"
        class="text-success"
      />
      <UIcon
        v-else
        name="i-lucide-circle"
        class="text-muted"
      />
      <span
        class="text-sm"
        :class="step.isFailed ? 'text-error' : step.isCompleted ? 'text-highlighted' : 'text-muted'"
      >
        {{ step.label }}
      </span>
    </li>
  </ol>
</template>
