Return exactly one valid JSON object and no Markdown:

{
  "schema_version": "1.0",
  "task_id": "<exact task_id from accepted blueprint>",
  "fragment": "core",
  "files": [
    {"path": "relative/path", "executable": false, "content": "complete file"}
  ],
  "implementation_notes": [],
  "known_open_gates": []
}

Implement the supplied accepted five-step blueprint and public contract as a
new offline Python 3.12 standard-library benchmark. Use the blueprint task_id
exactly. Do not refer to or copy any existing benchmark task or upstream code.

Generate only:

- a readable starter package under `environment/codebase/<package>/`, with
  `__init__.py`, explicit exception classes, and meaningful modules;
- complete replacement solution files under each of exactly five
  `steps/<number-name>/solution/files/` directories;
- executable `solution/solve.sh` for every Step, honoring `TDF_WORKSPACE` and
  copying only its declared replacement files.

Use the exact five Step names, public APIs, return shapes, ordering,
exceptions, and semantics in the supplied artifacts. Starter code must be
syntactically valid and partially useful, but each successive Step must fail
at least one critical assigned behavior until its solution is applied.
Applying solutions cumulatively must produce the complete Oracle.

Persistence and recovery must be deterministic: canonical encodings, explicit
injected clocks/sequence inputs where relevant, safe temporary files and
`os.replace`. Audit/validation operations are read-only. Never use random,
UUID, process-salted hash(), wall-clock time, locale, network, races, or
host-dependent ordering.

Code must be complete and readable, without TODOs, ellipses, skipped behavior,
compressed generated one-liners, or prose placeholders. Keep scope bounded;
prefer a clear 500-1,200 line educational implementation over cosmetic size.
Internally check imports, paths, signatures, cumulative replacements, syntax,
and deterministic behavior before returning.
