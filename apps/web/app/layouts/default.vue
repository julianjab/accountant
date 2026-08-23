<!-- Desktop-only shell (>= 1280px). Sidebar collapse for narrow viewports is out of scope for now. -->
<template>
  <div class="flex h-screen overflow-hidden bg-muted text-highlighted">
    <AppSidebar>
      <template #auth>
        <AppSidebarAuth />
      </template>
    </AppSidebar>

    <div class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
      <AppTopbar>
        <template #actions>
          <UColorModeButton />
        </template>
      </AppTopbar>

      <main class="min-h-0 flex-1 overflow-auto">
        <slot />
      </main>
    </div>
  </div>
</template>
