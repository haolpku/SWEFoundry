from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from .core import Artifact, Operator, OperatorContext, OperatorOutput


def slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized[:80] or "topic"


def unique_strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


class LoadRecordsOperator(Operator):
    name = "io.load-records"
    version = "1.0"
    output_types = {"records": "source-records"}

    def fingerprint(
        self,
        context: OperatorContext,
        config: Mapping[str, Any],
    ) -> Any:
        path = context.resolve(str(config["path"]))
        return {
            "path": str(config["path"]),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    def run(self, context, inputs, config):
        path = context.resolve(str(config["path"]))
        if path.suffix == ".jsonl":
            records = [
                json.loads(line)
                for line in path.read_text().splitlines()
                if line.strip()
            ]
        else:
            records = json.loads(path.read_text())
        if not isinstance(records, list) or not all(
            isinstance(item, dict) for item in records
        ):
            raise ValueError("io.load-records expects a list of objects")
        return {
            "records": OperatorOutput(
                "source-records",
                {"records": records, "record_count": len(records)},
            )
        }


class FindTopicOperator(Operator):
    name = "topic.find"
    version = "1.0"
    input_types = {"records": "source-records"}
    output_types = {
        "candidates": "topic-candidates",
        "rejected": "topic-rejections",
    }

    def run(self, context, inputs, config):
        minimum_score = int(config.get("minimum_score", 60))
        candidates = []
        rejected = []
        for record in inputs["records"].data["records"]:
            reasons: list[str] = []
            title = str(record.get("title", "")).strip()
            domain = str(record.get("domain", "")).strip()
            source_uri = str(record.get("source_uri", "")).strip()
            license_name = str(record.get("license", "")).strip()
            capabilities = unique_strings(record.get("capabilities"))
            stages = record.get("stages") if isinstance(record.get("stages"), list) else []
            if not title:
                reasons.append("missing title")
            if not domain:
                reasons.append("missing domain")
            if not source_uri:
                reasons.append("missing source provenance")
            if not license_name:
                reasons.append("missing license")
            if len(capabilities) < 5 and len(stages) < 5:
                reasons.append("fewer than five engineering capabilities")

            score = 0
            score += 20 if source_uri else 0
            score += 15 if license_name else 0
            score += min(25, len(capabilities) * 5)
            score += 20 if len(stages) >= 5 else 0
            text = str(record.get("text", "")).lower()
            stateful_signals = (
                "atomic",
                "durable",
                "recovery",
                "migration",
                "integrity",
                "transaction",
                "idempot",
            )
            score += min(
                20,
                4 * sum(signal in text for signal in stateful_signals),
            )
            topic_id = str(record.get("id") or slug(title))
            candidate = {
                "topic_id": topic_id,
                "title": title,
                "domain": domain,
                "source_uri": source_uri,
                "license": license_name,
                "score": score,
                "capabilities": capabilities,
                "stages": stages,
                "text": str(record.get("text", "")),
                "provenance": record.get("provenance") or {},
            }
            if reasons or score < minimum_score:
                rejected.append(
                    {
                        "topic_id": topic_id,
                        "score": score,
                        "reasons": reasons
                        + (["below minimum score"] if score < minimum_score else []),
                    }
                )
            else:
                candidates.append(candidate)
        candidates.sort(key=lambda item: (-item["score"], item["topic_id"]))
        rejected.sort(key=lambda item: item["topic_id"])
        return {
            "candidates": OperatorOutput(
                "topic-candidates",
                {"topics": candidates, "count": len(candidates)},
            ),
            "rejected": OperatorOutput(
                "topic-rejections",
                {"topics": rejected, "count": len(rejected)},
            ),
        }


class RankTopicOperator(Operator):
    name = "topic.rank"
    version = "1.0"
    input_types = {"candidates": "topic-candidates"}
    output_types = {"selected": "selected-topics"}

    def run(self, context, inputs, config):
        limit = int(config.get("limit", 10))
        per_domain = int(config.get("max_per_domain", 2))
        counts: Counter[str] = Counter()
        selected = []
        fingerprints: set[tuple[str, ...]] = set()
        for topic in inputs["candidates"].data["topics"]:
            fingerprint = tuple(sorted(slug(item) for item in topic["capabilities"]))
            if fingerprint in fingerprints:
                continue
            if counts[topic["domain"]] >= per_domain:
                continue
            selected.append(topic)
            fingerprints.add(fingerprint)
            counts[topic["domain"]] += 1
            if len(selected) >= limit:
                break
        return {
            "selected": OperatorOutput(
                "selected-topics",
                {
                    "topics": selected,
                    "count": len(selected),
                    "domain_counts": dict(sorted(counts.items())),
                },
            )
        }


class DesignMultistepOperator(Operator):
    name = "task.design-multistep"
    version = "1.0"
    input_types = {"topics": "selected-topics"}
    output_types = {"blueprints": "task-blueprints"}

    def run(self, context, inputs, config):
        task_id_prefix = str(config.get("task_id_prefix", "candidate")).strip("-")
        if not task_id_prefix or not re.fullmatch(
            r"[a-z0-9]+(?:-[a-z0-9]+)*", task_id_prefix
        ):
            raise ValueError("task_id_prefix must be lowercase kebab-case")
        blueprints = []
        for topic in inputs["topics"].data["topics"]:
            supplied = topic.get("stages") or []
            if supplied:
                stages = [dict(stage) for stage in supplied[:5]]
            else:
                stages = [
                    {
                        "id": f"{index}-{slug(capability)}",
                        "title": capability,
                        "instruction": (
                            f"Implement the {capability} capability according to "
                            "the local architecture and public API contract."
                        ),
                        "public_api": [],
                        "public_cases": [],
                        "hidden_categories": [],
                        "mutant": {},
                    }
                    for index, capability in enumerate(topic["capabilities"][:5], 1)
                ]
            for index, stage in enumerate(stages, 1):
                stage.setdefault("id", f"{index}-{slug(stage.get('title', 'step'))}")
                stage.setdefault("title", f"Step {index}")
                stage.setdefault("instruction", "")
                stage.setdefault("public_api", [])
                stage.setdefault("public_cases", [])
                stage.setdefault("hidden_categories", [])
                stage.setdefault("mutant", {})
            blueprints.append(
                {
                    "schema_version": "1.0",
                    "task_id": f"{task_id_prefix}-{topic['topic_id']}",
                    "topic_id": topic["topic_id"],
                    "title": topic["title"],
                    "domain": topic["domain"],
                    "source": {
                        "uri": topic["source_uri"],
                        "license": topic["license"],
                        "provenance": topic["provenance"],
                    },
                    "trajectory_shape": "five-step-progressive-greenfield",
                    "steps": stages,
                    "release_status": "draft",
                    "difficulty": "uncalibrated",
                }
            )
        return {
            "blueprints": OperatorOutput(
                "task-blueprints",
                {"blueprints": blueprints, "count": len(blueprints)},
            )
        }


class QualityGateOperator(Operator):
    name = "quality.blueprint-gate"
    version = "1.0"
    input_types = {"blueprints": "task-blueprints"}
    output_types = {
        "accepted": "accepted-blueprints",
        "report": "quality-gate-report",
    }

    def run(self, context, inputs, config):
        accepted = []
        reports = []
        for blueprint in inputs["blueprints"].data["blueprints"]:
            errors = []
            if len(blueprint["steps"]) != 5:
                errors.append("exactly five steps required")
            if not blueprint["source"]["uri"] or not blueprint["source"]["license"]:
                errors.append("source URI and license required")
            for index, step in enumerate(blueprint["steps"], 1):
                prefix = f"step {index}"
                if len(str(step.get("instruction", "")).split()) < 12:
                    errors.append(f"{prefix}: instruction too short")
                if not step.get("public_api"):
                    errors.append(f"{prefix}: public API missing")
                if len(step.get("public_cases", [])) < 2:
                    errors.append(f"{prefix}: fewer than two public cases")
                if len(step.get("hidden_categories", [])) < 2:
                    errors.append(f"{prefix}: insufficient hidden semantic coverage")
                mutant = step.get("mutant") or {}
                if not mutant.get("name") or not mutant.get("deterministic_fault"):
                    errors.append(f"{prefix}: deterministic mutant missing")
                forbidden = str(mutant).lower()
                if any(
                    marker in forbidden
                    for marker in ("hash(", "random.", "time.time", "uuid4")
                ):
                    errors.append(f"{prefix}: nondeterministic mutant")
            passed = not errors
            reports.append(
                {
                    "task_id": blueprint["task_id"],
                    "passed": passed,
                    "errors": errors,
                }
            )
            if passed:
                accepted.append(blueprint)
        return {
            "accepted": OperatorOutput(
                "accepted-blueprints",
                {"blueprints": accepted, "count": len(accepted)},
            ),
            "report": OperatorOutput(
                "quality-gate-report",
                {
                    "reports": reports,
                    "accepted": len(accepted),
                    "rejected": len(reports) - len(accepted),
                    "passed": bool(reports) and len(accepted) == len(reports),
                },
            ),
        }


class CompileContractOperator(Operator):
    name = "contract.compile"
    version = "1.0"
    input_types = {"blueprints": "accepted-blueprints"}
    output_types = {"contracts": "public-contracts"}

    def run(self, context, inputs, config):
        contracts = []
        for blueprint in inputs["blueprints"].data["blueprints"]:
            seen_step_ids: set[str] = set()
            steps = []
            for index, step in enumerate(blueprint["steps"], 1):
                step_id = str(step["id"])
                if step_id in seen_step_ids:
                    raise ValueError(
                        f"{blueprint['task_id']}: duplicate step id {step_id}"
                    )
                seen_step_ids.add(step_id)
                public_api = unique_strings(step.get("public_api"))
                public_cases = unique_strings(step.get("public_cases"))
                if len(public_api) != len(step["public_api"]):
                    raise ValueError(
                        f"{blueprint['task_id']}.{step_id}: duplicate public API"
                    )
                steps.append(
                    {
                        "position": index,
                        "step_id": step_id,
                        "instruction": str(step["instruction"]).strip(),
                        "public_api": public_api,
                        "public_cases": public_cases,
                        "smoke_required": True,
                    }
                )
            contracts.append(
                {
                    "task_id": blueprint["task_id"],
                    "contract_version": "1.0",
                    "trajectory_shape": blueprint["trajectory_shape"],
                    "steps": steps,
                    "final_step_must_regress_all_prior_steps": True,
                    "agent_visible": True,
                }
            )
        return {
            "contracts": OperatorOutput(
                "public-contracts",
                {"contracts": contracts, "count": len(contracts)},
            )
        }


class PlanMutantsOperator(Operator):
    name = "mutant.plan"
    version = "1.0"
    input_types = {"blueprints": "accepted-blueprints"}
    output_types = {"plan": "mutant-plan"}

    def run(self, context, inputs, config):
        mutants = []
        for blueprint in inputs["blueprints"].data["blueprints"]:
            for position, step in enumerate(blueprint["steps"], 1):
                mutant = step["mutant"]
                mutants.append(
                    {
                        "mutant_id": (
                            f"{blueprint['task_id']}--{position:02d}--"
                            f"{slug(mutant['name'])}"
                        ),
                        "task_id": blueprint["task_id"],
                        "step_id": step["id"],
                        "step_position": position,
                        "name": mutant["name"],
                        "deterministic_fault": mutant["deterministic_fault"],
                        "must_score": 0,
                        "repeat_count": int(config.get("repeat_count", 3)),
                    }
                )
        return {
            "plan": OperatorOutput(
                "mutant-plan",
                {
                    "mutants": mutants,
                    "count": len(mutants),
                    "covers_final_step": all(
                        any(
                            mutant["task_id"] == blueprint["task_id"]
                            and mutant["step_position"] == 5
                            for mutant in mutants
                        )
                        for blueprint in inputs["blueprints"].data["blueprints"]
                    ),
                },
            )
        }


class PlanAuditOperator(Operator):
    name = "quality.audit-plan"
    version = "1.0"
    input_types = {
        "blueprints": "accepted-blueprints",
        "contracts": "public-contracts",
        "mutants": "mutant-plan",
    }
    output_types = {"plan": "audit-plan"}

    def run(self, context, inputs, config):
        contracts = {
            item["task_id"]: item
            for item in inputs["contracts"].data["contracts"]
        }
        mutants = inputs["mutants"].data["mutants"]
        task_plans = []
        for blueprint in inputs["blueprints"].data["blueprints"]:
            task_id = blueprint["task_id"]
            task_mutants = [
                mutant for mutant in mutants if mutant["task_id"] == task_id
            ]
            if task_id not in contracts:
                raise ValueError(f"{task_id}: public contract missing")
            if {item["step_position"] for item in task_mutants} != set(range(1, 6)):
                raise ValueError(f"{task_id}: mutants must cover all five steps")
            task_plans.append(
                {
                    "task_id": task_id,
                    "gates": [
                        {"name": "schema", "expected": "pass"},
                        {"name": "public-contract", "expected": "50/50 semantics"},
                        {"name": "oracle", "expected": "5/5 strict steps"},
                        {"name": "starter", "expected": "0/5 strict steps"},
                        {
                            "name": "mutants",
                            "expected": f"{len(task_mutants)}/{len(task_mutants)} rejected",
                        },
                        {"name": "isolation-probe", "expected": "pass"},
                        {
                            "name": "determinism-repeat",
                            "expected": f"{int(config.get('repeat_count', 3))} identical runs",
                        },
                    ],
                    "release_reward": "strict-binary-final",
                    "auxiliary_reward_allowed": True,
                }
            )
        return {
            "plan": OperatorOutput(
                "audit-plan",
                {
                    "tasks": task_plans,
                    "task_count": len(task_plans),
                    "required_status_after_pass": "verifier-audited",
                },
            )
        }


class RolloutPlanOperator(Operator):
    name = "rollout.plan"
    version = "1.0"
    input_types = {"blueprints": "accepted-blueprints"}
    output_types = {"plan": "rollout-plan"}

    def run(self, context, inputs, config):
        models = config.get("model_families") or []
        attempts = int(config.get("attempts", 3))
        shard_size = int(config.get("shard_size", 100))
        if len(models) < 2:
            raise ValueError("rollout.plan requires at least two model families")
        jobs = []
        for blueprint in inputs["blueprints"].data["blueprints"]:
            for model in models:
                family = str(model["family"])
                model_id = str(model["model"])
                for attempt in range(1, attempts + 1):
                    jobs.append(
                        {
                            "job_id": (
                                f"{blueprint['task_id']}--{slug(family)}--"
                                f"{attempt:03d}"
                            ),
                            "task_id": blueprint["task_id"],
                            "model_family": family,
                            "model": model_id,
                            "attempt": attempt,
                            "clean_workspace": True,
                            "record_trajectory": True,
                        }
                    )
        shards = [
            {
                "shard_id": f"rollout-{start // shard_size:05d}",
                "jobs": [job["job_id"] for job in jobs[start : start + shard_size]],
            }
            for start in range(0, len(jobs), shard_size)
        ]
        return {
            "plan": OperatorOutput(
                "rollout-plan",
                {
                    "jobs": jobs,
                    "job_count": len(jobs),
                    "model_families": sorted(
                        {job["model_family"] for job in jobs}
                    ),
                    "attempts_per_model": attempts,
                    "shards": shards,
                },
            )
        }


class PackagePlanOperator(Operator):
    name = "release.package-plan"
    version = "1.0"
    input_types = {
        "blueprints": "accepted-blueprints",
        "contracts": "public-contracts",
        "audit": "audit-plan",
        "rollouts": "rollout-plan",
    }
    output_types = {"plan": "release-package-plan"}

    def run(self, context, inputs, config):
        rollout_jobs = inputs["rollouts"].data["jobs"]
        model_families = inputs["rollouts"].data["model_families"]
        packages = []
        for blueprint in inputs["blueprints"].data["blueprints"]:
            task_id = blueprint["task_id"]
            task_jobs = [job for job in rollout_jobs if job["task_id"] == task_id]
            packages.append(
                {
                    "task_id": task_id,
                    "required_directories": [
                        "environment",
                        "instructions",
                        "solution",
                        "tests",
                        "verifier/anti_cheat",
                        "knowledge",
                    ],
                    "required_records": [
                        "task.json",
                        "provenance.json",
                        "public-contract.json",
                        "audit-report.json",
                        "rollout-summary.json",
                    ],
                    "rollout_job_count": len(task_jobs),
                    "model_families": model_families,
                    "manifest": "MANIFEST.sha256",
                }
            )
        return {
            "plan": OperatorOutput(
                "release-package-plan",
                {
                    "packages": packages,
                    "count": len(packages),
                    "static_candidate_label": (
                        "post-contract-calibration-smoke-complete"
                    ),
                    "release_label": "full-calibration-required",
                    "blockers": [
                        "audit execution evidence is not yet attached",
                        "cross-family repeated rollout results are not yet attached",
                        "human approval is not yet attached",
                    ],
                },
            )
        }


def builtin_registry() -> dict[str, Operator]:
    operators = [
        LoadRecordsOperator(),
        FindTopicOperator(),
        RankTopicOperator(),
        DesignMultistepOperator(),
        QualityGateOperator(),
        CompileContractOperator(),
        PlanMutantsOperator(),
        PlanAuditOperator(),
        RolloutPlanOperator(),
        PackagePlanOperator(),
    ]
    return {operator.name: operator for operator in operators}
