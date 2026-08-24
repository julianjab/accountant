<script setup lang="ts">
import { confidenceBarColorClass, confidenceBarWidthPercent, confidenceValueColorClass } from '~/components/documents/confidence'
import { formatScalarValue, humanizeFieldKey, isArrayOfObjects, isPlainObject } from '~/utils/extraction-field-display'

const props = defineProps<{
  fieldKey: string
  value: unknown
  confidence: number | null
}>()

const label = computed(() => humanizeFieldKey(props.fieldKey))

// Extracted values are shaped by a DocumentType's dynamic schema: a plain scalar most of the
// time, but sometimes an object (a nested "contribuyente { nombre, numero_identificacion }")
// or an array of objects (a list of movements). Dumping either as raw JSON is unreadable for
// a non-technical accountant, so each shape gets its own rendering below instead.
const arrayItems = computed(() => (isArrayOfObjects(props.value) ? props.value : null))
const objectEntries = computed(() => (!arrayItems.value && isPlainObject(props.value) ? props.value : null))
const scalarDisplayValue = computed(() => (
  arrayItems.value || objectEntries.value ? null : formatScalarValue(props.fieldKey, props.value)
))
</script>

<template>
  <div class="py-3">
    <div class="flex flex-col gap-1.5 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
      <span class="font-mono text-sm text-muted sm:pt-0.5">{{ label }}</span>

      <div
        v-if="arrayItems"
        class="flex w-full flex-col gap-2 sm:max-w-[70%]"
      >
        <dl
          v-for="(item, index) in arrayItems"
          :key="index"
          class="space-y-1 rounded-md border border-default bg-elevated p-2.5 text-sm"
        >
          <div
            v-for="(itemValue, itemKey) in item"
            :key="itemKey"
            class="flex items-baseline justify-between gap-3"
          >
            <dt class="text-muted">
              {{ humanizeFieldKey(String(itemKey)) }}
            </dt>
            <dd
              class="break-words text-right"
              :class="confidenceValueColorClass(confidence)"
            >
              {{ formatScalarValue(String(itemKey), itemValue) }}
            </dd>
          </div>
        </dl>
      </div>

      <dl
        v-else-if="objectEntries"
        class="w-full space-y-1 text-sm sm:max-w-[70%]"
      >
        <div
          v-for="(itemValue, itemKey) in objectEntries"
          :key="itemKey"
          class="flex items-baseline justify-between gap-3"
        >
          <dt class="text-muted">
            {{ humanizeFieldKey(String(itemKey)) }}
          </dt>
          <dd
            class="break-words text-right"
            :class="confidenceValueColorClass(confidence)"
          >
            {{ formatScalarValue(String(itemKey), itemValue) }}
          </dd>
        </div>
      </dl>

      <!-- `break-words`: an extracted value is arbitrary OCR output (a long IBAN, a URL) with
           no space to wrap at, so without it the row pushes the card past the viewport. -->
      <span
        v-else
        class="break-words sm:text-right"
        :class="confidenceValueColorClass(confidence)"
      >{{ scalarDisplayValue }}</span>
    </div>
    <div
      v-if="confidence !== null"
      class="mt-2 h-[34px] w-full rounded bg-elevated"
    >
      <div
        class="h-full rounded"
        :class="confidenceBarColorClass(confidence)"
        :style="{ width: `${confidenceBarWidthPercent(confidence)}%` }"
      />
    </div>
  </div>
</template>
