<script setup lang="ts">
import type { DocumentStatus } from '~/domain/entities/document'

const props = defineProps<{
  status?: DocumentStatus
  total: number
  filtered: number
}>()

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const CHIPS: { value: DocumentStatus | 'all', labelKey: string }[] = [
  { value: 'all', labelKey: 'inbox.filter.all' },
  { value: 'pending', labelKey: 'inbox.filter.pending' },
  { value: 'classifying', labelKey: 'inbox.filter.classifying' },
  { value: 'running_ocr', labelKey: 'inbox.filter.runningOcr' },
  { value: 'processed', labelKey: 'inbox.filter.processed' },
  { value: 'failed', labelKey: 'inbox.filter.failed' }
]

function isActive(value: DocumentStatus | 'all') {
  return value === 'all' ? props.status === undefined : props.status === value
}

function select(value: DocumentStatus | 'all') {
  const query = { ...route.query }
  if (value === 'all') {
    delete query.status
  } else {
    query.status = value
  }
  router.replace({ query })
}
</script>

<template>
  <div class="flex items-center justify-between gap-3 border-b border-default px-4 py-3">
    <div class="flex flex-wrap items-center gap-2">
      <button
        v-for="chip in CHIPS"
        :key="chip.value"
        type="button"
        class="rounded-full border px-3 py-1.5 text-[12.5px] font-medium transition-colors duration-[120ms]"
        :class="isActive(chip.value)
          ? 'border-neutral-950 bg-neutral-950 text-invert'
          : 'border-default bg-default text-toned hover:bg-elevated'"
        @click="select(chip.value)"
      >
        {{ t(chip.labelKey) }}
      </button>
    </div>
    <span class="shrink-0 text-[12px] text-muted">
      {{ t('inbox.filterCount', { filtered, total }) }}
    </span>
  </div>
</template>
