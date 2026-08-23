<script setup lang="ts">
import type { ClientDocument } from '~/domain/entities/document'
import type { ExtractedData } from '~/domain/entities/extracted-data'
import DocumentViewer from '~/components/documents/DocumentViewer.vue'
import ExtractionCard from '~/components/documents/ExtractionCard.vue'

const { t } = useI18n()
const route = useRoute()
const documentId = route.params.id as string

const getDocument = useGetDocumentUseCase()
const getExtractedData = useGetDocumentExtractedDataUseCase()

const { data: document, error: documentError } = await useAsyncData<ClientDocument>(
  `document-${documentId}`,
  () => getDocument.execute(documentId)
)

const { data: extractedData, error: extractedDataError } = await useAsyncData<ExtractedData | null>(
  `document-${documentId}-extracted-data`,
  () => getExtractedData.execute(documentId)
)
</script>

<template>
  <UContainer class="py-8">
    <UAlert
      v-if="documentError"
      color="error"
      :title="t('documents.notFound')"
    />

    <template v-else-if="document">
      <h1 class="text-xl font-semibold mb-6">
        {{ t('documents.title') }}
      </h1>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <DocumentViewer
          :drive-file-id="document.driveFileId"
          :mime-type="document.mimeType"
          :file-name="document.fileName"
        />
        <ExtractionCard
          :document="document"
          :extracted-data="extractedData ?? null"
          :extracted-data-error="!!extractedDataError"
        />
      </div>
    </template>
  </UContainer>
</template>
