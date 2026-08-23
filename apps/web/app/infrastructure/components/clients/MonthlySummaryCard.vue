<script setup lang="ts">
import type { ClientDocument, DocumentStatus } from '~/domain/entities/document'

const props = defineProps<{
  documents: ClientDocument[]
}>()

const { t } = useI18n()

const STATUSES: DocumentStatus[] = ['pending', 'classifying', 'running_ocr', 'processed', 'failed']

const countsByStatus = computed(() => {
  const now = new Date()
  const currentMonthDocs = props.documents.filter((doc) => {
    const createdAt = new Date(doc.createdAt)
    return createdAt.getFullYear() === now.getFullYear() && createdAt.getMonth() === now.getMonth()
  })

  return STATUSES.map(status => ({
    status,
    count: currentMonthDocs.filter(doc => doc.status === status).length
  }))
})
</script>

<template>
  <UCard :ui="{ body: 'p-4' }">
    <div class="mb-3 text-[11.5px] font-medium tracking-[0.08em] text-neutral-600 uppercase">
      {{ t('clients.detail.summary.title') }}
    </div>

    <div
      v-for="row in countsByStatus"
      :key="row.status"
      class="flex items-baseline justify-between border-b border-line-25 py-[7px] last:border-b-0"
    >
      <span class="text-[13px] text-neutral-800">{{ t(`documents.status.${row.status}`) }}</span>
      <span class="font-mono text-[13px] font-medium">{{ row.count }}</span>
    </div>
  </UCard>
</template>
