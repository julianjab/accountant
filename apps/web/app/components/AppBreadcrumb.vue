<script setup lang="ts">
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { labels: breadcrumbLabels } = useBreadcrumbLabels()

const NAV_LABEL_KEYS: Record<string, string> = {
  'clients': 'nav.clients',
  'document-types': 'nav.documentTypes',
  'sheets': 'nav.sheets',
  'documents': 'nav.documents'
}

interface Crumb {
  label: string
  path: string
  /** False for a segment with nowhere to send the reader — no page of its own
   * (`/documents` has no index) and no `linkTo` override pointing elsewhere.
   *
   * Convention: every crumb should end up navigable. A segment with no page of its own
   * should get a `linkTo` override (via `useBreadcrumbLabels().setLabel(path, label, linkTo)`)
   * from whichever page has the context to pick a sensible target — e.g. `documents/[id].vue`
   * points its "documents" crumb at the owning client's page. Only fall back to a dead crumb
   * when truly nothing appropriate exists to link to. */
  navigable: boolean
}

const crumbs = computed<Crumb[]>(() => {
  const segments = route.path.split('/').filter(Boolean)

  let cumulativePath = ''
  const trail = segments.map((segment) => {
    cumulativePath += `/${segment}`
    const override = breadcrumbLabels.value[cumulativePath]
    const key = NAV_LABEL_KEYS[segment]
    const label = override?.label ?? (key ? t(key) : segment)
    const linkPath = override?.linkTo ?? cumulativePath
    return {
      label,
      path: linkPath,
      navigable: router.resolve(linkPath).matched.length > 0
    }
  })

  return [{ label: t('breadcrumb.home'), path: '/', navigable: true }, ...trail]
})
</script>

<template>
  <nav
    aria-label="breadcrumb"
    class="min-w-0"
  >
    <!--
      Below `sm` only the last two crumbs are kept. The full trail does not fit a phone
      header, and trimming to the deepest crumb alone leaves things like a bare client id
      with nothing to say which section it belongs to — the parent is the half that carries
      the meaning. The ancestors above it are one tap away in the drawer.
    -->
    <ol class="flex items-center gap-1.5 font-mono text-xs lowercase text-toned">
      <li
        v-for="(crumb, index) in crumbs"
        :key="index"
        class="items-center gap-1.5"
        :class="index >= crumbs.length - 2 ? 'flex min-w-0' : 'hidden sm:flex'"
      >
        <span
          v-if="index > 0"
          :class="index === crumbs.length - 1 ? '' : 'hidden sm:inline'"
        >/</span>
        <NuxtLink
          v-if="index < crumbs.length - 1 && crumb.navigable"
          :to="crumb.path"
          class="truncate transition-colors duration-[120ms] hover:text-green-600"
        >{{ crumb.label }}</NuxtLink>
        <span
          v-else
          class="truncate"
        >{{ crumb.label }}</span>
      </li>
    </ol>
  </nav>
</template>
