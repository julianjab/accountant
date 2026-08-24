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
  const labels = useState<Record<string, string>>('breadcrumb-labels', () => ({}))

  function setLabel(path: string, label: string) {
    labels.value = { ...labels.value, [path]: label }
  }

  function clearLabel(path: string) {
    if (!(path in labels.value)) return
    labels.value = Object.fromEntries(
      Object.entries(labels.value).filter(([key]) => key !== path)
    )
  }

  return { labels: readonly(labels), setLabel, clearLabel }
}
