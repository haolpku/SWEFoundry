Return only one valid JSON array containing exactly ten objects. Do not use
Markdown or commentary.

Propose a diverse portfolio of ten premium five-step Greenfield terminal
benchmark topics. They must be materially different from these frozen or pilot
themes:

- partitioned stream log;
- blob/object store;
- workflow scheduler;
- feature platform;
- package resolver;
- metrics engine;
- mail service;
- data warehouse;
- trust store;
- numerical optimization pipeline;
- GTFS transit planner and fare ledger.

Portfolio constraints:

- exactly ten different domains;
- no more than two tasks primarily centered on SQLite, transaction protocols,
  generic recovery journals, or generic CRUD;
- at least two tasks centered on filesystem/process/OS behavior;
- at least two tasks centered on a real file format or open specification;
- at least one networking/protocol task that is fully testable offline;
- at least one developer-tooling task;
- at least one scientific or media-processing task that is not an optimizer;
- Python 3.12 standard library only;
- no runtime network;
- realistic persistent state, recovery, migration, integrity, or replay
  semantics;
- bounded enough for a five-step educational codebase;
- deterministic black-box verification;
- no copied upstream code.

Use exactly these top-level keys for every object:

id, title, domain, source_uri, license, provenance, text, capabilities, stages

Requirements:

- id is a short lowercase hyphenated identifier;
- source_uri is an authoritative open-source project or specification;
- license is the verified source/specification license;
- provenance is
  {"kind":"open-source-concept-study","copied_code":false,
  "review_required":true};
- text describes the engineering narrative and contains multiple signals among
  atomicity, durability, recovery, migration, integrity, idempotency, replay;
- capabilities contains exactly five distinct capabilities;
- stages contains exactly five ordered objects.

Each stage must contain exactly:

id, title, instruction, public_api, public_cases, hidden_categories, mutant

Every stage:

- has an instruction of at least 20 words defining observable behavior;
- has a nonempty array of exact Python class/function signatures;
- has at least two named public behavior cases;
- has at least three hidden semantic categories;
- has a deterministic mutant object with exactly `name` and
  `deterministic_fault`;
- never relies on hash(), random, wall-clock time, UUID, races, network state,
  locale, or host-specific ordering.

Step 5 must integrate and regress Steps 1-4. Public return types, exception
types, canonical ordering, read-only validation behavior, and recovery outcomes
must be explicit. Avoid ten renamed variants of the same transactional store.
