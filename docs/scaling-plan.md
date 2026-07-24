# Scaling from 10 families to 1,000 and 10,000 instances

The ten checked-in directories are task families, not a promise that copying each directory creates useful diversity. Scale comes from a three-level identity:

`family -> generated instance(seed, parameters, fault profile) -> rollout(model, attempt, hint condition)`

## 10 to 1,000

- Keep the ten families balanced at 100 instances each.
- Add constrained parameter generators and property-based fixture generation per family.
- Build immutable image digests once per family revision; generate evidence per instance.
- Run oracle, blank, four known-bad, and verifier determinism gates before scheduling model trials.
- Schedule 10 rollouts per instance: 10,000 trials, normally 20 shards of 500.
- Human-review all proposed releases in this first scaled wave; use labels to refine generators and verifier blind spots.

On the current three-host pool, keep the task source and immutable run manifests on `/vepfs-mlp2/c20250602/500050`, but load base images into each host's local Docker store. Start with a measured concurrency cap of four trials per host and tune from CPU, memory, Docker build queue, verifier latency, and VEPFS metadata latency rather than the hosts' nominal core count. Write active job state to host-local scratch, then atomically commit completed result/trajectory bundles and a compact summary to the shared artifact plane.

## 1,000 to 10,000

- Add more families before multiplying near-duplicate seeds; preserve the 25% category cap and measure template similarity.
- Maintain a registry of family revision, generator revision, image digest, verifier digest, instance seed, and parent provenance.
- Deduplicate instructions, evidence, solution patches, and trajectory signatures before expensive rollouts.
- Schedule 100,000 trials for ten rollouts per instance, normally 200 shards of 500.
- Use two execution pools: cheap preflight/oracle and expensive target-model rollout. Failed preflight instances never enter the expensive queue.
- Store large traces in an artifact plane and only indexed metadata/quality decisions in the catalog database.

At 10,000 instances, do not submit 100,000 model trials as one Harbor job. Materialize immutable shards with `tdf plan`, lease shards to workers, checkpoint each completed trial, and make retries idempotent on `(task_digest, instance_seed, model, attempt, hint_condition)`. Separate capacity pools for generation, Oracle/known-bad verification, and paid model rollout. Benchmark real target-agent latency and token cost before setting an ETA; the current ~30-second Oracle runtime is not a proxy for model rollout time.

## Execution records

Every job record should include task/generator/verifier digests, seed and parameters, base-image digest, Harbor version and environment import path, host, start/finish timestamps, reward vector, CTRF counts, exception class, artifact checksums, model identity, sampling configuration, and cost. `scripts/summarize_harbor_batch.py` creates the compact Oracle batch view from selected immutable Harbor job directories.

## Release gates

An instance moves through `generated -> buildable -> oracle-passed -> verifier-audited -> rollout-qualified -> failure-analyzed -> human-approved -> released`. Automated gates may reject data; only a recorded human owner can perform the final release transition. A family can be locally verifier-audited while individual generated instances remain unqualified.

Use `tdf plan` to materialize deterministic instance and shard manifests without copying task trees.
