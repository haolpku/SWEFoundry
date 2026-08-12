# Build `featureflags`

Create an installable Python package named `featureflags` in the empty
workspace. It exposes:

```python
from featureflags import evaluate
evaluate(flag: dict, context: dict) -> bool
```

A flag contains a required boolean `default` and optional `rules`. Each rule
contains integer `priority`, boolean `value`, and a list named `all`. Conditions
inside `all` have `key`, `op`, and `value`.

Supported operators:

- `eq`: context value equals the condition value.
- `in`: context value is contained in the condition's list value.
- `exists`: condition value must be boolean; compare it with whether the key
  exists in context.

Evaluate rules by descending priority. For equal priorities, preserve input
order. The first rule whose conditions all match returns its `value`; otherwise
return `default`. An empty `all` list matches.

Reject malformed flags, rules, conditions, unknown operators, non-list `in`
values, and non-boolean `exists` values with `ValueError`. Do not mutate inputs,
read environment variables, access the network, or use third-party packages.
