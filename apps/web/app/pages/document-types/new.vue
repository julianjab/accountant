<script setup lang="ts">
import type { DocumentType } from '~/domain/entities/document-type'
import type { ClientDocument } from '~/domain/entities/document'
import type { DocumentTypeProposal, UnmappedField } from '~/domain/entities/document-type-proposal'
import type { ProposalFieldRow } from '~/domain/document-type-configuration'
import {
  buildProposalRows,
  creationBlock,
  invalidTaxYears,
  keptPaths,
  parseTaxYears,
  proposalMappingBaseline,
  readSource,
  toDocumentTypeFields,
  toMappingDraft,
  toProposedFieldMappings,
  writeSource
} from '~/domain/document-type-configuration'
import type { SectionNotes } from '~/domain/proposal-loop'
import { carryChoices, toFieldSelection } from '~/domain/proposal-loop'
import { listSchemaFields, pruneSchema } from '~/domain/extraction-schema'
import DocumentViewer from '~/components/documents/DocumentViewer.vue'
import ProposalFieldPicker from '~/components/document-types/ProposalFieldPicker.vue'

type Step = 'form' | 'analyzing' | 'select' | 'created'

const { t } = useI18n()
const proposeDocumentType = useProposeDocumentTypeUseCase()
const getDocument = useGetDocumentUseCase()
const createDocumentType = useCreateDocumentTypeUseCase()

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
// Declared values, for the papers that never state them. Empty string rather
// than null so they can be bound straight to a text input.
const reporterTaxId = ref<string | null>(null)
const reporterName = ref<string | null>(null)
const declaredPeriod = ref<string | null>(null)

/**
 * Every path this document offers, for the one box that answers "where does
 * this come from" — pick a field, or type the value yourself.
 *
 * Built from the kept fields themselves, not from the select items: those
 * lead with a "no field" sentinel, which as a suggestion reads like a field
 * of the document and, chosen, stores a path nothing can ever resolve. On the
 * reporting party that is worse than leaving it blank — the screen counts it
 * as answered and the type is created attributing its figures to nobody.
 */
const pathSuggestions = computed(() =>
  rows.value.filter(row => row.kept).map(row => row.path)
)

function applySource(
  answer: string,
  path: Ref<string | null>,
  value: Ref<string | null>
) {
  const read = readSource(answer, pathSuggestions.value)
  path.value = read.path
  value.value = read.value
}

const setReporter = (answer: string) => applySource(answer, reporterPath, reporterTaxId)
const setReporterName = (answer: string) => applySource(answer, reporterNamePath, reporterName)
const setPeriod = (answer: string) => applySource(answer, periodPath, declaredPeriod)
const taxYearsText = ref('')

const saving = ref(false)
const saveFailed = ref(false)
const createdType = ref<DocumentType | null>(null)
/** Fields this type will extract but never reconcile, as the server
 * reported them when it saved the type. */
const unmappedFields = ref<UnmappedField[]>([])

/**
 * The uploaded sample, as something the browser can render.
 *
 * A sample picked from Drive is shown through its Drive preview, but an
 * uploaded one never reaches the server as anything durable — so there was
 * nothing to show, at the one step where the fields are chosen by reading
 * them against the paper. The bytes are already in the page; this just points
 * at them.
 */
const uploadedPreview = ref<string | null>(null)

function releaseUploadedPreview() {
  if (uploadedPreview.value) URL.revokeObjectURL(uploadedPreview.value)
  uploadedPreview.value = null
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  releaseUploadedPreview()
  sampleFile.value = input.files?.[0] ?? null
  if (sampleFile.value) uploadedPreview.value = URL.createObjectURL(sampleFile.value)
}

// Revoked on the way out: an object URL pins the whole file in memory until
// it is, and this page can be left with a scanned PDF loaded.
onBeforeUnmount(releaseUploadedPreview)

const uploadedIsImage = computed(() => sampleFile.value?.type.startsWith('image/') ?? false)
const uploadedIsPdf = computed(() => sampleFile.value?.type === 'application/pdf')

/**
 * The document named in the URL, when the flow was started from one.
 *
 * Loaded so the sample can be shown while its fields are chosen, and so the
 * name of the paper is on screen rather than an opaque id.
 */
const { data: sampleDocument } = await useAsyncData<ClientDocument | null>(
  `document-type-new-sample-${sampleDocumentId.value || 'none'}`,
  () =>
    sampleDocumentId.value
      ? getDocument.execute(sampleDocumentId.value)
      : Promise.resolve(null),
  { server: false, default: () => null }
)

/** Either a document already in Drive or a file from this machine names the
 * sample; without one there is nothing to read. */
const canAnalyze = computed(() => Boolean(sampleDocumentId.value || sampleFile.value))

/** What the person says this reading got wrong, for the next one. */
const guidance = ref('')

/**
 * What they said about whole blocks of the page.
 *
 * Kept on the screen rather than on the rows: a block outlives the fields any
 * one reading proposes under it, so an instruction about the obligations table
 * survives a round that read that table differently.
 */
const sectionNotes = ref<SectionNotes>({})

function annotateSection(section: string, note: string) {
  sectionNotes.value = { ...sectionNotes.value, [section]: note }
}
const rereading = ref(false)

async function analyze() {
  if (analyzing.value || !canAnalyze.value) return

  step.value = 'analyzing'
  analysisFailed.value = false

  try {
    await read()
    step.value = 'select'
  } catch {
    analysisFailed.value = true
    step.value = 'form'
  }
}

/**
 * Reads the paper again with the answers to the last reading in hand.
 *
 * The loop, and the reason the first proposal does not have to be right: what
 * was ticked, renamed and annotated goes back as the instruction, so a round
 * converges on the handful of fields this office actually wants instead of
 * re-offering the twenty that were just refused.
 *
 * Stays on the select step while it runs rather than returning to the form —
 * the paper, the choices and the guidance are all still on screen, and losing
 * them to a spinner is losing the work being iterated on.
 */
async function reread() {
  if (rereading.value || !canAnalyze.value) return

  rereading.value = true
  analysisFailed.value = false
  try {
    await read()
    guidance.value = ''
  } catch {
    analysisFailed.value = true
  } finally {
    rereading.value = false
  }
}

async function read() {
  const previous = rows.value
  const proposed = await proposeDocumentType.execute({
    name: name.value,
    // A stored document wins: it is the one the saved type can point back at.
    documentId: sampleDocumentId.value || null,
    sampleFile: sampleFile.value,
    guidance: guidance.value,
    // Empty on the first reading, which has no answer behind it yet.
    selection: previous.length ? toFieldSelection(previous, sectionNotes.value) : null
  })
  proposal.value = proposed
  rows.value = carryChoices(
    buildProposalRows(proposed, listSchemaFields(proposed.extractionSchema)),
    previous
  )
  reporterPath.value = proposed.reporterPath
  reporterNamePath.value = proposed.reporterNamePath
  periodPath.value = proposed.periodPath
}

function startOver() {
  proposal.value = null
  rows.value = []
  guidance.value = ''
  sectionNotes.value = {}
  step.value = 'form'
}

const draft = computed(() =>
  toMappingDraft(
    rows.value,
    {
      reporterPath: reporterPath.value,
      reporterNamePath: reporterNamePath.value,
      periodPath: periodPath.value,
      reporterTaxId: reporterTaxId.value,
      reporterName: reporterName.value,
      period: declaredPeriod.value
    },
    // The proposal is the baseline rather than a stored mapping: it carries the
    // signs and account paths this screen has no control for.
    proposal.value ? proposalMappingBaseline(proposal.value) : null
  )
)

const blocked = computed(() => creationBlock(rows.value, draft.value))
const canSave = computed(() => !saving.value && blocked.value === null && invalidYears.value.length === 0)

const rowByPath = computed(() => new Map(rows.value.map(row => [row.path, row])))

/** Only fields that survive the trimming can play a role: pointing the
 * reporting party at a field about to be dropped is the failure, not a
 * choice. */

const proposedReporterRow = computed(() =>
  proposal.value?.reporterPath ? rowByPath.value.get(proposal.value.reporterPath) ?? null : null
)

const invalidYears = computed(() => invalidTaxYears(taxYearsText.value))

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
      // Taken from the draft, which already blanked the empty inputs. Left out,
      // a type whose issuer is only declared reaches the server naming nobody
      // and has every one of its mappings discarded.
      reporterTaxId: draft.value.reporterTaxId,
      reporterName: draft.value.reporterName,
      period: draft.value.period,
      taxYears: parseTaxYears(taxYearsText.value),
      kindId: proposal.value.kindId,
      sampleDocumentId: sampleDocumentId.value || null
    })
    createdType.value = created.documentType
    unmappedFields.value = created.unmappedFields
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

    <!--
      The paper on the right, at every step. Naming the type, waiting on the
      analysis and choosing the fields are all done by reading the document,
      so it never leaves the screen while the column beside it changes.
    -->
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] lg:items-start">
      <div class="flex min-w-0 flex-col gap-6">
        <form
          v-if="step === 'form'"
          class="flex flex-col gap-4"
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

          <!--
        Started from a document, so there is nothing to upload: that paper is
        the sample, and the type will keep pointing at it.
      -->
          <UFormField
            v-if="sampleDocument"
            :label="t('documentTypes.fields.sampleFile')"
            :help="t('documentTypes.new.sampleDocumentHint')"
          >
            <UButton
              :to="`/documents/${sampleDocument.id}`"
              variant="link"
              size="xs"
              class="w-fit p-0"
            >
              {{ sampleDocument.fileName }}
            </UButton>
          </UFormField>

          <UFormField
            v-else
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
            :disabled="analyzing || !canAnalyze"
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
                :help="t('documentTypes.edit.reporter.sourceHint')"
                required
              >
                <UInputMenu
                  :model-value="writeSource(reporterPath, reporterTaxId)"
                  :items="pathSuggestions"
                  create-item
                  class="w-full sm:w-96"
                  data-testid="reporter-path"
                  :placeholder="t('documentTypes.edit.reporter.sourcePlaceholder')"
                  @update:model-value="setReporter($event as string)"
                  @create="setReporter($event as string)"
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
                :help="t('documentTypes.edit.reporter.nameSourceHint')"
              >
                <UInputMenu
                  :model-value="writeSource(reporterNamePath, reporterName)"
                  :items="pathSuggestions"
                  create-item
                  class="w-full sm:w-96"
                  data-testid="reporter-name-path"
                  :placeholder="t('documentTypes.edit.reporter.nameSourcePlaceholder')"
                  @update:model-value="setReporterName($event as string)"
                  @create="setReporterName($event as string)"
                />
              </UFormField>

              <UFormField
                :label="t('documentTypes.edit.period.path')"
                :help="t('documentTypes.edit.period.sourceHint')"
              >
                <UInputMenu
                  :model-value="writeSource(periodPath, declaredPeriod)"
                  :items="pathSuggestions"
                  create-item
                  class="w-full sm:w-96"
                  data-testid="period-path"
                  :placeholder="t('documentTypes.edit.period.sourcePlaceholder')"
                  @update:model-value="setPeriod($event as string)"
                  @create="setPeriod($event as string)"
                />
              </UFormField>

              <UAlert
                v-if="!draft.periodPath && !draft.period"
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

            <ProposalFieldPicker
              v-else
              :rows="rows"
              :section-notes="sectionNotes"
              @annotate="annotateSection"
            />

            <!--
              The loop. A first reading is an offer, and what was just ticked,
              renamed and annotated is a better instruction for the next one
              than the document alone — so the answer goes back rather than
              being spent on a one-way create.
            -->
            <template #footer>
              <UFormField
                :label="t('documentTypes.reread.guidance')"
                :help="t('documentTypes.reread.hint')"
              >
                <UTextarea
                  v-model="guidance"
                  :rows="2"
                  class="w-full"
                  data-testid="reread-guidance"
                  :placeholder="t('documentTypes.reread.placeholder')"
                />
              </UFormField>
              <UButton
                class="mt-3"
                variant="outline"
                icon="i-lucide-refresh-cw"
                :loading="rereading"
                :disabled="rereading || !rows.length"
                data-testid="reread-type"
                @click="reread"
              >
                {{ t('documentTypes.reread.action') }}
              </UButton>
            </template>
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

          <!--
        The type is saved by the time this shows, so these are not errors to
        retry: they are the fields it will read off every document of this
        kind and then have nothing to compare against. Said here because the
        alternative is discovering it as a missing certificate months later.
      -->
          <section
            v-if="unmappedFields.length > 0"
            class="flex flex-col gap-2"
            data-testid="unmapped-fields"
          >
            <h2 class="font-medium">
              {{ t('documentTypes.new.created.unmappedTitle') }}
            </h2>
            <UAlert
              v-for="field in unmappedFields"
              :key="field.fieldPath"
              color="warning"
              variant="soft"
              :title="field.fieldPath"
              :description="field.reason"
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
      </div>

      <!--
        Sticky: the field list runs long, and reading a row against the paper
        is the whole job, whichever row is being decided.
      -->
      <aside
        class="lg:sticky lg:top-4"
        data-testid="sample-document"
      >
        <UButton
          v-if="sampleDocument"
          :to="`/documents/${sampleDocument.id}`"
          variant="link"
          size="xs"
          class="mb-2 w-fit p-0"
        >
          {{ sampleDocument.fileName }}
        </UButton>
        <p
          v-else-if="sampleFile"
          class="text-toned mb-2 text-[13px]"
        >
          {{ sampleFile.name }}
        </p>

        <DocumentViewer
          v-if="sampleDocument"
          :drive-file-id="sampleDocument.driveFileId"
          :mime-type="sampleDocument.mimeType"
          :file-name="sampleDocument.fileName"
        />
        <iframe
          v-else-if="uploadedPreview && uploadedIsPdf"
          :src="`${uploadedPreview}#toolbar=0&navpanes=0&scrollbar=0&view=FitH`"
          class="border-default aspect-[3/4] w-full rounded-lg border"
        />
        <img
          v-else-if="uploadedPreview && uploadedIsImage"
          :src="uploadedPreview"
          :alt="sampleFile?.name"
          class="border-default w-full rounded-lg border"
        >
        <p
          v-else-if="uploadedPreview"
          class="text-muted text-sm"
        >
          {{ t('documentTypes.new.previewUnsupported') }}
        </p>
        <!--
          Nothing chosen yet. The space is held rather than collapsed, so the
          column does not appear on the first file picked and shove the form
          it sits next to sideways.
        -->
        <div
          v-else
          class="border-default text-muted flex aspect-[3/4] items-center justify-center rounded-lg border border-dashed p-8 text-center text-sm"
          data-testid="sample-pending"
        >
          {{ t('documentTypes.new.samplePending') }}
        </div>
      </aside>
    </div>
  </UContainer>
</template>
