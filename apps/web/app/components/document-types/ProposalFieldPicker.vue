<script setup lang="ts">
/**
 * The list a proposal is answered with, shared by creating and regenerating.
 *
 * Both screens ask the same question — which of these fields matter, and what
 * do you call them — so they ask it with the same list. Before this, creating
 * offered a choice and regenerating offered a read-only diff, and the two
 * drifted: the screen that most needed a correction (a type already in use,
 * read wrong) was the one with nowhere to make it.
 *
 * The row is a checkbox and nothing else until asked. Renaming a field and
 * writing a note about it are real controls, but they are the exception —
 * putting two text inputs on all thirty-five rows would bury the tick that is
 * the actual work.
 */
import type { ProposalFieldRow } from '~/domain/document-type-configuration'
import { groupBySection, rowLabel } from '~/domain/document-type-configuration'
import type { SectionNotes } from '~/domain/proposal-loop'
import { sectionKey } from '~/domain/proposal-loop'
import { matchesFieldQuery } from '~/domain/field-search'
import { isRepeatedPath } from '~/domain/extraction-schema'
import { formatSampleValue } from '~/utils/extraction-field-display'

const props = defineProps<{
  /** Mutated in place: the rows are the screen's own state, and the parent
   * reads the ticks back off them when it saves or regenerates. */
  rows: ProposalFieldRow[]
  /** Paths this reading added that the type did not have. Annotated rather
   * than separated, so a new field is still chosen among its neighbours on
   * the page instead of in a list of its own. */
  addedPaths?: readonly string[]
  /** Paths the type declares today that this reading no longer proposes. Named
   * on the row itself: a count above a list is not an answer to "which ones",
   * which is the only question worth asking about a field about to be lost. */
  removedPaths?: readonly string[]
  /**
   * What the reader has said about each block of the document.
   *
   * Read-only here and written through `annotate`: unlike the rows — whose
   * ticks are the screen's own state — these are the parent's, and a note
   * about a block outlives the rows of any one round.
   *
   * Per block rather than only per field because that is the grain most
   * corrections come in: "this table has one row per obligation" governs every
   * field under that heading, and saying it once against the heading beats
   * repeating it on each row or burying it in the general guidance, where the
   * model has to work out which part of the page was meant.
   */
  sectionNotes?: SectionNotes
}>()

const emit = defineEmits<{ annotate: [section: string, note: string] }>()

const { t } = useI18n()

const fieldQuery = ref('')
const visibleRows = computed(() =>
  props.rows.filter(row =>
    matchesFieldQuery(fieldQuery.value, [rowLabel(row), row.path, row.sampleValue, row.section])
  )
)

/** Sections are built from what is on screen, so the counts and the
 * mark-all/none buttons of a filtered list act on the rows the user can
 * actually see rather than on hidden ones. */
const rowByPath = computed(() => new Map(props.rows.map(row => [row.path, row])))

const sections = computed(() =>
  groupBySection(visibleRows.value).map(group => ({
    ...group,
    // The group is a domain answer about paths; the rows it is rendered with
    // are a rendering detail, resolved once here instead of in the template.
    rows: group.paths.map(path => rowByPath.value.get(path)).filter(row => row !== undefined)
  }))
)

const keptCount = computed(() => props.rows.filter(row => row.kept).length)
const added = computed(() => new Set(props.addedPaths ?? []))
const removed = computed(() => new Set(props.removedPaths ?? []))

function setSection(paths: readonly string[], kept: boolean) {
  const target = new Set(paths)
  for (const row of props.rows) {
    if (target.has(row.path)) row.kept = kept
  }
}

/**
 * Which rows have their advanced controls open.
 *
 * Keyed by path rather than held on the row: this is a state of the screen,
 * not of the field, and storing it on the row would send it to the server on
 * the next round as part of the answer.
 */
const editing = ref(new Set<string>())

function toggleEditing(path: string) {
  const next = new Set(editing.value)
  if (next.has(path)) next.delete(path)
  else next.add(path)
  editing.value = next
}

/** A field the person edited stays open even after a regeneration, because
 * what they wrote is the reason the row looks the way it does. */
function isEditing(row: ProposalFieldRow): boolean {
  return editing.value.has(row.path) || !!row.renamedLabel || !!row.note
}

/** The value as the paper states it: an amount is money, and shown as money
 * — a bare `150464.81` beside a certificate that prints `$150.464,81` is the
 * one thing here nobody can check at a glance. */
function sampleValueOf(row: ProposalFieldRow): string {
  return formatSampleValue(row.sampleValue, row.role, row.path)
}

/** Which blocks have their instruction box open. A block that already carries
 * one stays open: what was written is why the reading below looks as it does. */
const annotating = ref(new Set<string>())

function toggleAnnotating(section: string | null) {
  const key = sectionKey(section)
  const next = new Set(annotating.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  annotating.value = next
}

function isAnnotating(section: string | null): boolean {
  const key = sectionKey(section)
  return annotating.value.has(key) || !!props.sectionNotes?.[key]?.trim()
}

function sectionNote(section: string | null): string {
  return props.sectionNotes?.[sectionKey(section)] ?? ''
}

function setSectionNote(section: string | null, value: string) {
  emit('annotate', sectionKey(section), value)
}

function setRenamed(row: ProposalFieldRow, value: string) {
  // Empty means "call it what the document calls it" — stored as null so the
  // next reading may refresh the label instead of pinning an empty string.
  row.renamedLabel = value.trim() ? value : null
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <UInput
      v-model="fieldQuery"
      icon="i-lucide-search"
      class="w-full sm:w-96"
      data-testid="field-filter"
      :placeholder="t('documentTypes.fields.filter.placeholder')"
    >
      <template
        v-if="fieldQuery"
        #trailing
      >
        <UButton
          color="neutral"
          variant="link"
          size="sm"
          icon="i-lucide-x"
          :aria-label="t('documentTypes.fields.filter.clear')"
          @click="fieldQuery = ''"
        />
      </template>
    </UInput>

    <p
      v-if="!visibleRows.length"
      class="text-muted text-sm"
      data-testid="field-filter-empty"
    >
      {{ t('documentTypes.fields.filter.empty', { query: fieldQuery }) }}
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
              {{ section.section ?? t('documentTypes.sections.other') }}
            </p>
            <p class="text-muted text-xs">
              {{ t('documentTypes.sections.count', {
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
              {{ t('documentTypes.sections.all') }}
            </UButton>
            <UButton
              size="xs"
              color="neutral"
              variant="ghost"
              @click="setSection(section.paths, false)"
            >
              {{ t('documentTypes.sections.none') }}
            </UButton>
            <UButton
              v-if="sectionNotes"
              size="xs"
              color="neutral"
              variant="ghost"
              icon="i-lucide-message-square-plus"
              :data-testid="`section-annotate-${section.section ?? '__headless__'}`"
              @click="toggleAnnotating(section.section)"
            >
              {{ t('documentTypes.sections.annotate') }}
            </UButton>
          </div>
        </div>

        <!--
          Aimed at the whole block, and sent with it: the fields under one
          heading are read together, and the correction that matters most —
          what the table actually is — is a statement about the heading rather
          than about any one row beneath it.
        -->
        <UFormField
          v-if="sectionNotes && isAnnotating(section.section)"
          :label="t('documentTypes.sections.annotateLabel')"
          :help="t('documentTypes.sections.annotateHint')"
        >
          <UTextarea
            :model-value="sectionNote(section.section)"
            :rows="2"
            class="w-full"
            :data-testid="`section-note-${section.section ?? '__headless__'}`"
            :placeholder="t('documentTypes.sections.annotatePlaceholder')"
            @update:model-value="setSectionNote(section.section, String($event))"
          />
        </UFormField>

        <div
          v-for="row in section.rows"
          :key="row.path"
          class="border-default rounded-lg border transition-colors duration-[120ms]"
          :class="row.kept ? '' : 'opacity-60'"
          :data-testid="`field-row-${row.path}`"
        >
          <div class="flex items-start gap-3 p-3">
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
                  {{ rowLabel(row) }}
                </p>
                <UBadge
                  size="sm"
                  variant="subtle"
                  :color="row.role === 'amount' ? 'primary' : row.role === 'identifier' ? 'success' : 'neutral'"
                >
                  {{ t(`documentTypes.new.select.role.${row.role}`) }}
                </UBadge>
                <UBadge
                  v-if="added.has(row.path)"
                  size="sm"
                  variant="subtle"
                  color="success"
                  data-testid="field-added"
                >
                  {{ t('documentTypes.fields.added') }}
                </UBadge>
                <UBadge
                  v-if="removed.has(row.path)"
                  size="sm"
                  variant="subtle"
                  color="warning"
                  data-testid="field-removed"
                >
                  {{ t('documentTypes.fields.removed') }}
                </UBadge>
                <UBadge
                  v-if="row.renamedLabel"
                  size="sm"
                  variant="subtle"
                  color="neutral"
                  :title="row.label"
                >
                  {{ t('documentTypes.fields.renamed') }}
                </UBadge>
              </div>
              <p
                v-if="row.sampleValue"
                class="text-toned text-[13px]"
              >
                {{ t(
                  isRepeatedPath(row.path)
                    ? 'documentTypes.sections.sampleValueRow'
                    : 'documentTypes.sections.sampleValue',
                  { value: sampleValueOf(row) }
                ) }}
              </p>
              <p class="text-dimmed break-all font-mono text-xs">
                {{ row.path }}
              </p>
            </div>
            <UButton
              size="xs"
              color="neutral"
              variant="ghost"
              icon="i-lucide-pencil"
              class="shrink-0"
              :aria-label="t('documentTypes.fields.edit')"
              :data-testid="`field-edit-${row.path}`"
              @click="toggleEditing(row.path)"
            >
              {{ t('documentTypes.fields.edit') }}
            </UButton>
          </div>

          <!--
            Opened by request, and left open once written in: what the person
            typed is the reason the row reads the way it does, so hiding it
            behind a toggle they have to remember pressing would be a trap.
          -->
          <div
            v-if="isEditing(row)"
            class="border-default flex flex-col gap-3 border-t p-3 sm:flex-row"
            :data-testid="`field-advanced-${row.path}`"
          >
            <UFormField
              :label="t('documentTypes.fields.label')"
              :help="t('documentTypes.fields.labelHint')"
              class="flex-1"
            >
              <UInput
                :model-value="row.renamedLabel ?? ''"
                class="w-full"
                :placeholder="row.label"
                :data-testid="`field-label-${row.path}`"
                @update:model-value="setRenamed(row, String($event))"
              />
            </UFormField>
            <UFormField
              :label="t('documentTypes.fields.note')"
              :help="t('documentTypes.fields.noteHint')"
              class="flex-1"
            >
              <UInput
                v-model="row.note"
                class="w-full"
                :placeholder="t('documentTypes.fields.notePlaceholder')"
                :data-testid="`field-note-${row.path}`"
              />
            </UFormField>
          </div>
        </div>
      </section>
    </div>

    <p
      class="text-muted text-sm"
      data-testid="kept-summary"
    >
      {{ t('documentTypes.new.select.keptSummary', { kept: keptCount, total: rows.length }) }}
    </p>
  </div>
</template>
