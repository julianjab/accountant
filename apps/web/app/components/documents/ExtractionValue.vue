<script setup lang="ts">
import { confidenceValueColorClass } from '~/components/documents/confidence'
import { formatScalarValue, humanizeFieldKey, isArrayOfObjects, isPlainObject } from '~/utils/extraction-field-display'

// Extracted values can nest arbitrarily deep (an object whose own fields are themselves
// objects or arrays of objects — e.g. "retencion_gmf.gmf_operaciones_credito"). A single
// fixed-depth render (object -> scalar) left the second level falling through to
// `String(value)`, which prints "[object Object]". Recursing through itself is what lets
// any depth render as readable rows instead.
const props = defineProps<{
  fieldKey: string
  value: unknown
  confidence: number | null
}>()

const arrayItems = computed(() => (isArrayOfObjects(props.value) ? props.value : null))
const objectEntries = computed(() => (!arrayItems.value && isPlainObject(props.value) ? props.value : null))
const plainArrayItems = computed(() => (
  !arrayItems.value && !objectEntries.value && Array.isArray(props.value) ? props.value : null
))
const scalarDisplayValue = computed(() => (
  arrayItems.value || objectEntries.value || plainArrayItems.value
    ? null
    : formatScalarValue(props.fieldKey, props.value)
))
</script>

<template>
  <dl
    v-if="arrayItems"
    class="w-full space-y-2"
  >
    <div
      v-for="(item, index) in arrayItems"
      :key="index"
      class="space-y-1 rounded-md border border-default bg-elevated p-2.5 text-sm"
    >
      <div
        v-for="(itemValue, itemKey) in item"
        :key="itemKey"
        class="grid grid-cols-1 gap-x-3 gap-y-0.5 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] sm:items-baseline"
      >
        <dt class="text-muted sm:text-left">
          {{ humanizeFieldKey(String(itemKey)) }}
        </dt>
        <dd class="break-words sm:text-right">
          <ExtractionValue
            :field-key="String(itemKey)"
            :value="itemValue"
            :confidence="confidence"
          />
        </dd>
      </div>
    </div>
  </dl>

  <dl
    v-else-if="objectEntries"
    class="w-full space-y-1"
  >
    <div
      v-for="(itemValue, itemKey) in objectEntries"
      :key="itemKey"
      class="grid grid-cols-1 gap-x-3 gap-y-0.5 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] sm:items-baseline"
    >
      <dt class="text-muted sm:text-left">
        {{ humanizeFieldKey(String(itemKey)) }}
      </dt>
      <dd class="break-words sm:text-right">
        <ExtractionValue
          :field-key="String(itemKey)"
          :value="itemValue"
          :confidence="confidence"
        />
      </dd>
    </div>
  </dl>

  <span
    v-else-if="plainArrayItems"
    class="break-words"
    :class="confidenceValueColorClass(confidence)"
  >{{ plainArrayItems.length ? plainArrayItems.map(item => formatScalarValue(fieldKey, item)).join(', ') : '—' }}</span>

  <span
    v-else
    class="break-words"
    :class="confidenceValueColorClass(confidence)"
  >{{ scalarDisplayValue }}</span>
</template>
