# Reproduce `routekit`

Implement the public API in `routekit.py`:

```python
compile_routes(specs: list[tuple[str, str]]) -> object
match(compiled: object, path: str) -> dict | None
```

Patterns begin with `/` and contain static segments, `:name` parameters, or a
final `*name` wildcard. Names are non-empty ASCII identifiers. Reject malformed
patterns and duplicate patterns with `ValueError`.

Matching rules:

- Paths must begin with `/`; otherwise `match` raises `ValueError`.
- Split on `/` without URL decoding. A trailing slash is ignored except for
  the root path.
- Static segments outrank parameters, which outrank wildcards, regardless of
  declaration order.
- If specificity is otherwise equal, declaration order wins.
- Parameters capture exactly one non-empty segment.
- A wildcard is final and captures the remaining segments joined by `/`; it
  may capture the empty string.
- Return `{"name": route_name, "params": captures}` or `None`.

The environment provides a queryable executable `routekit-oracle` accepting
one JSON request per line. Requests use either:

```json
{"op":"compile","specs":[["home","/"]]}
{"op":"match","specs":[["user","/users/:id"]],"path":"/users/7"}
```

Use it for behavioral exploration. Do not import or invoke it from your final
implementation.
