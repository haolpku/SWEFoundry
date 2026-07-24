Return only one valid JSON array containing exactly ten corrected topic
objects. Do not use Markdown or commentary.

Act as an adversarial benchmark portfolio reviewer. Review the supplied ten
Topic objects and repair or replace weak candidates.

Hard gates:

- ten unique domains and ten materially different codebase shapes;
- no overlap with the eleven frozen/pilot themes listed in the original prompt;
- authoritative source URI and license must be plausible and internally
  consistent; uncertain provenance must be replaced, not guessed;
- exact five capabilities and five stages per Topic;
- public API names and return/exception behavior must be unambiguous;
- hidden checks must be inferable from instructions and public contract;
- Step 5 must run meaningful regressions for Steps 1-4;
- all mutants must be deterministic and mechanically testable;
- no generic CRUD, cosmetic domain renaming, live network, non-stdlib package,
  uncontrolled concurrency, wall-clock, random, UUID, hash(), or locale
  dependence;
- implementation scope must fit a five-step Python standard-library task;
- portfolio must vary storage form: do not make most tasks JSON transactional
  databases.

Preserve the exact object/stage shapes from the original prompt. You may change
IDs, sources, APIs, Steps, or replace an entire candidate to satisfy the gates.
