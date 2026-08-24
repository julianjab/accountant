<script setup lang="ts">
import type { ConceptMapping, MappingChange } from '~/domain/entities/concept-mapping'
import type { DocumentType, DocumentTypeField } from '~/domain/entities/document-type'
import type { ClientDocument } from '~/domain/entities/document'
import type { ReconciliationKind } from '~/domain/entities/reconciliation-kind'
import type { FieldSelection } from '~/domain/document-type-configuration'
import {
  buildFieldSelections,
  configurationStatus,
  fieldsMissingAccountPath,
  groupBySpineConcept,
  isDraftSavable,
  keptPaths,
  mappingChangeSeverity,
  shouldSaveDraft,
  toMappingDraft
} from '~/domain/document-type-configuration'
import { listSchemaFields, pruneSchema } from '~/domain/extraction-schema'
import {
  descriptionsForKnownPaths,
  labelFor,
  orderedSectionNames,
  sectionFor
} from '~/domain/field-sections'

const { t } = useI18n()
const route = useRoute()
const documentTypeId = route.params.id as string

const getDocumentType = useGetDocumentTypeUseCase()
const getDocument = useGetDocumentUseCase()
const proposeDocumentType = useProposeDocumentTypeUseCase()
const updateDocumentType = useUpdateDocumentTypeUseCase()
const listReconciliationKinds = useListReconciliationKindsUseCase()
const getConceptMapping = useGetConceptMappingUseCase()
const saveConceptMapping = useSaveConceptMappingUseCase()
const { setLabel: setBreadcrumbLabel } = useBreadcrumbLabels()
const { isAuthenticated, isLoading: isAuthLoading } = useGoogleAuth()

// A select cannot hold null, so "no concept" travels as a sentinel and is
// translated back at the edge — an unmapped field is a normal answer here.
const UNMAPPED = '__unmapped__'

// Deferred and client-only on purpose: these endpoints need the session
// cookie, which SSR does not carry (see clients/index.vue). Fired together
// from the isAuthenticated watcher below rather than awaited here in sequence
// — three awaited useAsyncData calls in <script setup> would otherwise chain
// into a waterfall that Suspense holds the whole route transition on.
const { data: documentType, pending, refresh: refreshDocumentType } = await useAsyncData<DocumentType | null>(
  `document-type-${documentTypeId}`,
  () => getDocumentType.execute(documentTypeId),
  { immediate: false, server: false, default: () => null }
)

const { data: kinds, refresh: refreshKinds } = await useAsyncData<ReconciliationKind[]>(
  'reconciliation-kinds',
  () => listReconciliationKinds.execute(),
  { immediate: false, server: false, default: () => [] }
)

/**
 * The document this type was configured from.
 *
 * Shown beside the fields because that is the only way to check them: a list
 * of labels and sections says what the AI claims the paper contains, and
 * nothing here says whether it read the paper right. Keyed on the type so it
 * loads once the type resolves, and simply absent for types configured before
 * the sample was recorded.
 */
const { data: sampleDocument } = await useAsyncData<ClientDocument | null>(
  `document-type-sample-${documentTypeId}`,
  () =>
    documentType.value?.sampleDocumentId
      ? getDocument.execute(documentType.value.sampleDocumentId)
      : Promise.resolve(null),
  { immediate: false, server: false, default: () => null, watch: [documentType] }
)

/**
 * A document offered in the URL to re-read this type from.
 *
 * The way in is the document detail: looking at a paper of this type is the
 * moment you can say "configure the type from this one".
 */
const offeredDocumentId = computed(() => {
  const value = route.query.document
  return typeof value === 'string' ? value : ''
})

const { data: offeredDocument, refresh: refreshOfferedDocument } = await useAsyncData<ClientDocument | null>(
  `document-type-offered-${documentTypeId}`,
  () =>
    offeredDocumentId.value
      ? getDocument.execute(offeredDocumentId.value)
      : Promise.resolve(null),
  { immediate: false, server: false, default: () => null }
)

const recovering = ref(false)
const recoveryFailed = ref(false)
/** How many of the type's fields the re-read managed to name, and out of how
 * many. Null until a recovery has run. */
const recovered = ref<{ named: number, total: number } | null>(null)

/**
 * Re-reads the offered document and stores what it calls this type's fields.
 *
 * Only the descriptions: the prompt, the schema and the concept mappings are
 * left exactly as they are, because those are what someone curated and this
 * is meant to add the labels they never got, not to reopen their decisions.
 */
async function recoverDescriptions() {
  if (recovering.value || !documentType.value || !offeredDocumentId.value) return

  recovering.value = true
  recoveryFailed.value = false

  try {
    const proposal = await proposeDocumentType.execute({
      name: documentType.value.name,
      documentId: offeredDocumentId.value
    })
    const known = schemaFields.value.map(field => field.path)
    const named: DocumentTypeField[] = descriptionsForKnownPaths(proposal.fields, known)

    await updateDocumentType.execute(documentTypeId, {
      fields: named,
      sampleDocumentId: offeredDocumentId.value
    })
    recovered.value = { named: named.length, total: known.length }
    await refreshDocumentType()
  } catch {
    recoveryFailed.value = true
  } finally {
    recovering.value = false
  }
}

const selectedKindId = ref<string | null>(null)
watch(
  kinds,
  (loaded) => {
    if (!selectedKindId.value && loaded.length > 0) selectedKindId.value = loaded[0]!.id
  },
  { immediate: true }
)

const selectedKind = computed(
  () => kinds.value.find(kind => kind.id === selectedKindId.value) ?? null
)

// `watch: [selectedKindId]` keeps refetching this whenever the selected kind
// changes (e.g. once `kinds` resolves and picks a default) independently of
// `immediate`, which only governs the very first call.
const { data: mapping, refresh: refreshMapping } = await useAsyncData<ConceptMapping | null>(
  `concept-mapping-${documentTypeId}`,
  () =>
    selectedKindId.value
      ? getConceptMapping.execute(selectedKindId.value, documentTypeId)
      : Promise.resolve(null),
  { immediate: false, server: false, default: () => null, watch: [selectedKindId] }
)

watch(
  isAuthenticated,
  (authenticated) => {
    if (!authenticated) return
    refreshDocumentType()
    refreshKinds()
    refreshMapping()
    refreshOfferedDocument()
  },
  { immediate: true }
)

// Same gap as document-types/index.vue: with `immediate: false`, `pending` starts `false`
// and `documentType` starts `null`, so without this the first render (and the permanently
// signed-out case, since the watcher above never fires) falls straight into "not found"
// instead of a loading or sign-in state.
const showSkeleton = computed(() => isAuthLoading.value || (isAuthenticated.value && pending.value && !documentType.value))

const name = ref('')
const description = ref('')
const active = ref(true)
const selections = ref<FieldSelection[]>([])
const reporterPath = ref<string | null>(null)
const reporterNamePath = ref<string | null>(null)
const periodPath = ref<string | null>(null)

const saving = ref(false)
const saved = ref(false)
const saveFailed = ref(false)
/** The type was written and its mapping was not — a state a plain failure
 * message would misreport, since retrying is not the same as starting over. */
const typeSavedWithoutMapping = ref(false)
const mappingChanges = ref<MappingChange[]>([])

const schemaFields = computed(() => listSchemaFields(documentType.value?.extractionSchema ?? {}))

function syncDetailsForm() {
  if (!documentType.value) return
  name.value = documentType.value.name
  description.value = documentType.value.description
  active.value = documentType.value.active
}

function syncMappingForm() {
  selections.value = buildFieldSelections(schemaFields.value, mapping.value)
  reporterPath.value = mapping.value?.reporterPath ?? null
  reporterNamePath.value = mapping.value?.reporterNamePath ?? null
  periodPath.value = mapping.value?.periodPath ?? null
}

watch(documentType, syncDetailsForm, { immediate: true })
// Also keyed on the schema, so a save that trimmed fields rebuilds the rows
// instead of leaving controls for fields that no longer exist.
watch([mapping, schemaFields], syncMappingForm, { immediate: true })

const draft = computed(() =>
  toMappingDraft(
    selections.value,
    {
      reporterPath: reporterPath.value,
      reporterNamePath: reporterNamePath.value,
      periodPath: periodPath.value
    },
    mapping.value
  )
)

const status = computed(() => configurationStatus(draft.value))
const canSave = computed(() => !saving.value && isDraftSavable(draft.value))

const prunedSchema = computed(() =>
  pruneSchema(documentType.value?.extractionSchema ?? {}, keptPaths(selections.value))
)

// PATCH re-checks the mapping against any schema it is given, so an unchanged
// schema is left out of the request entirely.
const schemaChanged = computed(
  () =>
    JSON.stringify(prunedSchema.value) !== JSON.stringify(documentType.value?.extractionSchema ?? {})
)

const removedCount = computed(() => selections.value.filter(selection => !selection.kept).length)

const descriptionByPath = computed(
  () => new Map(schemaFields.value.map(field => [field.path, field.description]))
)

/** Only fields that survive the edit can play a role: pointing the reporting
 * party at a field about to be dropped is the failure, not a choice. */
const keptFieldItems = computed(() =>
  selections.value
    .filter(selection => selection.kept)
    .map(selection => ({ label: selection.path, value: selection.path }))
)

const optionalFieldItems = computed(() => [
  { label: t('documentTypes.edit.fields.unsetField'), value: UNMAPPED },
  ...keptFieldItems.value
])

const conceptItems = computed(() => [
  { label: t('documentTypes.edit.fields.unmapped'), value: UNMAPPED },
  ...(selectedKind.value?.evidenceConcepts ?? []).map(concept => ({
    label: concept.label,
    value: concept.id
  }))
])

const spineItems = computed(() => [
  { label: t('documentTypes.edit.fields.noSpine'), value: UNMAPPED },
  ...(selectedKind.value?.spineConcepts ?? []).map(concept => ({
    label: concept.label,
    value: concept.id
  }))
])

const kindItems = computed(() => kinds.value.map(kind => ({ label: kind.label, value: kind.id })))

/** Both halves of the choice are spelled out as full sentences: the user has to
 * decide it by looking at the paper, not by knowing what "per account" means. */
const comparisonItems = computed(() => [
  {
    label: t('documentTypes.edit.fields.comparison.total'),
    value: 'total',
    description: t('documentTypes.edit.fields.comparison.totalHint')
  },
  {
    label: t('documentTypes.edit.fields.comparison.perAccount'),
    value: 'perAccount',
    description: t('documentTypes.edit.fields.comparison.perAccountHint')
  }
])

function conceptLabel(conceptId: string): string {
  const concept = selectedKind.value?.evidenceConcepts.find(candidate => candidate.id === conceptId)
  return concept?.label ?? conceptId
}

function spineConcept(conceptId: string) {
  return selectedKind.value?.spineConcepts.find(candidate => candidate.id === conceptId) ?? null
}

// Rows are rendered grouped by the line they answer, but edited in place, so
// the group only carries paths and the index is looked up here.
const indexByPath = computed(
  () => new Map(selections.value.map((selection, index) => [selection.path, index]))
)

// The group is a domain answer about paths; the row indices it is rendered
// with are a rendering detail, resolved once here instead of in the template.
const groups = computed(() =>
  groupBySpineConcept(selections.value).map(group => ({
    ...group,
    indices: group.paths.map(path => indexByPath.value.get(path) ?? -1).filter(index => index >= 0)
  }))
)

// Named per field below too; this only decides whether the summary line is
// worth showing, so nobody has to scan every group to find the one at fault.
const missingAccountPaths = computed(() => fieldsMissingAccountPath(selections.value))

const nameByPath = computed(
  () => new Map(schemaFields.value.map(field => [field.path, field.name]))
)

/** What the type recorded about its fields when it was created: the document's
 * own name for each one and the block of the page it sits in. */
const describedFields = computed(() => documentType.value?.fields ?? [])

/**
 * The rows are grouped by the line of the exogena they answer, which is the
 * question this screen exists to settle. The section is shown on the row
 * instead of as a second level of grouping: it says *where on the paper* the
 * field is, which is what someone needs to recognise a field, and a field's
 * block and the line it answers are independent — one exogena line is
 * routinely answered by figures from two different blocks.
 */
function fieldSection(path: string): string {
  return sectionFor(path, describedFields.value)
}

/** The document's own words where they exist, the schema's name otherwise. */
function fieldName(path: string): string {
  const described = labelFor(path, describedFields.value)
  if (described !== path) return described
  return nameByPath.value.get(path) ?? path
}

/** The blocks this document is divided into, listed so the reader can see the
 * shape of the paper before scrolling through its fields. */
const sectionNames = computed(() => orderedSectionNames(describedFields.value))

function selectValue(path: string | null): string {
  return path ?? UNMAPPED
}

function toPath(value: string): string | null {
  return value === UNMAPPED ? null : value
}

const KNOWN_CHANGES = ['entry_dropped', 'path_cleared', 'mapping_cleared', 'prune_failed']

function mappingChangeText(change: MappingChange): string {
  const key = KNOWN_CHANGES.includes(change.change) ? change.change : 'unknown'
  return t(`documentTypes.edit.mappingChanges.${key}`, {
    change: change.change,
    path: change.path ?? change.fieldPath ?? '—',
    field: change.fieldPath ?? change.path ?? '—',
    concept: change.conceptId ? conceptLabel(change.conceptId) : '—'
  })
}

async function save() {
  if (!canSave.value || !documentType.value || !selectedKindId.value) return

  saving.value = true
  saved.value = false
  saveFailed.value = false
  typeSavedWithoutMapping.value = false
  mappingChanges.value = []

  // Two writes with no transaction between them. If the second fails the type
  // is already changed on the server, so reporting a plain failure would be a
  // lie: the user would retry believing nothing was written, and the mapping
  // they see would no longer describe the stored schema.
  let typeSaved = false
  try {
    const update = await updateDocumentType.execute(documentTypeId, {
      name: name.value,
      description: description.value,
      active: active.value,
      ...(schemaChanged.value ? { extractionSchema: prunedSchema.value } : {})
    })
    typeSaved = true
    documentType.value = update.documentType
    mappingChanges.value = update.mappingChanges

    // The PATCH may have pruned the mapping on its own; this PUT then states
    // what the user actually asked for, which is the same set of entries minus
    // the trimmed fields.
    if (shouldSaveDraft(draft.value, mapping.value)) {
      mapping.value = await saveConceptMapping.execute(
        selectedKindId.value,
        documentTypeId,
        draft.value
      )
    }
    syncMappingForm()
    saved.value = true
  } catch {
    if (typeSaved) {
      // Re-read so the form stops showing a mapping the server no longer has.
      typeSavedWithoutMapping.value = true
      await refreshMapping()
      syncMappingForm()
    } else {
      saveFailed.value = true
    }
  } finally {
    saving.value = false
  }
}

// The breadcrumb only knows the URL; this is the one place that also knows the
// type's name, so it hands over a readable label instead of a raw id.
const ownPath = route.path
watch(
  documentType,
  (loaded) => {
    if (loaded) setBreadcrumbLabel(ownPath, loaded.name)
  },
  { immediate: true }
)
</script>

<template>
  <UContainer class="py-6 sm:py-8">
    <SkeletonCard
      v-if="showSkeleton"
      :lines="4"
    />

    <p
      v-else-if="!isAuthenticated"
      class="text-muted"
    >
      {{ t('documentTypes.signInRequired') }}
    </p>

    <p
      v-else-if="!documentType"
      class="text-muted"
    >
      {{ t('documentTypes.edit.notFound') }}
    </p>

    <div
      v-else
      class="flex flex-col gap-6"
    >
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 class="min-w-0 break-words text-xl font-semibold">
          {{ documentType.name }}
        </h1>
        <UBadge
          :color="status === 'configured' ? 'success' : status === 'unusable' ? 'error' : 'neutral'"
          variant="subtle"
          class="w-fit shrink-0"
          data-testid="configuration-status"
        >
          {{ t(`documentTypes.edit.status.${status}`) }}
        </UBadge>
      </div>

      <UCard>
        <template #header>
          <h2 class="font-medium">
            {{ t('documentTypes.edit.details') }}
          </h2>
        </template>

        <div class="flex flex-col gap-4">
          <UFormField :label="t('documentTypes.fields.name')">
            <UInput
              v-model="name"
              class="w-full"
            />
          </UFormField>

          <UFormField :label="t('documentTypes.fields.description')">
            <UTextarea
              v-model="description"
              class="w-full"
            />
          </UFormField>

          <UFormField
            :label="t('documentTypes.edit.active')"
            :help="t('documentTypes.edit.activeHint')"
          >
            <USwitch v-model="active" />
          </UFormField>
        </div>
      </UCard>

      <!--
        Loudest control on the screen on purpose: without it the server drops
        every mapping below, and the type then reports each figure it should
        back as missing.
      -->
      <UCard :ui="{ root: status === 'unusable' ? 'ring-2 ring-error' : '' }">
        <template #header>
          <div class="flex flex-col gap-1">
            <h2 class="font-medium">
              {{ t('documentTypes.edit.reporter.title') }}
            </h2>
            <p class="text-muted text-sm">
              {{ t('documentTypes.edit.reporter.hint') }}
            </p>
          </div>
        </template>

        <div class="flex flex-col gap-4">
          <UAlert
            v-if="!draft.reporterPath"
            color="error"
            variant="soft"
            icon="i-lucide-triangle-alert"
            :title="t('documentTypes.edit.reporter.missingTitle')"
            :description="t('documentTypes.edit.reporter.missing')"
            data-testid="reporter-missing"
          />

          <UFormField
            :label="t('documentTypes.edit.reporter.path')"
            :help="t('documentTypes.edit.reporter.pathHint')"
            required
          >
            <USelect
              :model-value="selectValue(reporterPath)"
              :items="optionalFieldItems"
              class="w-full sm:w-96"
              data-testid="reporter-path"
              @update:model-value="reporterPath = toPath($event as string)"
            />
          </UFormField>

          <UFormField
            :label="t('documentTypes.edit.reporter.namePath')"
            :help="t('documentTypes.edit.reporter.nameHint')"
          >
            <USelect
              :model-value="selectValue(reporterNamePath)"
              :items="optionalFieldItems"
              class="w-full sm:w-96"
              @update:model-value="reporterNamePath = toPath($event as string)"
            />
          </UFormField>

          <UFormField
            :label="t('documentTypes.edit.period.path')"
            :help="t('documentTypes.edit.period.hint')"
          >
            <USelect
              :model-value="selectValue(periodPath)"
              :items="optionalFieldItems"
              class="w-full sm:w-96"
              data-testid="period-path"
              @update:model-value="periodPath = toPath($event as string)"
            />
          </UFormField>

          <UAlert
            v-if="!draft.periodPath"
            color="warning"
            variant="soft"
            :title="t('documentTypes.edit.period.missing')"
            data-testid="period-missing"
          />
        </div>
      </UCard>

      <UCard>
        <template #header>
          <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div class="flex flex-col gap-1">
              <h2 class="font-medium">
                {{ t('documentTypes.edit.fields.title') }}
              </h2>
              <p class="text-muted text-sm">
                {{ t('documentTypes.edit.fields.hint') }}
              </p>
              <!--
                The blocks the document is divided into, before any field is
                listed: the rows below are ordered by the exogena line they
                answer, so this is the only place the shape of the paper
                itself is visible.
              -->
              <div
                v-if="sectionNames.length"
                class="mt-1 flex flex-wrap items-center gap-1.5"
                data-testid="document-sections"
              >
                <span class="text-dimmed text-xs">{{ t('documentTypes.edit.fields.sections') }}</span>
                <UBadge
                  v-for="section in sectionNames"
                  :key="section"
                  color="neutral"
                  variant="subtle"
                  size="sm"
                >
                  {{ section }}
                </UBadge>
              </div>
            </div>
            <UFormField
              v-if="kindItems.length > 1"
              :label="t('documentTypes.edit.kind')"
            >
              <USelect
                :model-value="selectedKindId ?? undefined"
                :items="kindItems"
                class="w-full sm:w-64"
                @update:model-value="selectedKindId = $event as string"
              />
            </UFormField>
          </div>
        </template>

        <!--
          Types configured before descriptions were stored show dotted paths
          and no blocks. Re-reading the paper recovers the names without
          reopening the prompt, the schema or the mappings.
        -->
        <section
          v-if="offeredDocument && !recovered"
          class="border-default mb-6 flex flex-col gap-3 rounded-lg border p-3"
          data-testid="recover-descriptions"
        >
          <div>
            <h3 class="text-sm font-medium">
              {{ t('documentTypes.edit.recover.title') }}
            </h3>
            <p class="text-muted text-xs">
              {{ t('documentTypes.edit.recover.hint', { file: offeredDocument.fileName }) }}
            </p>
          </div>
          <UAlert
            v-if="recoveryFailed"
            color="error"
            variant="soft"
            :description="t('documentTypes.edit.recover.failed')"
          />
          <UButton
            :loading="recovering"
            :disabled="recovering"
            variant="outline"
            size="sm"
            class="w-fit"
            @click="recoverDescriptions"
          >
            {{ t('documentTypes.edit.recover.action') }}
          </UButton>
        </section>

        <UAlert
          v-if="recovered"
          class="mb-6"
          :color="recovered.named > 0 ? 'success' : 'warning'"
          variant="soft"
          data-testid="recovery-result"
          :description="recovered.named > 0
            ? t('documentTypes.edit.recover.done', recovered)
            : t('documentTypes.edit.recover.nothing')"
        />

        <section
          v-if="sampleDocument"
          class="mb-6 flex flex-col gap-2"
          data-testid="sample-document"
        >
          <div class="flex flex-wrap items-baseline justify-between gap-2">
            <h3 class="text-sm font-medium">
              {{ t('documentTypes.edit.sample.title') }}
            </h3>
            <UButton
              :to="`/documents/${sampleDocument.id}`"
              variant="link"
              size="xs"
              class="p-0"
            >
              {{ sampleDocument.fileName }}
            </UButton>
          </div>
          <p class="text-muted text-xs">
            {{ t('documentTypes.edit.sample.hint') }}
          </p>
          <DocumentViewer
            :drive-file-id="sampleDocument.driveFileId"
            :mime-type="sampleDocument.mimeType"
            :file-name="sampleDocument.fileName"
          />
        </section>

        <p
          v-if="!selections.length"
          class="text-muted text-sm"
        >
          {{ t('documentTypes.edit.fields.empty') }}
        </p>

        <div
          v-else
          class="flex flex-col gap-6"
          data-testid="field-rows"
        >
          <section
            v-for="group in groups"
            :key="group.spineConceptId ?? '__unanswered__'"
            class="flex flex-col gap-3"
          >
            <!--
              The heading is the line of the exogena, not the document: every
              field under it is added up before the comparison, and a flat list
              of fields would never let that be discovered.
            -->
            <div class="bg-elevated/50 flex flex-col gap-1 rounded-lg px-3 py-2">
              <p class="text-highlighted text-sm font-medium">
                {{ group.spineConceptId
                  ? spineConcept(group.spineConceptId)?.label ?? group.spineConceptId
                  : t('documentTypes.edit.fields.noSpineGroup') }}
              </p>
              <p
                v-if="group.spineConceptId && spineConcept(group.spineConceptId)?.description"
                class="text-muted text-xs"
              >
                {{ spineConcept(group.spineConceptId)?.description }}
              </p>
              <p
                v-if="group.summed"
                class="text-primary text-xs"
                data-testid="summed-note"
              >
                {{ t('documentTypes.edit.fields.summed', { count: group.paths.length }) }}
              </p>
              <p
                v-else
                class="text-muted text-xs"
              >
                {{ group.spineConceptId
                  ? t('documentTypes.edit.fields.single')
                  : t('documentTypes.edit.fields.noSpineGroupHint') }}
              </p>
              <p
                v-if="group.mixedComparison"
                class="text-warning text-xs"
                data-testid="mixed-comparison"
              >
                {{ t('documentTypes.edit.fields.mixedComparison') }}
              </p>
            </div>

            <div
              v-for="index in group.indices"
              :key="selections[index]!.path"
              class="border-default flex flex-col gap-3 rounded-lg border p-3"
              :class="selections[index]!.kept ? '' : 'opacity-60'"
            >
              <div class="flex items-start gap-3">
                <UCheckbox
                  v-model="selections[index]!.kept"
                  :aria-label="t('documentTypes.edit.fields.keep')"
                  class="mt-1"
                />

                <div class="min-w-0">
                  <UBadge
                    v-if="fieldSection(selections[index]!.path)"
                    color="neutral"
                    variant="subtle"
                    size="sm"
                    class="mb-1"
                    data-testid="field-section"
                  >
                    {{ fieldSection(selections[index]!.path) }}
                  </UBadge>
                  <p
                    class="text-sm font-medium"
                    :class="selections[index]!.kept ? 'text-highlighted' : 'text-muted line-through'"
                  >
                    {{ fieldName(selections[index]!.path) }}
                  </p>
                  <p
                    v-if="descriptionByPath.get(selections[index]!.path)"
                    class="text-muted text-xs"
                  >
                    {{ descriptionByPath.get(selections[index]!.path) }}
                  </p>
                  <p class="text-dimmed break-all font-mono text-xs">
                    {{ selections[index]!.path }}
                  </p>
                  <p
                    v-if="!selections[index]!.kept"
                    class="text-warning text-xs"
                  >
                    {{ t('documentTypes.edit.fields.removed') }}
                  </p>
                </div>
              </div>

              <div class="grid gap-3 sm:grid-cols-2 sm:pl-8">
                <UFormField
                  :label="t('documentTypes.edit.fields.conceptQuestion')"
                  :help="t('documentTypes.edit.fields.conceptHint')"
                >
                  <USelect
                    :model-value="selections[index]!.conceptId ?? UNMAPPED"
                    :items="conceptItems"
                    :disabled="!selections[index]!.kept"
                    class="w-full"
                    @update:model-value="selections[index]!.conceptId = toPath($event as string)"
                  />
                </UFormField>

                <UFormField
                  :label="t('documentTypes.edit.fields.spineQuestion')"
                  :help="t('documentTypes.edit.fields.spineHint')"
                >
                  <USelect
                    :model-value="selections[index]!.spineConceptId ?? UNMAPPED"
                    :items="spineItems"
                    :disabled="!selections[index]!.kept || !selections[index]!.conceptId"
                    class="w-full"
                    @update:model-value="selections[index]!.spineConceptId = toPath($event as string)"
                  />
                </UFormField>
              </div>

              <div
                v-if="selections[index]!.kept && selections[index]!.conceptId && selections[index]!.spineConceptId"
                class="flex flex-col gap-3 sm:pl-8"
              >
                <UFormField :label="t('documentTypes.edit.fields.comparison.question')">
                  <URadioGroup
                    :model-value="selections[index]!.perAccount ? 'perAccount' : 'total'"
                    :items="comparisonItems"
                    @update:model-value="selections[index]!.perAccount = $event === 'perAccount'"
                  />
                </UFormField>

                <UFormField
                  v-if="selections[index]!.perAccount"
                  :label="t('documentTypes.edit.fields.accountPath')"
                  :help="t('documentTypes.edit.fields.accountPathHint')"
                >
                  <USelect
                    :model-value="selectValue(selections[index]!.accountPath)"
                    :items="optionalFieldItems"
                    class="w-full sm:w-96"
                    @update:model-value="selections[index]!.accountPath = toPath($event as string)"
                  />
                </UFormField>

                <UAlert
                  v-if="selections[index]!.perAccount && !selections[index]!.accountPath"
                  color="warning"
                  variant="soft"
                  icon="i-lucide-triangle-alert"
                  data-testid="account-path-missing"
                  :title="t('documentTypes.edit.fields.accountPathMissing')"
                />
              </div>
            </div>
          </section>
        </div>

        <p
          v-if="missingAccountPaths.length > 0"
          class="text-warning mt-3 text-sm"
          data-testid="account-path-warning"
        >
          {{ t(
            'documentTypes.edit.fields.accountPathMissingCount',
            { count: missingAccountPaths.length },
            missingAccountPaths.length
          ) }}
        </p>

        <p
          v-if="removedCount > 0"
          class="text-warning mt-3 text-sm"
          data-testid="removed-count"
        >
          {{ t('documentTypes.edit.fields.removedCount', { count: removedCount }, removedCount) }}
        </p>
      </UCard>

      <UAlert
        v-if="status === 'notMapped'"
        color="neutral"
        variant="soft"
        :title="t('documentTypes.edit.status.notMapped')"
        :description="t('documentTypes.edit.status.notMappedHint')"
      />

      <section
        v-if="mappingChanges.length > 0"
        class="flex flex-col gap-2"
        data-testid="mapping-changes"
      >
        <h2 class="font-medium">
          {{ t('documentTypes.edit.mappingChanges.title') }}
        </h2>
        <UAlert
          v-for="(change, index) in mappingChanges"
          :key="`${change.change}-${index}`"
          :color="mappingChangeSeverity(change) === 'critical' ? 'error' : 'warning'"
          variant="soft"
          :title="mappingChangeText(change)"
          :description="change.reason"
        />
      </section>

      <div class="flex flex-col gap-3">
        <UAlert
          v-if="saveFailed"
          color="error"
          :title="t('documentTypes.edit.saveError')"
        />
        <UAlert
          v-else-if="typeSavedWithoutMapping"
          color="warning"
          variant="subtle"
          icon="i-lucide-triangle-alert"
          data-testid="save-partial"
          :title="t('documentTypes.edit.savePartialTitle')"
          :description="t('documentTypes.edit.savePartialDescription')"
        />
        <UAlert
          v-else-if="saved"
          color="success"
          variant="soft"
          :title="t('documentTypes.edit.saved')"
        />

        <div class="flex flex-wrap items-center gap-3">
          <UButton
            :loading="saving"
            :disabled="!canSave"
            data-testid="save-document-type"
            @click="save"
          >
            {{ t('documentTypes.edit.save') }}
          </UButton>
          <UButton
            to="/document-types"
            color="neutral"
            variant="soft"
          >
            {{ t('documentTypes.edit.back') }}
          </UButton>
          <p
            v-if="!isDraftSavable(draft)"
            class="text-error text-sm"
          >
            {{ t('documentTypes.edit.reporter.blocksSave') }}
          </p>
        </div>
      </div>
    </div>
  </UContainer>
</template>
