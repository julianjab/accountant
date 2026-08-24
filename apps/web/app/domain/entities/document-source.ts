/** A file format the server reads on its own, with a parser rather than an AI.
 *
 * Not a document type: these are never proposed by the classifier — a document
 * of one of these formats always fails classification — so the reviewer is the
 * one who names it.
 */
export interface DocumentSource {
  id: string
  label: string
  /** What the parser accepts, so only the sources that could read the file in
   * front of the reader are offered. */
  mediaTypes: string[]
}
