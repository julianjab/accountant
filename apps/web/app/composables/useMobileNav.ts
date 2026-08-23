/**
 * Open/closed state of the navigation drawer, which is the sidebar's shape below `lg`.
 * From `lg` up the sidebar is a permanent rail and this state is irrelevant — the drawer
 * classes are overridden by `lg:` variants rather than by reading the viewport here, so
 * nothing depends on `window` during SSR.
 *
 * `useState` (not a module-level ref) so the value is per-request on the server: a
 * module-level ref would be shared across every concurrent SSR render.
 */
export function useMobileNav() {
  const isOpen = useState('mobile-nav-open', () => false)
  const route = useRoute()

  function open() {
    isOpen.value = true
  }

  function close() {
    isOpen.value = false
  }

  function toggle() {
    isOpen.value = !isOpen.value
  }

  // Navigating is the drawer's whole purpose, so every route change dismisses it —
  // including a tap on the link for the page already open, which changes nothing else.
  watch(() => route.fullPath, close)

  return { isOpen: readonly(isOpen), open, close, toggle }
}
