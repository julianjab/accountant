<script setup lang="ts">
/**
 * The figures of this document that the cross-check actually leans on.
 *
 * Shown above the transcription rather than beside it, because these are the
 * ones a misreading turns into a discrepancy: everything else on the page is
 * context an accountant scans, while these are compared against a line of the
 * base report and have to be right. The concept and the line it answers travel
 * with each row, so the reader can see *why* a figure matters without leaving
 * for the type's configuration screen.
 */
import type { MappedField } from '~/domain/mapped-extraction'
import ExtractionValue from '~/components/documents/ExtractionValue.vue'

defineProps<{
  fields: MappedField[]
  /** Per-field confidence is not stored yet; the document-level one stands in. */
  confidence: number | null
}>()

const { t } = useI18n()

/** The leaf of the path, which is what the value formatter reads to decide
 * whether a number is an amount. */
function leafKey(fieldPath: string): string {
  const leaf = fieldPath.split('.').pop() ?? fieldPath
  return leaf.endsWith('[]') ? leaf.slice(0, -2) : leaf
}
</script>

<template>
  <div class="divide-y divide-default">
    <div
      v-for="field in fields"
      :key="field.fieldPath"
      class="py-3"
      data-testid="mapped-concept"
    >
      <div class="flex flex-col gap-1.5 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
        <div class="min-w-0">
          <p class="text-sm text-highlighted">
            {{ field.label }}
          </p>
          <p class="text-xs text-muted">
            {{ field.conceptLabel }}
            <template v-if="field.spineLabel">
              <span aria-hidden="true"> → </span>{{ field.spineLabel }}
            </template>
            <!-- A field the paper states with the opposite sign is added to the
                 comparison negated; without saying so, its figure reads as
                 contradicting the total it in fact completes. -->
            <span
              v-if="field.inverted"
              class="text-dimmed"
            > · {{ t('documents.mapped.inverted') }}</span>
          </p>
        </div>

        <div class="w-full break-words sm:max-w-[60%] sm:text-right">
          <!-- Absent, not zero: the certificate simply does not state this, and
               that silence is exactly what the cross-check reports. -->
          <span
            v-if="field.values.length === 0"
            class="text-sm text-dimmed"
            data-testid="mapped-concept-absent"
          >{{ t('documents.mapped.absent') }}</span>
          <div
            v-for="(entry, index) in field.values"
            v-else
            :key="index"
            class="flex flex-col items-end gap-0.5"
          >
            <ExtractionValue
              :field-key="leafKey(field.fieldPath)"
              :value="entry.value"
              :confidence="confidence"
            />
            <span
              v-if="entry.account"
              class="font-mono text-xs text-dimmed"
            >{{ t('documents.mapped.account', { account: entry.account }) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
