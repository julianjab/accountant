/** How a document read by a dedicated parser is named on screen.
 *
 * The name lives here rather than travelling from the server with the
 * document: it is user-facing text, and the convention is that user-facing
 * text goes through i18n. The server only ever hands over an opaque
 * `sourceId`, which is the right shape for it — it is an identifier, not a
 * label.
 */
export function documentSourceLabelKey(sourceId: string): string {
  return `documents.sources.${sourceId}`
}
