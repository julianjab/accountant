<script setup lang="ts">
// Generic list/table-row placeholder: a leading icon box, a title line, and an optional
// trailing chip — the shape shared by `InboxDocumentRow`, the client list rows, etc.
withDefaults(
  defineProps<{
    indent?: boolean
    trailing?: boolean
  }>(),
  { indent: false, trailing: true }
)
</script>

<template>
  <div
    class="flex items-center gap-2.5 border-b border-muted px-4 py-3 last:border-b-0"
    :class="indent ? 'sm:pl-12' : ''"
  >
    <USkeleton class="h-[26px] w-[22px] shrink-0 rounded-[3px]" />
    <USkeleton class="h-3.5 w-40 max-w-[45%]" />
    <USkeleton
      v-if="trailing"
      class="ml-auto h-5 w-16 shrink-0 rounded-full"
    />
  </div>
</template>
