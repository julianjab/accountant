<script setup lang="ts">
import type { DocumentType } from '~/domain/entities/document-type'

const { t } = useI18n()
const listDocumentTypes = useListDocumentTypesUseCase()

const { data: documentTypes } = await useAsyncData<DocumentType[]>('document-types', () =>
  listDocumentTypes.execute()
)

function schemaKeys(documentType: DocumentType): string[] {
  const schema = documentType.extractionSchema as { properties?: Record<string, unknown> }
  const properties = schema.properties ?? documentType.extractionSchema
  return Object.keys(properties)
}

// Placeholder metric until the backend exposes "documents processed per type".
function fieldsCount(documentType: DocumentType): number {
  return schemaKeys(documentType).length
}
</script>

<template>
  <UContainer class="py-8">
    <div class="mb-4 flex items-center justify-between">
      <h1 class="text-xl font-semibold">
        {{ t('documentTypes.title') }}
      </h1>
      <UButton
        to="/document-types/new"
        icon="i-lucide-plus"
      >
        {{ t('documentTypes.define') }}
      </UButton>
    </div>

    <p
      v-if="!documentTypes?.length"
      class="text-muted"
    >
      {{ t('documentTypes.empty') }}
    </p>

    <div
      v-else
      class="grid grid-cols-1 gap-4 md:grid-cols-2"
    >
      <UCard
        v-for="documentType in documentTypes"
        :key="documentType.id"
      >
        <template #header>
          <div class="flex items-center justify-between gap-2">
            <h2 class="font-medium">
              {{ documentType.name }}
            </h2>
            <UBadge
              :color="documentType.active ? 'success' : 'neutral'"
              variant="subtle"
            >
              {{ documentType.active ? t('documentTypes.status.active') : t('documentTypes.status.draft') }}
            </UBadge>
          </div>
        </template>

        <p class="text-muted mb-3 text-sm">
          {{ documentType.description }}
        </p>

        <p class="text-muted mb-2 text-xs">
          {{ t('documentTypes.fields.fieldsCount', { count: fieldsCount(documentType) }) }}
        </p>

        <div class="flex flex-wrap gap-1.5">
          <UBadge
            v-for="key in schemaKeys(documentType)"
            :key="key"
            color="neutral"
            variant="outline"
            class="font-mono"
          >
            {{ key }}
          </UBadge>
        </div>
      </UCard>
    </div>
  </UContainer>
</template>
