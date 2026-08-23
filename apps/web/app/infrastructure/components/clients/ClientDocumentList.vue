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
    class="p-4 text-[13px] text-toned"
  >
    {{ t('clients.detail.documents.empty') }}
  </p>

  <ul
    v-else
    class="divide-y divide-default"
  >
    <li
      v-for="doc in documents"
      :key="doc.id"
      class="flex items-center gap-3 px-4 py-2.5"
    >
      <UIcon
        name="i-lucide-file-text"
        class="size-4 shrink-0 text-muted"
      />

      <!-- The 320px cap keeps the desktop list from stretching a long file name across the
           whole card; on a phone the row is already narrower than that. -->
      <div class="min-w-0 flex-1 sm:max-w-[320px]">
        <div class="truncate text-[13.5px] font-medium text-highlighted">
          {{ doc.fileName }}
        </div>
        <div class="mt-0.5 truncate text-[12px] text-muted">
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
