<script setup lang="ts">
import type { DocumentType } from '~/domain/entities/document-type'

type Step = 'form' | 'loading' | 'proposal' | 'error'

const { t } = useI18n()
const defineDocumentType = useDefineDocumentTypeUseCase()

const name = ref('')
const description = ref('')
const sampleFile = ref<File | null>(null)

const step = ref<Step>('form')
const loading = computed(() => step.value === 'loading')
const documentType = ref<DocumentType | null>(null)

const editing = ref(false)
const editedPrompt = ref('')
const editedSchemaText = ref('')
const jsonError = ref(false)

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  sampleFile.value = input.files?.[0] ?? null
}

async function onSubmit() {
  if (loading.value || !sampleFile.value) return

  step.value = 'loading'

  try {
    documentType.value = await defineDocumentType.execute({
      name: name.value,
      description: description.value,
      sampleFile: sampleFile.value
    })
    step.value = 'proposal'
  } catch {
    step.value = 'error'
  }
}

function startEditing() {
  if (!documentType.value) return
  editedPrompt.value = documentType.value.extractionPrompt
  editedSchemaText.value = JSON.stringify(documentType.value.extractionSchema, null, 2)
  jsonError.value = false
  editing.value = true
}

function cancelEditing() {
  editing.value = false
  jsonError.value = false
}

function confirmEditing() {
  try {
    const schema = JSON.parse(editedSchemaText.value)
    if (!documentType.value) return
    // TODO(follow-up): persist edits via PATCH /document-types/{id} once that endpoint exists.
    documentType.value = {
      ...documentType.value,
      extractionPrompt: editedPrompt.value,
      extractionSchema: schema
    }
    jsonError.value = false
    editing.value = false
  } catch {
    jsonError.value = true
  }
}

function saveType() {
  navigateTo('/document-types')
}
</script>

<template>
  <UContainer class="py-8">
    <h1 class="mb-4 text-xl font-semibold">
      {{ t('documentTypes.new.title') }}
    </h1>

    <UAlert
      v-if="step === 'error'"
      color="error"
      class="mb-4"
      :title="t('documentTypes.new.error')"
    />

    <form
      v-if="step === 'form' || step === 'error'"
      class="flex max-w-xl flex-col gap-4"
      @submit.prevent="onSubmit"
    >
      <UFormField
        :label="t('documentTypes.fields.name')"
        required
      >
        <UInput
          v-model="name"
          required
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
        required
      >
        <input
          type="file"
          accept="application/pdf,image/png,image/jpeg,image/webp,image/gif"
          required
          @change="onFileChange"
        >
      </UFormField>

      <UButton
        type="submit"
        :loading="loading"
        :disabled="loading"
        class="w-fit"
      >
        {{ t('documentTypes.new.submit') }}
      </UButton>
    </form>

    <div
      v-else-if="step === 'loading'"
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
      v-else-if="step === 'proposal' && documentType"
      class="flex flex-col gap-4"
    >
      <h2 class="text-lg font-medium">
        {{ t('documentTypes.proposal.title') }}
      </h2>

      <div>
        <p class="mb-1 text-sm font-medium">
          {{ t('documentTypes.proposal.prompt') }}
        </p>
        <UTextarea
          v-if="editing"
          v-model="editedPrompt"
          class="w-full"
          :rows="8"
        />
        <pre
          v-else
          class="bg-muted text-highlighted ring-default max-h-64 overflow-auto whitespace-pre-wrap rounded-md p-3 font-mono text-xs ring-1"
        >{{ documentType.extractionPrompt }}</pre>
      </div>

      <div>
        <p class="mb-1 text-sm font-medium">
          {{ t('documentTypes.proposal.schema') }}
        </p>
        <UTextarea
          v-if="editing"
          v-model="editedSchemaText"
          class="w-full font-mono"
          :rows="12"
        />
        <pre
          v-else
          class="bg-muted text-highlighted ring-default max-h-64 overflow-auto whitespace-pre-wrap rounded-md p-3 font-mono text-xs ring-1"
        >{{ JSON.stringify(documentType.extractionSchema, null, 2) }}</pre>
        <p
          v-if="jsonError"
          class="text-error mt-1 text-xs"
        >
          {{ t('documentTypes.new.invalidJson') }}
        </p>
      </div>

      <div class="flex gap-2">
        <template v-if="editing">
          <UButton @click="confirmEditing">
            {{ t('documentTypes.proposal.edit') }}
          </UButton>
          <UButton
            color="neutral"
            variant="soft"
            @click="cancelEditing"
          >
            {{ t('documentTypes.proposal.cancelEdit') }}
          </UButton>
        </template>
        <template v-else>
          <UButton @click="saveType">
            {{ t('documentTypes.proposal.save') }}
          </UButton>
          <UButton
            color="neutral"
            variant="soft"
            @click="startEditing"
          >
            {{ t('documentTypes.proposal.edit') }}
          </UButton>
        </template>
      </div>
    </div>
  </UContainer>
</template>
