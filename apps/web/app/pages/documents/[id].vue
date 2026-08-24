<script setup lang="ts">
import type { ClientDocument } from '~/domain/entities/document'
import type { DocumentType } from '~/domain/entities/document-type'
import type { ExtractedData } from '~/domain/entities/extracted-data'
import type { ConceptMapping } from '~/domain/entities/concept-mapping'
import type { ReconciliationKind } from '~/domain/entities/reconciliation-kind'
import DocumentViewer from '~/components/documents/DocumentViewer.vue'
import ExtractionCard from '~/components/documents/ExtractionCard.vue'

const { t } = useI18n()
const route = useRoute()
const documentId = route.params.id as string

const getDocument = useGetDocumentUseCase()
const getExtractedData = useGetDocumentExtractedDataUseCase()
const getDocumentType = useGetDocumentTypeUseCase()
const listReconciliationKinds = useListReconciliationKindsUseCase()
const getConceptMapping = useGetConceptMappingUseCase()
const approveDocument = useApproveDocumentUseCase()
const reprocessDocument = useReprocessDocumentUseCase()
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

/**
 * What this document's type contributes to the cross-check.
 *
 * Read here rather than in the card so the card stays a renderer: the page
 * already owns every other fetch this screen makes. Both are absent for a
 * document with no type and for a type nobody mapped, which is the same thing
 * on screen — the transcription on its own.
 *
 * The kind is taken as the first one published rather than named: only one
 * reconciliation model exists today, and hard-coding its id in a second place
 * would make adding the next one a hunt.
 */
const { data: kinds, refresh: refreshKinds } = await useAsyncData<ReconciliationKind[]>(
  'reconciliation-kinds',
  () => listReconciliationKinds.execute(),
  { immediate: false, server: false, default: () => [] }
)

const kind = computed<ReconciliationKind | null>(() => kinds.value?.[0] ?? null)

const { data: conceptMapping, refresh: refreshConceptMapping } = await useAsyncData<ConceptMapping | null>(
  `document-${documentId}-mapping`,
  () =>
    kind.value && document.value?.documentTypeId
      ? getConceptMapping.execute(kind.value.id, document.value.documentTypeId)
      : Promise.resolve(null),
  { immediate: false, server: false, default: () => null }
)

watch(
  isAuthenticated,
  async (authenticated) => {
    if (!authenticated) return
    // `refreshExtractedData` and `refreshKinds` have no dependency on
    // `document`, so they fire alongside it instead of waiting behind it —
    // only `refreshDocumentType` and `refreshConceptMapping` need
    // `document.value.documentTypeId` and must wait for it to resolve.
    const documentPromise = refreshDocument()
    refreshExtractedData()
    const kindsPromise = refreshKinds()
    await documentPromise
    refreshDocumentType()
    await kindsPromise
    refreshConceptMapping()
  },
  { immediate: true }
)

const approving = ref(false)
const actionError = ref<string | null>(null)

async function onApprove() {
  approving.value = true
  actionError.value = null
  try {
    await approveDocument.execute(documentId)
    // Approving is what produced the extraction, so both changed; the type may
    // have changed too, since an ordinary document is reclassified on the way
    // — and with it the mapping that says what the new type contributes.
    await refreshDocument()
    await Promise.all([refreshExtractedData(), refreshDocumentType(), refreshConceptMapping()])
  } catch (error) {
    actionError.value = errorMessage(error, t('documents.approveFailed'))
  } finally {
    approving.value = false
  }
}

const reprocessing = ref(false)

/**
 * Reads the document again and leaves it unapproved.
 *
 * Refreshes exactly what approving does, and for the same reason: the reread
 * reclassifies the document, so its type — and the mapping that says what that
 * type contributes — can both come back different.
 */
async function onReprocess() {
  reprocessing.value = true
  actionError.value = null
  try {
    await reprocessDocument.execute(documentId)
    await refreshDocument()
    await Promise.all([refreshExtractedData(), refreshDocumentType(), refreshConceptMapping()])
  } catch (error) {
    actionError.value = errorMessage(error, t('documents.reprocessFailed'))
  } finally {
    reprocessing.value = false
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
          :concept-mapping="conceptMapping ?? null"
          :reconciliation-kind="kind"
          :extracted-data-error="!!extractedDataError"
          :approving="approving"
          :reprocessing="reprocessing"
          :action-error="actionError"
          @approve="onApprove"
          @reprocess="onReprocess"
        />
      </div>
    </template>
  </UContainer>
</template>
