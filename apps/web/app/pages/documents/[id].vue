<script setup lang="ts">
import type { ClientDocument } from '~/domain/entities/document'
import type { DocumentSource } from '~/domain/entities/document-source'
import type { DocumentType } from '~/domain/entities/document-type'
import type { ExtractedData } from '~/domain/entities/extracted-data'
import DocumentViewer from '~/components/documents/DocumentViewer.vue'
import ExtractionCard from '~/components/documents/ExtractionCard.vue'

const { t } = useI18n()
const route = useRoute()
const documentId = route.params.id as string

const getDocument = useGetDocumentUseCase()
const getExtractedData = useGetDocumentExtractedDataUseCase()
const getDocumentType = useGetDocumentTypeUseCase()
const listDocumentSources = useListDocumentSourcesUseCase()
const recognizeDocumentSource = useRecognizeDocumentSourceUseCase()
const approveDocument = useApproveDocumentUseCase()
const { isAuthenticated, isLoading: isAuthLoading } = useGoogleAuth()
const { setLabel: setBreadcrumbLabel, clearLabel: clearBreadcrumbLabel } = useBreadcrumbLabels()
const showSignedOut = computed(() => !isAuthLoading.value && !isAuthenticated.value)

// Deferred and client-only on purpose: these endpoints need the session
// cookie, which SSR does not carry (see clients/index.vue).
const { data: document, pending: documentPending, error: documentError, refresh: refreshDocument } = await useAsyncData<ClientDocument>(
  `document-${documentId}`,
  () => getDocument.execute(documentId),
  { immediate: false, server: false }
)

// Covers the gap between auth resolving and `document` resolving, where nothing would
// otherwise render.
const showSkeleton = computed(() => isAuthLoading.value || (isAuthenticated.value && documentPending.value && !document.value && !documentError.value))

const { data: extractedData, error: extractedDataError, refresh: refreshExtractedData } = await useAsyncData<
  ExtractedData | null
>(
  `document-${documentId}-extracted-data`,
  () => getExtractedData.execute(documentId),
  { immediate: false, server: false }
)

// Depends on `document` having loaded (needs its `documentTypeId`), so it is only refreshed
// after `refreshDocument` resolves rather than alongside it.
const { data: documentType, refresh: refreshDocumentType } = await useAsyncData<DocumentType | null>(
  `document-${documentId}-type`,
  () => (document.value?.documentTypeId ? getDocumentType.execute(document.value.documentTypeId) : Promise.resolve(null)),
  { immediate: false, server: false, default: () => null }
)

// Narrowed to the sources whose parser accepts this file, so the reader is
// never offered one that would refuse it — a refusal they would only see after
// choosing. Depends on `document` for its media type, so it waits behind it.
const { data: sources, refresh: refreshSources } = await useAsyncData<DocumentSource[]>(
  `document-${documentId}-sources`,
  () => (document.value ? listDocumentSources.execute(document.value.mimeType) : Promise.resolve([])),
  { immediate: false, server: false, default: () => [] }
)

watch(
  isAuthenticated,
  async (authenticated) => {
    if (!authenticated) return
    // `refreshExtractedData` has no dependency on `document`, so it fires
    // alongside it instead of waiting behind it — only `refreshDocumentType`
    // and `refreshSources` need `document` to have resolved.
    const documentPromise = refreshDocument()
    refreshExtractedData()
    await documentPromise
    refreshDocumentType()
    refreshSources()
  },
  { immediate: true }
)

const recognizing = ref(false)
const approving = ref(false)
const actionError = ref<string | null>(null)

async function onRecognize(sourceId: string) {
  recognizing.value = true
  actionError.value = null
  try {
    await recognizeDocumentSource.execute(documentId, sourceId)
    // The document and its extraction both changed; the type did not, since a
    // document read this way deliberately never gets one.
    await Promise.all([refreshDocument(), refreshExtractedData()])
  } catch (error) {
    // 422 is the expected one: the file is not the source it was said to be.
    // Nothing was written, so the reader can simply pick again.
    actionError.value = errorMessage(error, t('documents.declareSource.failed'))
  } finally {
    recognizing.value = false
  }
}

async function onApprove() {
  approving.value = true
  actionError.value = null
  try {
    await approveDocument.execute(documentId)
    await refreshDocument()
  } catch (error) {
    actionError.value = errorMessage(error, t('documents.approveFailed'))
  } finally {
    approving.value = false
  }
}

/** The server's own explanation when it sent one — it names *why* the file was
 * refused, which a generic message cannot. */
function errorMessage(error: unknown, fallback: string): string {
  const detail = (error as { data?: { detail?: unknown } })?.data?.detail
  return typeof detail === 'string' && detail.length > 0 ? detail : fallback
}

// The breadcrumb only knows the URL (`/documents/<id>`); this is the one place that also has
// the file name, so it hands over a readable label rather than leaving the crumb as a raw id.
// It's also the only place that knows which client owns this document, so it points the
// parent "documents" crumb at that client's page — `/documents` has no index of its own to
// link to otherwise, and a dead crumb is worse than a slightly indirect one.
//
// Pinned at setup rather than read from `route` each time: `route` is the global reactive
// object, so by the time this page unmounts it already points at wherever we navigated to.
// Clearing that path would wipe the label the *next* page just set for itself, and leave
// this one's behind forever.
const ownPath = route.path
const documentsPath = ownPath.replace(/\/[^/]+$/, '')

watch(
  document,
  (loadedDocument) => {
    if (loadedDocument) {
      setBreadcrumbLabel(ownPath, loadedDocument.fileName)
      setBreadcrumbLabel(documentsPath, t('nav.documents'), `/clients/${loadedDocument.clientId}`)
    }
  },
  { immediate: true }
)

onUnmounted(() => {
  clearBreadcrumbLabel(ownPath)
  clearBreadcrumbLabel(documentsPath)
})
</script>

<template>
  <UContainer class="py-6 sm:py-8">
    <div v-if="showSkeleton">
      <USkeleton class="mb-4 h-6 w-48 sm:mb-6" />
      <div class="grid grid-cols-1 gap-4 sm:gap-6 lg:grid-cols-2">
        <SkeletonCard :lines="6" />
        <SkeletonCard :lines="6" />
      </div>
    </div>

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
      <div class="mb-4 flex flex-wrap items-center justify-between gap-3 sm:mb-6">
        <h1 class="text-xl font-semibold">
          {{ t('documents.title') }}
        </h1>
        <!--
          Offered on a document with no type because that is exactly when it
          is needed: the classifier had nothing to match this paper against,
          and this is the paper to teach it from. The type then keeps pointing
          at it, so its fields stay checkable against the page.
        -->
        <UButton
          v-if="!document.documentTypeId"
          :to="`/document-types/new?document=${document.id}`"
          variant="outline"
          size="sm"
        >
          {{ t('documents.defineTypeFromThis') }}
        </UButton>
        <!--
          The same offer for a document that already has a type: this is the
          paper its configuration can be read from, which is how a type
          configured before descriptions were stored gets them.
        -->
        <UButton
          v-else
          :to="`/document-types/${document.documentTypeId}?document=${document.id}`"
          variant="outline"
          size="sm"
        >
          {{ t('documents.configureTypeFromThis') }}
        </UButton>
      </div>
      <!-- Preview above the extracted fields on one column, side by side from `lg` up. -->
      <div class="grid grid-cols-1 gap-4 sm:gap-6 lg:grid-cols-2">
        <DocumentViewer
          :drive-file-id="document.driveFileId"
          :mime-type="document.mimeType"
          :file-name="document.fileName"
        />
        <ExtractionCard
          :document="document"
          :document-type="documentType ?? null"
          :extracted-data="extractedData ?? null"
          :extracted-data-error="!!extractedDataError"
          :sources="sources ?? []"
          :recognizing="recognizing"
          :approving="approving"
          :action-error="actionError"
          @recognize="onRecognize"
          @approve="onApprove"
        />
      </div>
    </template>
  </UContainer>
</template>
