<script setup lang="ts">
/**
 * What one extracted value is to the reconciliation, beside the value itself.
 *
 * A tag rather than a separate list of the same document: the reader is
 * already looking at the figure, and the question a tag answers — "does this
 * one matter?" — is asked while reading down the page, not before it.
 *
 * The two states are deliberately different colours. A figure compared against
 * a line of the exógena is one a misreading turns into a discrepancy; a figure
 * merely carried into the cross-check is not, and levelling them would make
 * the tag decoration.
 */
import type { MappedConcept } from '~/domain/mapped-extraction'

const props = defineProps<{ concept: MappedConcept }>()

const { t } = useI18n()

// The line of the base report wins the label: among the mapped values it is
// what distinguishes one from another, while the concept is the internal name
// of the same idea.
const label = computed(() => props.concept.spineLabel ?? props.concept.conceptLabel)

/** The whole story on hover, for a tag that had to be short. */
const title = computed(() => {
  const parts = [
    props.concept.spineLabel
      ? t('documents.mapped.answers', {
          concept: props.concept.conceptLabel,
          spine: props.concept.spineLabel
        })
      : t('documents.mapped.notCompared', { concept: props.concept.conceptLabel })
  ]
  if (props.concept.inverted) parts.push(t('documents.mapped.inverted'))
  return parts.join(' · ')
})
</script>

<template>
  <UBadge
    :color="concept.spineLabel ? 'primary' : 'neutral'"
    variant="subtle"
    size="sm"
    class="max-w-full"
    :title="title"
    data-testid="concept-tag"
    :data-crossed="concept.spineLabel ? 'true' : 'false'"
  >
    <span class="truncate">{{ label }}</span>
    <!-- A figure the paper states with the opposite sign is added to the
         comparison negated; without saying so it reads as contradicting the
         total it in fact completes. -->
    <span
      v-if="concept.inverted"
      class="ml-1 opacity-70"
    >&minus;</span>
  </UBadge>
</template>
