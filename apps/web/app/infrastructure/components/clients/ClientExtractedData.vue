<script setup lang="ts">
import type { ClientDocument } from '~/domain/entities/document'
import type { ExtractedData } from '~/domain/entities/extracted-data'

const props = defineProps<{ documents: ClientDocument[] }>()

const { t } = useI18n()
const getExtractedData = useGetDocumentExtractedDataUseCase()

// Only documents that finished extraction can have fields. Asking for the
// others would be a request per document that is certain to 404.
const extractable = computed(() =>
  props.documents.filter(d => d.status === 'processed' || d.status === 'approved')
)

const { data: extracted, pending } = await useAsyncData<Record<string, ExtractedData | null>>(
  () => `extracted:${extractable.value.map(d => d.id).join(',')}`,
  async () => {
    const entries = await Promise.all(
      extractable.value.map(async d => [d.id, await getExtractedData.execute(d.id)] as const)
    )
    return Object.fromEntries(entries)
  },
  { server: false, default: () => ({}), watch: [extractable] }
)

/** Flattens nested objects and arrays into `path → value` rows.
 *
 * Extraction schemas are proposed per document type, so their shape is not
 * known here and cannot be. Showing the leaves with their path keeps every
 * extracted figure visible whatever the AI designed, and the path is the same
 * one the concept mapping refers to. */
function toRows(value: unknown, prefix = ''): { path: string, value: string }[] {
  if (value === null || value === undefined) return [{ path: prefix, value: '—' }]
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => toRows(item, `${prefix}[${index}]`))
  }
  if (typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>).flatMap(([key, nested]) =>
      toRows(nested, prefix ? `${prefix}.${key}` : key)
    )
  }
  return [{ path: prefix, value: String(value) }]
}

const sections = computed(() =>
  extractable.value.map(document => ({
    document,
    rows: extracted.value?.[document.id] ? toRows(extracted.value[document.id]!.fields) : []
  }))
)
</script>

<template>
  <div
    v-if="pending"
    class="p-4 text-[13px] text-toned"
  >
    {{ t('auth.loading') }}
  </div>

  <p
    v-else-if="sections.length === 0"
    class="p-4 text-[13px] text-toned"
    data-testid="extracted-data-empty"
  >
    {{ t('clients.detail.extractedData.empty') }}
  </p>

  <div v-else>
    <section
      v-for="section in sections"
      :key="section.document.id"
      class="border-b border-default last:border-b-0"
    >
      <div class="flex items-baseline justify-between gap-3 px-4 pt-4">
        <h3 class="text-[13px] font-semibold text-highlighted">
          {{ section.document.fileName }}
        </h3>
        <span class="shrink-0 text-[12px] text-muted">
          {{ t('clients.detail.extractedData.fieldCount', { count: section.rows.length }) }}
        </span>
      </div>

      <p
        v-if="section.rows.length === 0"
        class="px-4 py-3 text-[13px] text-toned"
      >
        {{ t('clients.detail.extractedData.notExtracted') }}
      </p>

      <dl
        v-else
        class="grid grid-cols-1 gap-x-6 px-4 py-3 sm:grid-cols-2"
      >
        <div
          v-for="row in section.rows"
          :key="row.path"
          class="flex items-baseline justify-between gap-3 border-b border-default/60 py-1.5 last:border-b-0"
        >
          <dt class="truncate font-mono text-[11px] text-muted">
            {{ row.path }}
          </dt>
          <dd class="shrink-0 text-right font-mono text-[12px] tabular-nums text-highlighted">
            {{ row.value }}
          </dd>
        </div>
      </dl>
    </section>
  </div>
</template>
