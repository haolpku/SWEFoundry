Return only one valid JSON object with exactly this top-level shape:

```json
{
  "schema_version": "1.0",
  "task_id": "<exact task id>",
  "diagnosis": "<specific root cause and intended correction>",
  "files": [
    {
      "path": "<existing or new safe task-relative path>",
      "content": "<complete replacement file>",
      "executable": false
    }
  ]
}
```

Repair the executable benchmark, not its score. Preserve the published API,
instructions, named behavior cases, check counts, strict `release_pass`
semantics, Starter rejection, five Step-specific mutants, and subprocess
isolation. Never delete, skip, weaken, xfail, mock away, or special-case a
check. Never read reward files or tests from candidate code.

The executable `verifier/run_audit.py` contract is strict: it must write an
`audit-report.json` object with a top-level boolean `passed`, and exit zero if
and only if every audit gate succeeds. A deliberately rejected Starter or
mutant has verifier `release_pass == 0` but its audit gate is successful, so
the gate's `passed` value remains true. Do not invert or rename this meaning to
make a report appear successful.

Prefer the smallest coherent set of complete replacement files. Step solutions
are cumulative: installing solutions 1…N into a fresh starter must make that
Step's public smoke and strict verifier pass. Fix syntax, imports, package
exports, solution payloads, public-smoke fixtures, and verifier harness defects
only when the supplied evidence proves they are wrong.

Allowed roots are `environment/`, `steps/`, and `verifier/`. Do not replace
`task.toml`, `metadata.json`, or `audit-report.json`. Use Python standard
library only, no runtime network, no random/hash/wall-clock/locale dependence,
and no host-specific ordering.
