"""Reading a document type's extraction JSON Schema.

Paths use the notation the projection resolves: dotted segments, with `[]` on a
segment that walks a list (`cuentas[].saldo`). This lives in the domain because
a type's schema is a domain fact — the reconciliation engine has its own
counterpart, `path_resolves_in`, and intake must not reach into it.
"""


def list_schema_paths(schema: object, prefix: str = "") -> tuple[str, ...]:
    """Every leaf an extraction schema declares, as dotted paths.

    The counterpart of the engine's `path_resolves_in`: that one answers
    whether a path the caller already has leads anywhere, this one enumerates
    the paths there are. Objects and arrays of objects are containers rather
    than values, so they are walked into instead of listed — only a leaf holds
    a figure.

    It exists so a re-reading of a sample can be asked about the fields a type
    already declares. Asking the model to propose a schema again and matching
    what comes back by name recovers nothing whenever the second run names its
    fields differently, which for a long certificate is most of the time.
    """
    if not isinstance(schema, dict):
        return ()
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return ()

    paths: list[str] = []
    for key, value in properties.items():
        if not isinstance(value, dict):
            continue
        is_list = value.get("type") == "array"
        target = value.get("items", {}) if is_list else value
        path = f"{prefix}{key}{'[]' if is_list else ''}"
        nested = list_schema_paths(target, f"{path}.")
        if nested:
            paths.extend(nested)
        else:
            paths.append(path)
    return tuple(paths)
