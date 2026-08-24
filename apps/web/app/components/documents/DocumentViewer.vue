<script setup lang="ts">
// Preview depends on the Drive file being accessible to the signed-in user (owner or shared
// with them). A 403 from Drive is not handled here — tracked as a follow-up.
const props = defineProps<{
  driveFileId: string
  mimeType: string
  fileName: string
}>()

const { t } = useI18n()

const previewKind = computed<'pdf' | 'image' | 'unsupported'>(() => {
  if (props.mimeType === 'application/pdf') {
    return 'pdf'
  }
  if (props.mimeType.startsWith('image/')) {
    return 'image'
  }
  return 'unsupported'
})

const driveViewUrl = computed(() => `https://drive.google.com/file/d/${props.driveFileId}/view`)

/**
 * The page itself, with the reader's own PDF chrome turned off.
 *
 * Chrome's viewer opens with a toolbar and a thumbnail rail, which here are
 * controls for a document nobody is editing — they take a third of the width
 * and put a page-number box and a print button on a screen about choosing
 * fields. `#toolbar=0&navpanes=0` leaves the page and the scroll.
 */
const PDF_VIEW = '#toolbar=0&navpanes=0&scrollbar=0&view=FitH'
</script>

<template>
  <div class="w-full">
    <iframe
      v-if="previewKind === 'pdf'"
      :src="`https://drive.google.com/file/d/${driveFileId}/preview${PDF_VIEW}`"
      class="w-full aspect-[3/4] rounded-lg border border-default"
      allow="autoplay"
    />
    <img
      v-else-if="previewKind === 'image'"
      :src="`https://drive.google.com/thumbnail?id=${driveFileId}&sz=w1600`"
      :alt="fileName"
      class="w-full rounded-lg border border-default"
    >
    <div
      v-else
      class="flex flex-col items-center gap-4 rounded-lg border border-default p-8 text-center"
    >
      <p class="text-muted">
        {{ t('documents.viewer.unsupportedMime') }}
      </p>
      <UButton
        :to="driveViewUrl"
        target="_blank"
        variant="outline"
      >
        {{ t('documents.viewer.openInDrive') }}
      </UButton>
    </div>
  </div>
</template>
