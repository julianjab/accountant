<script setup lang="ts">
import type { MappingChange } from '~/domain/entities/concept-mapping'
import type { DocumentType } from '~/domain/entities/document-type'
import type { DocumentTypeProposal } from '~/domain/entities/document-type-proposal'
import type { ProposalFieldRow } from '~/domain/document-type-configuration'
import {
  buildProposalRows,
  creationBlock,
  groupBySection,
  invalidTaxYears,
  keptPaths,
  mappingChangeSeverity,
  parseTaxYears,
  proposalMappingBaseline,
  toDocumentTypeFields,
  toMappingDraft,
  toProposedFieldMappings
} from '~/domain/document-type-configuration'
import { listSchemaFields, pruneSchema } from '~/domain/extraction-schema'

type Step = 'form' | 'analyzing' | 'select' | 'created'

const { t } = useI18n()
const proposeDocumentType = useProposeDocumentTypeUseCase()
const createDocumentType = useCreateDocumentTypeUseCase()

// A select cannot hold null, so "no field" travels as a sentinel and is
// translated back at the edge — the same convention the edit screen uses.
const UNSET = '__unset__'

// Prefilled when arriving from a client's missing-document row, which already
// knows who issues the certificate — the part hardest to type correctly.
const route = useRoute()
function queryText(key: string): string {
  const value = route.query[key]
  return typeof value === 'string' ? value : ''
}

const issuer = computed(() => queryText('issuer'))
const claim = computed(() => queryText('claim'))
/** The document the sample was taken from, so the type remembers the paper it
 * came from; empty when the flow was started from the types list. */
const sampleDocumentId = computed(() => queryText('document'))

const name = ref(issuer.value)
const description = ref(
  issuer.value
    ? t(claim.value ? 'documentTypes.new.claimDescription' : 'documentTypes.new.issuerDescription', {
        issuer: issuer.value,
        claim: claim.value
      })
    : ''
)
const sampleFile = ref<File | null>(null)

const step = ref<Step>('form')
const analyzing = computed(() => step.value === 'analyzing')
const analysisFailed = ref(false)

const proposal = ref<DocumentTypeProposal | null>(null)
const rows = ref<ProposalFieldRow[]>([])
const reporterPath = ref<string | null>(null)
const reporterNamePath = ref<string | null>(null)
const periodPath = ref<string | null>(null)
const taxYearsText = ref('')

const saving = ref(false)
const saveFailed = ref(false)
const createdType = ref<DocumentType | null>(null)
const mappingChanges = ref<MappingChange[]>([])

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  sampleFile.value = input.files?.[0] ?? null
}

async function analyze() {
  if (analyzing.value || !sampleFile.value) return

  step.value = 'analyzing'
  analysisFailed.value = false

  try {
    const proposed = await proposeDocumentType.execute({
      name: name.value,
      sampleFile: sampleFile.value
    })
    proposal.value = proposed
    rows.value = buildProposalRows(proposed, listSchemaFields(proposed.extractionSchema))
    reporterPath.value = proposed.reporterPath
    reporterNamePath.value = proposed.reporterNamePath
    periodPath.value = proposed.periodPath
    step.value = 'select'
  } catch {
    analysisFailed.value = true
    step.value = 'form'
  }
}

function startOver() {
  proposal.value = null
  rows.value = []
  step.value = 'form'
}

const draft = computed(() =>
  toMappingDraft(
    rows.value,
    {
      reporterPath: reporterPath.value,
      reporterNamePath: reporterNamePath.value,
      periodPath: periodPath.value
    },
    // The proposal is the baseline rather than a stored mapping: it carries the
    // signs and account paths this screen has no control for.
    proposal.value ? proposalMappingBaseline(proposal.value) : null
  )
)

const blocked = computed(() => creationBlock(rows.value, draft.value))
const canSave = computed(() => !saving.value && blocked.value === null && invalidYears.value.length === 0)

const keptCount = computed(() => keptPaths(rows.value).size)

const rowByPath = computed(() => new Map(rows.value.map(row => [row.path, row])))

const sections = computed(() =>
  groupBySection(rows.value).map(group => ({
    ...group,
    // The group is a domain answer about paths; the rows it is rendered with
    // are a rendering detail, resolved once here instead of in the template.
    rows: group.paths.map(path => rowByPath.value.get(path)).filter(row => row !== undefined)
  }))
)

function setSection(paths: readonly string[], kept: boolean) {
  const target = new Set(paths)
  for (const row of rows.value) {
    if (target.has(row.path)) row.kept = kept
  }
}

/** Only fields that survive the trimming can play a role: pointing the
 * reporting party at a field about to be dropped is the failure, not a
 * choice. */
const keptFieldItems = computed(() => [
  { label: t('documentTypes.edit.fields.unsetField'), value: UNSET },
  ...rows.value
    .filter(row => row.kept)
    .map(row => ({ label: row.label, value: row.path, description: row.path }))
])

const proposedReporterRow = computed(() =>
  proposal.value?.reporterPath ? rowByPath.value.get(proposal.value.reporterPath) ?? null : null
)

const invalidYears = computed(() => invalidTaxYears(taxYearsText.value))

function selectValue(path: string | null): string {
  return path ?? UNSET
}

function toPath(value: string): string | null {
  return value === UNSET ? null : value
}

const KNOWN_CHANGES = ['entry_dropped', 'path_cleared', 'mapping_cleared', 'prune_failed']

function mappingChangeText(change: MappingChange): string {
  const key = KNOWN_CHANGES.includes(change.change) ? change.change : 'unknown'
  return t(`documentTypes.edit.mappingChanges.${key}`, {
    change: change.change,
    path: change.path ?? change.fieldPath ?? '—',
    field: change.fieldPath ?? change.path ?? '—',
    concept: change.conceptId ?? '—'
  })
}

async function save() {
  if (!canSave.value || !proposal.value) return

  saving.value = true
  saveFailed.value = false

  try {
    const created = await createDocumentType.execute({
      name: name.value,
      description: description.value,
      extractionPrompt: proposal.value.extractionPrompt,
      // Sent already trimmed: the create endpoint stores exactly what it gets,
      // so what is not pruned here is what every future document is asked for.
      extractionSchema: pruneSchema(proposal.value.extractionSchema, keptPaths(rows.value)),
      fieldMappings: toProposedFieldMappings(draft.value),
      // Sent alongside the schema so the type remembers what the document calls
      // each field and which block it sits in — the sections the user just
      // chose by would otherwise be gone as soon as this screen is left.
      fields: toDocumentTypeFields(rows.value),
      reporterPath: draft.value.reporterPath,
      reporterNamePath: draft.value.reporterNamePath,
      periodPath: draft.value.periodPath,
      taxYears: parseTaxYears(taxYearsText.value),
      kindId: proposal.value.kindId,
      sampleDocumentId: sampleDocumentId.value || null
    })
    createdType.value = created.documentType
    mappingChanges.value = created.mappingChanges
    step.value = 'created'
  } catch {
    saveFailed.value = true
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <UContainer class="py-6 sm:py-8">
    <h1 class="mb-1 text-xl font-semibold">
      {{ t('documentTypes.new.title') }}
    </h1>
    <p class="text-muted mb-4 text-sm">
      {{ t('documentTypes.new.nothingSaved') }}
    </p>

    <UAlert
      v-if="analysisFailed"
      color="error"
      class="mb-4"
      :title="t('documentTypes.new.error')"
    />

    <form
      v-if="step === 'form'"
      class="flex max-w-xl flex-col gap-4"
      @submit.prevent="analyze"
    >
      <UFormField
        :label="t('documentTypes.fields.name')"
        required
      >
        <UInput
          v-model="name"
          required
          class="w-full"
        />
      </UFormField>

      <UFormField
        :label="t('documentTypes.fields.description')"
        required
      >
        <UTextarea
          v-model="description"
          required
          class="w-full"
        />
      </UFormField>

      <UFormField
        :label="t('documentTypes.fields.sampleFile')"
        :help="t('documentTypes.new.sampleFileHint')"
        required
      >
        <input
          type="file"
          accept="application/pdf,image/png,image/jpeg,image/webp,image/gif"
          required
          class="max-w-full text-[13px] text-toned"
          @change="onFileChange"
        >
      </UFormField>

      <UButton
        type="submit"
        :loading="analyzing"
        :disabled="analyzing"
        block
        class="sm:w-fit"
      >
        {{ t('documentTypes.new.submit') }}
      </UButton>
    </form>

    <div
      v-else-if="step === 'analyzing'"
      class="flex flex-col items-center gap-3 py-16 text-center"
    >
      <UIcon
        name="i-lucide-loader-circle"
        class="text-primary size-8 animate-spin"
      />
      <p class="font-medium">
        {{ t('documentTypes.new.loading') }}
      </p>
      <p class="text-muted text-sm">
        {{ t('documentTypes.new.loadingHint') }}
      </p>
    </div>

    <div
      v-else-if="step === 'select' && proposal"
      class="flex flex-col gap-6"
    >
      <!--
        Loudest control on the screen on purpose: without it the server drops
        every mapping this type carries, and the type then reports each figure
        it should back as missing.
      -->
      <UCard :ui="{ root: blocked === 'noReporter' ? 'ring-2 ring-error' : '' }">
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
            v-if="proposedReporterRow"
            color="warning"
            variant="soft"
            icon="i-lucide-badge-check"
            data-testid="reporter-proposed"
            :title="t('documentTypes.new.reporterProposed', {
              field: proposedReporterRow.label,
              value: proposedReporterRow.sampleValue || '—'
            })"
            :description="t('documentTypes.edit.reporter.pathHint')"
          />
          <UAlert
            v-else
            color="error"
            variant="soft"
            icon="i-lucide-triangle-alert"
            data-testid="reporter-not-proposed"
            :title="t('documentTypes.new.reporterNotProposed')"
            :description="t('documentTypes.edit.reporter.missing')"
          />

          <UFormField
            :label="t('documentTypes.edit.reporter.path')"
            :help="t('documentTypes.edit.reporter.pathHint')"
            required
          >
            <USelect
              :model-value="selectValue(reporterPath)"
              :items="keptFieldItems"
              class="w-full sm:w-96"
              data-testid="reporter-path"
              @update:model-value="reporterPath = toPath($event as string)"
            />
          </UFormField>

          <UAlert
            v-if="blocked === 'noReporter'"
            color="error"
            variant="soft"
            icon="i-lucide-triangle-alert"
            data-testid="reporter-missing"
            :title="t('documentTypes.edit.reporter.missingTitle')"
            :description="t('documentTypes.edit.reporter.missing')"
          />

          <UFormField
            :label="t('documentTypes.edit.reporter.namePath')"
            :help="t('documentTypes.edit.reporter.nameHint')"
          >
            <USelect
              :model-value="selectValue(reporterNamePath)"
              :items="keptFieldItems"
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
              :items="keptFieldItems"
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
          />
        </div>
      </UCard>

      <UCard>
        <template #header>
          <div class="flex flex-col gap-1">
            <h2 class="font-medium">
              {{ t('documentTypes.new.select.title') }}
            </h2>
            <p class="text-muted text-sm">
              {{ t('documentTypes.new.select.hint') }}
            </p>
          </div>
        </template>

        <p
          v-if="!rows.length"
          class="text-muted text-sm"
        >
          {{ t('documentTypes.new.select.empty') }}
        </p>

        <div
          v-else
          class="flex flex-col gap-6"
          data-testid="proposal-sections"
        >
          <section
            v-for="section in sections"
            :key="section.section ?? '__headless__'"
            class="flex flex-col gap-2"
          >
            <div class="bg-elevated/50 flex flex-wrap items-center justify-between gap-2 rounded-lg px-3 py-2">
              <div class="min-w-0">
                <p class="text-highlighted text-sm font-medium">
                  {{ section.section ?? t('documentTypes.new.select.otherSection') }}
                </p>
                <p class="text-muted text-xs">
                  {{ t('documentTypes.new.select.sectionCount', {
                    kept: section.keptCount,
                    total: section.paths.length
                  }) }}
                </p>
              </div>
              <div class="flex shrink-0 gap-1">
                <UButton
                  size="xs"
                  color="neutral"
                  variant="ghost"
                  @click="setSection(section.paths, true)"
                >
                  {{ t('documentTypes.new.select.all') }}
                </UButton>
                <UButton
                  size="xs"
                  color="neutral"
                  variant="ghost"
                  @click="setSection(section.paths, false)"
                >
                  {{ t('documentTypes.new.select.none') }}
                </UButton>
              </div>
            </div>

            <label
              v-for="row in section.rows"
              :key="row.path"
              class="border-default flex items-start gap-3 rounded-lg border p-3 transition-colors duration-[120ms] hover:bg-elevated/60"
              :class="row.kept ? '' : 'opacity-60'"
            >
              <UCheckbox
                v-model="row.kept"
                :aria-label="t('documentTypes.new.select.keep')"
                class="mt-0.5"
              />
              <div class="min-w-0 flex-1">
                <div class="flex flex-wrap items-center gap-2">
                  <p
                    class="text-sm font-medium"
                    :class="row.kept ? 'text-highlighted' : 'text-muted'"
                  >
                    {{ row.label }}
                  </p>
                  <UBadge
                    size="sm"
                    variant="subtle"
                    :color="row.role === 'amount' ? 'primary' : row.role === 'identifier' ? 'success' : 'neutral'"
                  >
                    {{ t(`documentTypes.new.select.role.${row.role}`) }}
                  </UBadge>
                </div>
                <p
                  v-if="row.sampleValue"
                  class="text-toned text-[13px]"
                >
                  {{ t('documentTypes.new.select.sampleValue', { value: row.sampleValue }) }}
                </p>
                <p class="text-dimmed break-all font-mono text-xs">
                  {{ row.path }}
                </p>
              </div>
            </label>
          </section>
        </div>

        <p
          class="text-muted mt-4 text-sm"
          data-testid="kept-summary"
        >
          {{ t('documentTypes.new.select.keptSummary', { kept: keptCount, total: rows.length }) }}
        </p>
      </UCard>

      <UCard>
        <template #header>
          <h2 class="font-medium">
            {{ t('documentTypes.new.taxYears.title') }}
          </h2>
        </template>

        <UFormField
          :label="t('documentTypes.new.taxYears.label')"
          :help="t('documentTypes.new.taxYears.hint')"
        >
          <UInput
            v-model="taxYearsText"
            :placeholder="t('documentTypes.new.taxYears.placeholder')"
            class="w-full sm:w-96"
            data-testid="tax-years"
          />
        </UFormField>
        <p
          v-if="invalidYears.length"
          class="text-error mt-2 text-sm"
          data-testid="tax-years-invalid"
        >
          {{ t('documentTypes.new.taxYears.invalid', { years: invalidYears.join(', ') }) }}
        </p>
      </UCard>

      <div class="flex flex-col gap-3">
        <UAlert
          v-if="saveFailed"
          color="error"
          :title="t('documentTypes.new.createError')"
        />

        <div class="flex flex-wrap items-center gap-3">
          <UButton
            :loading="saving"
            :disabled="!canSave"
            data-testid="create-document-type"
            @click="save"
          >
            {{ t('documentTypes.new.save') }}
          </UButton>
          <UButton
            color="neutral"
            variant="soft"
            @click="startOver"
          >
            {{ t('documentTypes.new.startOver') }}
          </UButton>
          <p
            v-if="blocked === 'noReporter'"
            class="text-error text-sm"
          >
            {{ t('documentTypes.edit.reporter.blocksSave') }}
          </p>
          <p
            v-else-if="blocked === 'noFields'"
            class="text-error text-sm"
            data-testid="no-fields"
          >
            {{ t('documentTypes.new.blocked.noFields') }}
          </p>
        </div>
      </div>
    </div>

    <div
      v-else-if="step === 'created' && createdType"
      class="flex flex-col gap-4"
    >
      <UAlert
        color="success"
        variant="soft"
        icon="i-lucide-check"
        :title="t('documentTypes.new.created.title', { name: createdType.name })"
        :description="t('documentTypes.new.created.hint')"
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

      <div class="flex flex-wrap gap-3">
        <UButton :to="`/document-types/${createdType.id}`">
          {{ t('documentTypes.new.created.configure') }}
        </UButton>
        <UButton
          to="/document-types"
          color="neutral"
          variant="soft"
        >
          {{ t('documentTypes.new.created.list') }}
        </UButton>
      </div>
    </div>
  </UContainer>
</template>
