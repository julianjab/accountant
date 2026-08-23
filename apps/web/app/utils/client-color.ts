const PALETTE_SIZE = 6

export interface ClientColor {
  bg: string
  fg: string
}

export function colorForClient(clientId: string): ClientColor {
  const sum = [...clientId].reduce((total, char) => total + char.charCodeAt(0), 0)
  const index = (sum % PALETTE_SIZE) + 1
  return {
    bg: `bg-avatar-${index}-bg`,
    fg: `text-avatar-${index}-fg`
  }
}
