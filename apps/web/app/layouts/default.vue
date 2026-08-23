<script setup lang="ts">
const { isOpen, close } = useMobileNav()

// Escape closes the drawer wherever focus happens to be. Registered on the window (not on
// the <nav>) so it also works right after the toggle is pressed, while focus is still on it.
onMounted(() => {
  function onKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') close()
  }
  window.addEventListener('keydown', onKeydown)
  onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
})

// The drawer overlays a page that is still scrollable behind it, so scrolling the backdrop
// would move the page under the reader's finger. Locked on <body> rather than a wrapper
// because the mobile shell deliberately scrolls the document, not an inner element.
watch(isOpen, (open) => {
  document.body.classList.toggle('overflow-hidden', open)
})

onBeforeUnmount(() => document.body.classList.remove('overflow-hidden'))
</script>

<!--
  Mobile first: one scrolling document column, with the sidebar as an off-canvas drawer.
  From `lg` up it becomes the classic two-pane shell — a permanent sidebar next to a main
  region that scrolls on its own inside a viewport-height frame. `h-screen` is deliberately
  `lg:`-only: on mobile browsers the address bar makes 100vh taller than what is visible,
  so a full-height non-scrolling body would clip the bottom of every page.
-->
<template>
  <div class="flex min-h-screen bg-muted text-highlighted lg:h-screen lg:min-h-0 lg:overflow-hidden">
    <Transition
      enter-active-class="transition-opacity duration-200"
      leave-active-class="transition-opacity duration-200"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isOpen"
        class="fixed inset-0 z-40 bg-neutral-950/50 lg:hidden"
        data-testid="mobile-nav-backdrop"
        @click="close"
      />
    </Transition>

    <AppSidebar>
      <template #auth>
        <AppSidebarAuth />
      </template>
    </AppSidebar>

    <div class="flex min-h-0 min-w-0 flex-1 flex-col lg:overflow-hidden">
      <AppTopbar>
        <template #actions>
          <UColorModeButton />
        </template>
      </AppTopbar>

      <main class="min-h-0 flex-1 lg:overflow-auto">
        <slot />
      </main>
    </div>
  </div>
</template>
