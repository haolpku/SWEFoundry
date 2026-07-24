# Open-source synthesis references

The factory deliberately reuses design patterns rather than vendoring entire frameworks into every task.

## Directly adopted now

- **SWE-smith (MIT):** generate code mutations, execute them in isolated repository images, compare pre-gold and post-gold tests, and retain only mutations that cause observable failures. The factory applies this idea to starter defects and task-specific flawed patches; a generated patch is not accepted merely because it looks plausible.
- **Frontier-Bench / Terminal-Bench 3 task rubrics:** automated gates cover functional verification, instruction-test alignment, deterministic reproduction, essential rather than clerical difficulty, reviewability, separate-verifier inputs, environment hygiene, schema precision, and instruction concision.
- **Harbor:** current execution, Oracle, Nop, artifact isolation, trajectories, rewards, and retry evidence.

## Planned for rollout and scale

- **OpenDCAI AgentFlow (Apache-2.0):** trajectory sampling, selection, and environment-grounded synthesis after task packages are executable.
- **OpenDCAI DataFlow (Apache-2.0) or distilabel (Apache-2.0):** provider-neutral generation, judge/refine stages, structured outputs, batching, retry, provenance, and model-feedback filtering when production grows beyond the ten-demo batch.
- **Data-Juicer (Apache-2.0):** large-scale operator execution, distributed filtering, deduplication, tracing, and bad-case analysis for 1,000/10,000-task production.

## Why not install everything now

At ten tasks, heavy Ray- or dataset-stack dependencies would add more infrastructure failure modes than value. The current lightweight synthesis client records raw outputs, response IDs, model names, token usage, and reviews. Framework migration should preserve that evidence schema and occur only when batching, recovery, or throughput becomes the bottleneck.
