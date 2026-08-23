<script setup lang="ts">
import type { ClientDocument, DocumentStatus } from '~/domain/entities/document'
import type { DocumentType } from '~/domain/entities/document-type'

const props = defineProps<{
  document: ClientDocument
  documentType: DocumentType | undefined
}>()

const { t } = useI18n()

// TODO(design-system): the inbox spec (design-system/README.md § 2) only defines a badge
// per Document.status pending|classifying|running_ocr|processed|failed. "approved" is a
// later status (post-processing review) with no dedicated token yet — reusing "processed"
// until the design system defines one.
const STATUS_COLOR: Record<DocumentStatus, { bg: string, fg: string }> = {
  pending: { bg: 'bg-status-pending-bg', fg: 'text-status-pending-fg' },
  classifying: { bg: 'bg-status-classifying-bg', fg: 'text-status-classifying-fg' },
  running_ocr: { bg: 'bg-status-running-ocr-bg', fg: 'text-status-running-ocr-fg' },
  processed: { bg: 'bg-status-processed-bg', fg: 'text-status-processed-fg' },
  approved: { bg: 'bg-status-processed-bg', fg: 'text-status-processed-fg' },
  failed: { bg: 'bg-status-failed-bg', fg: 'text-status-failed-fg' }
}

function iconForFile(fileName: string): string {
  const extension = fileName.split('.').pop()?.toLowerCase() ?? ''
  if (extension === 'pdf') return 'i-lucide-file-text'
  if (['jpg', 'jpeg', 'png', 'heic', 'tiff', 'tif'].includes(extension)) return 'i-lucide-image'
  return 'i-lucide-file'
}

const icon = computed(() => iconForFile(props.document.fileName))
const statusColor = computed(() => STATUS_COLOR[props.document.status])
const typeLabel = computed(() => props.documentType?.name ?? t('inbox.unclassified'))

const time = computed(() =>
  new Date(props.document.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
)
</script>

<template>
  <NuxtLink
    :to="`/documents/${document.id}`"
    class="grid grid-cols-[minmax(0,1.9fr)_minmax(0,1.1fr)_auto_90px] items-center gap-3 border-b border-line-25 py-[9px] pr-4 pl-12 transition-colors duration-[120ms] hover:bg-paper-50"
  >
    <div class="flex min-w-0 items-center gap-2.5">
      <div class="flex h-[26px] w-[22px] shrink-0 items-center justify-center rounded-[3px] border border-line-150 bg-paper-100">
        <UIcon
          :name="icon"
          class="size-3.5 text-neutral-600"
        />
      </div>
      <span
        class="truncate text-[13.5px] font-medium text-neutral-900"
        :title="document.fileName"
      >{{ document.fileName }}</span>
    </div>
    <span class="truncate text-[13px] text-neutral-700">{{ typeLabel }}</span>
    <UBadge
      :class="[statusColor.bg, statusColor.fg]"
      variant="soft"
      size="sm"
    >
      {{ t(`inbox.status.${document.status}`) }}
    </UBadge>
    <span
      class="text-right font-mono text-[12px] text-neutral-500"
      :title="document.createdAt"
    >{{ time }}</span>
  </NuxtLink>
</template>
