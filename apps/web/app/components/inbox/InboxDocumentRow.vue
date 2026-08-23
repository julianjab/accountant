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
  <!--
    One row of four columns from `sm` up; below that it folds into two lines — the file name,
    then its type/status/time — because four columns inside ~300px leaves the file name, the
    only thing that identifies the document, as three characters and an ellipsis.
    `sm:contents` dissolves the second line's wrapper so the four cells land in the grid
    directly, keeping a single DOM for both shapes.
  -->
  <NuxtLink
    :to="`/documents/${document.id}`"
    class="flex flex-col gap-1.5 border-b border-muted px-4 py-3 transition-colors duration-[120ms] hover:bg-elevated sm:grid sm:grid-cols-[minmax(0,1.9fr)_minmax(0,1.1fr)_auto_90px] sm:items-center sm:gap-3 sm:py-[9px] sm:pr-4 sm:pl-12"
  >
    <div class="flex min-w-0 items-center gap-2.5">
      <div class="flex h-[26px] w-[22px] shrink-0 items-center justify-center rounded-[3px] border border-default bg-muted">
        <UIcon
          :name="icon"
          class="size-3.5 text-muted"
        />
      </div>
      <span
        class="truncate text-[13.5px] font-medium text-highlighted"
        :title="document.fileName"
      >{{ document.fileName }}</span>
    </div>

    <div class="flex min-w-0 items-center gap-2 pl-[32px] sm:contents">
      <span class="truncate text-[13px] text-toned">{{ typeLabel }}</span>
      <UBadge
        class="shrink-0"
        :class="[statusColor.bg, statusColor.fg]"
        variant="soft"
        size="sm"
      >
        {{ t(`inbox.status.${document.status}`) }}
      </UBadge>
      <span
        class="ml-auto shrink-0 text-right font-mono text-[12px] text-muted sm:ml-0"
        :title="document.createdAt"
      >{{ time }}</span>
    </div>
  </NuxtLink>
</template>
