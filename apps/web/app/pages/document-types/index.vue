<script setup lang="ts">
import type { DocumentType } from '~/domain/entities/document-type'

const { t } = useI18n()
const listDocumentTypes = useListDocumentTypesUseCase()
const { isAuthenticated, isLoading: isAuthLoading } = useGoogleAuth()

// Deferred and client-only on purpose: the endpoint needs the session cookie,
// which SSR does not carry (see clients/index.vue).
const { data: documentTypes, pending, refresh } = await useAsyncData<DocumentType[]>(
  'document-types',
  () => listDocumentTypes.execute(),
  { immediate: false, server: false, default: () => [] }
)

watch(isAuthenticated, authenticated => authenticated && refresh(), { immediate: true })

// Same gap as clients/index.vue: still loading once signed in, before `documentTypes` has resolved.
const showSkeleton = computed(() => isAuthLoading.value || (isAuthenticated.value && pending.value && !documentTypes.value?.length))

function schemaKeys(documentType: DocumentType): string[] {
  const schema = documentType.extractionSchema as { properties?: Record<string, unknown> } | null | undefined
  return Object.keys(schema?.properties ?? {})
}

// Placeholder metric until the backend exposes "documents processed per type".
function fieldsCount(documentType: DocumentType): number {
  return schemaKeys(documentType).length
}
</script>

<template>
  <UContainer class="py-6 sm:py-8">
    <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <h1 class="text-xl font-semibold">
        {{ t('documentTypes.title') }}
      </h1>
      <UButton
        to="/document-types/new"
        icon="i-lucide-plus"
        block
        class="sm:w-auto"
      >
        {{ t('documentTypes.define') }}
      </UButton>
    </div>

    <div
      v-if="showSkeleton"
      class="grid grid-cols-1 gap-4 md:grid-cols-2"
    >
      <SkeletonCard
        v-for="n in 4"
        :key="n"
        :lines="3"
      />
    </div>

    <p
      v-else-if="!isAuthenticated"
      class="text-muted"
      data-testid="document-types-signed-out"
    >
      {{ t('documentTypes.signInRequired') }}
    </p>

    <p
      v-else-if="!documentTypes?.length"
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
          <div class="flex items-start justify-between gap-2">
            <h2 class="min-w-0 break-words font-medium">
              {{ documentType.name }}
            </h2>
            <UBadge
              :color="documentType.active ? 'success' : 'neutral'"
              variant="subtle"
              class="shrink-0"
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

        <template #footer>
          <UButton
            :to="`/document-types/${documentType.id}`"
            icon="i-lucide-sliders-horizontal"
            color="neutral"
            variant="soft"
            block
            class="sm:w-fit"
          >
            {{ t('documentTypes.configure') }}
          </UButton>
        </template>
      </UCard>
    </div>
  </UContainer>
</template>
