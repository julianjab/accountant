/**
 * Reading and trimming a document type's extraction JSON Schema.
 *
 * Field paths use the same notation the server resolves when it projects
 * extracted data into facts: dotted segments, with `[]` on a segment that
 * walks a list (`accounts[].balance`). Anything else would be rejected as a
 * field the schema does not declare.
 */

export interface JsonSchemaNode {
  type?: unknown
  description?: unknown
  properties?: unknown
  items?: unknown
  required?: unknown
}

export interface SchemaField {
  /** The path the mapping refers to this field by. */
  path: string
  /** Last segment only, for a readable label next to the path. */
  name: string
  type: string
  description: string
  required: boolean
}

function asNode(value: unknown): JsonSchemaNode | null {
  return typeof value === 'object' && value !== null ? (value as JsonSchemaNode) : null
}

function propertiesOf(node: JsonSchemaNode | null): Record<string, unknown> | null {
  const properties = asNode(node?.properties)
  return properties ? (properties as Record<string, unknown>) : null
}

function requiredOf(node: JsonSchemaNode | null): string[] {
  return Array.isArray(node?.required) ? node.required.filter(k => typeof k === 'string') : []
}

function asText(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

/** The schema node a path segment actually describes, unwrapping an array. */
function unwrap(property: JsonSchemaNode): { node: JsonSchemaNode, isList: boolean } {
  if (property.type === 'array') {
    return { node: asNode(property.items) ?? {}, isList: true }
  }
  return { node: property, isList: false }
}

/**
 * Every leaf the schema declares, flattened.
 *
 * Objects and lists of objects are containers, not values, so they are walked
 * into rather than listed: only a leaf can carry an amount worth mapping.
 */
/**
 * Whether a path stands for something the document prints more than once.
 *
 * `obligaciones_a_cargo[].capital` is not one figure, it is a column: the
 * certificate prints one per row of the table. Everything that shows a single
 * "value read from the sample" for such a path is showing one occurrence out
 * of several, and has to say so — a reader who sees a lone figure under a
 * column concludes the extraction found a single row, which is exactly the
 * wrong thing to conclude while deciding whether the table was read right.
 */
export function isRepeatedPath(path: string): boolean {
  return path.includes('[]')
}

export function listSchemaFields(schema: unknown, prefix = ''): SchemaField[] {
  const node = asNode(schema)
  const properties = propertiesOf(node)
  if (!properties) return []

  const required = requiredOf(node)
  const fields: SchemaField[] = []

  for (const [key, rawProperty] of Object.entries(properties)) {
    const property = asNode(rawProperty)
    if (!property) continue

    const { node: target, isList } = unwrap(property)
    const path = `${prefix}${key}${isList ? '[]' : ''}`

    if (propertiesOf(target)) {
      fields.push(...listSchemaFields(target, `${path}.`))
      continue
    }

    fields.push({
      path,
      name: key,
      type: asText(target.type) || asText(property.type),
      description: asText(property.description) || asText(target.description),
      required: required.includes(key)
    })
  }

  return fields
}

/**
 * The same schema with every field the user dropped removed.
 *
 * A container left with no properties goes too: an empty object in the schema
 * asks the OCR for a shape with nothing in it, which is noise in the prompt
 * and can never be mapped.
 */
export function pruneSchema(
  schema: Record<string, unknown>,
  keptPaths: ReadonlySet<string>,
  prefix = ''
): Record<string, unknown> {
  const node = asNode(schema)
  const properties = propertiesOf(node)
  if (!properties) return schema

  const kept: Record<string, unknown> = {}

  for (const [key, rawProperty] of Object.entries(properties)) {
    const property = asNode(rawProperty)
    if (!property) continue

    const { node: target, isList } = unwrap(property)
    const path = `${prefix}${key}${isList ? '[]' : ''}`

    if (propertiesOf(target)) {
      const prunedTarget = pruneSchema(
        target as Record<string, unknown>,
        keptPaths,
        `${path}.`
      )
      if (Object.keys(propertiesOf(asNode(prunedTarget)) ?? {}).length === 0) continue
      kept[key] = isList ? { ...property, items: prunedTarget } : prunedTarget
      continue
    }

    if (keptPaths.has(path)) kept[key] = rawProperty
  }

  const pruned: Record<string, unknown> = { ...schema, properties: kept }
  const required = requiredOf(node).filter(key => key in kept)
  if (Array.isArray(node?.required)) pruned.required = required
  return pruned
}
