export interface BreadcrumbOverride {
  label: string
  /** Where this crumb should link to, when it differs from its own URL segment — e.g. the
   * "documents" segment has no index page of its own, so it links to the owning client's
   * page instead of being a dead crumb. */
  linkTo?: string
}

/**
 * Overrides for individual breadcrumb crumbs, keyed by the route path they belong to.
 *
 * `AppBreadcrumb` builds its trail purely from the URL (`/clients/<id>`), which is all it
 * has access to — it renders on every page and knows nothing about a specific entity. A page
 * that *does* have the entity (e.g. `clients/[id].vue` holding the loaded `Client`) can call
 * `setLabel` with a human-readable name so the crumb for its own path stops being a raw id,
 * and should call `clearLabel` (or rely on the `onUnmounted` cleanup below) once it no longer
 * has that data to offer.
 *
 * `useState` (not a module-level ref) so the value is per-request on the server, matching the
 * convention used by `useMobileNav`.
 */
export function useBreadcrumbLabels() {
  const overrides = useState<Record<string, BreadcrumbOverride>>('breadcrumb-labels', () => ({}))

  function setLabel(path: string, label: string, linkTo?: string) {
    overrides.value = { ...overrides.value, [path]: { label, linkTo } }
  }

  function clearLabel(path: string) {
    if (!(path in overrides.value)) return
    overrides.value = Object.fromEntries(
      Object.entries(overrides.value).filter(([key]) => key !== path)
    )
  }

  return { labels: readonly(overrides), setLabel, clearLabel }
}
