<script setup lang="ts">
import type { ConceptMapping, MappingChange } from '~/domain/entities/concept-mapping'
import type { DocumentType } from '~/domain/entities/document-type'
import type { ReconciliationKind } from '~/domain/entities/reconciliation-kind'
import type { FieldSelection } from '~/domain/document-type-configuration'
import {
  buildFieldSelections,
  configurationStatus,
  isDraftSavable,
  keptPaths,
  mappingChangeSeverity,
  shouldSaveDraft,
  toMappingDraft
} from '~/domain/document-type-configuration'
import { listSchemaFields, pruneSchema } from '~/domain/extraction-schema'

const { t } = useI18n()
const route = useRoute()
const documentTypeId = route.params.id as string

const getDocumentType = useGetDocumentTypeUseCase()
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

const kindItems = computed(() => kinds.value.map(kind => ({ label: kind.label, value: kind.id })))

function conceptLabel(conceptId: string): string {
  const concept = selectedKind.value?.evidenceConcepts.find(candidate => candidate.id === conceptId)
  return concept?.label ?? conceptId
}

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

        <p
          v-if="!selections.length"
          class="text-muted text-sm"
        >
          {{ t('documentTypes.edit.fields.empty') }}
        </p>

        <ul
          v-else
          class="divide-default divide-y"
          data-testid="field-rows"
        >
          <li
            v-for="(selection, index) in selections"
            :key="selection.path"
            class="grid grid-cols-[auto_1fr] items-start gap-x-3 gap-y-2 py-3 sm:grid-cols-[auto_1fr_18rem]"
          >
            <UCheckbox
              v-model="selections[index]!.kept"
              :aria-label="t('documentTypes.edit.fields.keep')"
              class="mt-1"
            />

            <div class="min-w-0">
              <p
                class="break-all font-mono text-sm"
                :class="selection.kept ? 'text-highlighted' : 'text-muted line-through'"
              >
                {{ selection.path }}
              </p>
              <p
                v-if="descriptionByPath.get(selection.path)"
                class="text-muted text-xs"
              >
                {{ descriptionByPath.get(selection.path) }}
              </p>
              <p
                v-if="!selection.kept"
                class="text-warning text-xs"
              >
                {{ t('documentTypes.edit.fields.removed') }}
              </p>
            </div>

            <div class="col-span-2 sm:col-span-1">
              <USelect
                :model-value="selection.conceptId ?? UNMAPPED"
                :items="conceptItems"
                :disabled="!selection.kept"
                class="w-full"
                :aria-label="t('documentTypes.edit.fields.concept')"
                @update:model-value="selections[index]!.conceptId = toPath($event as string)"
              />
            </div>
          </li>
        </ul>

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
