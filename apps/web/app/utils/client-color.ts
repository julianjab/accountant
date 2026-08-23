// TODO(design-system): palette is design-system/README.md § "Avatares de cliente",
// already ported to the 6 --color-avatar-N-bg/fg tokens in app/assets/css/main.css.
// Classes are spelled out as literals (not built from a template string) so Tailwind's
// source scanner can find and generate them.
export interface ClientColor {
  bg: string
  fg: string
}

const PALETTE: ClientColor[] = [
  { bg: 'bg-avatar-1-bg', fg: 'text-avatar-1-fg' },
  { bg: 'bg-avatar-2-bg', fg: 'text-avatar-2-fg' },
  { bg: 'bg-avatar-3-bg', fg: 'text-avatar-3-fg' },
  { bg: 'bg-avatar-4-bg', fg: 'text-avatar-4-fg' },
  { bg: 'bg-avatar-5-bg', fg: 'text-avatar-5-fg' },
  { bg: 'bg-avatar-6-bg', fg: 'text-avatar-6-fg' }
]

export function colorForClient(clientId: string): ClientColor {
  const sum = [...clientId].reduce((total, char) => total + char.charCodeAt(0), 0)
  return PALETTE[sum % PALETTE.length]!
}
