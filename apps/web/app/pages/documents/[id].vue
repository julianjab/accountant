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
const { isAuthenticated, isLoading: isAuthLoading } = useGoogleAuth()
const showSignedOut = computed(() => !isAuthLoading.value && !isAuthenticated.value)

// Deferred and client-only on purpose: these endpoints need the session
// cookie, which SSR does not carry (see clients/index.vue).
const { data: document, error: documentError, refresh: refreshDocument } = await useAsyncData<ClientDocument>(
  `document-${documentId}`,
  () => getDocument.execute(documentId),
  { immediate: false, server: false }
)

const { data: extractedData, error: extractedDataError, refresh: refreshExtractedData } = await useAsyncData<
  ExtractedData | null
>(
  `document-${documentId}-extracted-data`,
  () => getExtractedData.execute(documentId),
  { immediate: false, server: false }
)

watch(
  isAuthenticated,
  (authenticated) => {
    if (!authenticated) return
    refreshDocument()
    refreshExtractedData()
  },
  { immediate: true }
)
</script>

<template>
  <UContainer class="py-8">
    <p
      v-if="isAuthLoading"
      class="text-muted"
    >
      {{ t('auth.loading') }}
    </p>

    <p
      v-else-if="showSignedOut"
      class="text-muted"
    >
      {{ t('documents.signInRequired') }}
    </p>

    <UAlert
      v-else-if="documentError"
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
