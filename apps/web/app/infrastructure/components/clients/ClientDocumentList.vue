<script setup lang="ts">
import type { ClientDocument, DocumentStatus } from '~/domain/entities/document'
import type { DocumentType } from '~/domain/entities/document-type'

const props = defineProps<{
  documents: ClientDocument[]
  types: DocumentType[]
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
</script>

<template>
  <p
    v-if="!documents.length"
    class="p-4 text-[13px] text-neutral-700"
  >
    {{ t('clients.detail.documents.empty') }}
  </p>

  <ul
    v-else
    class="divide-y divide-line-25"
  >
    <li
      v-for="doc in documents"
      :key="doc.id"
      class="flex items-center gap-3 px-4 py-2.5"
    >
      <UIcon
        name="i-lucide-file-text"
        class="size-4 shrink-0 text-neutral-500"
      />

      <div class="min-w-0 max-w-[320px] flex-1">
        <div class="truncate text-[13.5px] font-medium text-neutral-900">
          {{ doc.fileName }}
        </div>
        <div class="mt-0.5 truncate text-[12px] text-neutral-600">
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
  </ul>
</template>
