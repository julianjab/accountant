<!-- Desktop-only shell (>= 1280px). Sidebar collapse for narrow viewports is out of scope for now. -->
<template>
  <div class="flex h-screen overflow-hidden bg-neutral-100 text-neutral-900">
    <AppSidebar>
      <template #auth>
        <AppSidebarAuth />
      </template>
    </AppSidebar>

    <div class="flex min-w-0 flex-1 flex-col overflow-hidden">
      <AppTopbar>
        <template #actions>
          <UColorModeButton />
        </template>
      </AppTopbar>

      <main class="flex-1 overflow-auto">
        <slot />
      </main>
    </div>
  </div>
</template>
