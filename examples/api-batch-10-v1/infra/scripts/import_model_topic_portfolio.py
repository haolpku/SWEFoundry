#!/usr/bin/env python3
"""Import a reviewed ten-topic portfolio with sanitized model provenance."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from terminal_data_factory.operators.core import atomic_json


KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EXPECTED_KEYS = {
    "id",
    "title",
    "domain",
    "source_uri",
    "license",
    "provenance",
    "text",
    "capabilities",
    "stages",
}
STAGE_KEYS = {
    "id",
    "title",
    "instruction",
    "public_api",
    "public_cases",
    "hidden_categories",
    "mutant",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--response", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit-output", type=Path, required=True)
    args = parser.parse_args()

    topics = json.loads(args.response.read_text())
    if not isinstance(topics, list) or len(topics) != 10:
        raise SystemExit("portfolio must contain exactly ten topics")
    ids: set[str] = set()
    domains: set[str] = set()
    for topic in topics:
        if not isinstance(topic, dict) or set(topic) != EXPECTED_KEYS:
            raise SystemExit("topic object keys differ")
        topic_id = topic["id"]
        if not isinstance(topic_id, str) or not KEBAB.fullmatch(topic_id):
            raise SystemExit(f"invalid topic id: {topic_id}")
        if topic_id in ids:
            raise SystemExit(f"duplicate topic id: {topic_id}")
        ids.add(topic_id)
        domains.add(str(topic["domain"]))
        if not topic["source_uri"] or not topic["license"]:
            raise SystemExit(f"{topic_id}: source/license missing")
        if len(topic["capabilities"]) != 5 or len(topic["stages"]) != 5:
            raise SystemExit(f"{topic_id}: exactly five capabilities/stages required")
        for stage in topic["stages"]:
            if set(stage) != STAGE_KEYS:
                raise SystemExit(f"{topic_id}: stage keys differ")
            if len(stage["public_cases"]) < 2 or len(stage["hidden_categories"]) < 3:
                raise SystemExit(f"{topic_id}: stage coverage too small")
            if set(stage["mutant"]) != {"name", "deterministic_fault"}:
                raise SystemExit(f"{topic_id}: mutant shape differs")
    if len(domains) != 10:
        raise SystemExit("portfolio must contain ten unique domains")

    raw_metadata = json.loads(args.metadata.read_text())
    atomic_json(args.output, topics)
    atomic_json(
        args.audit_output,
        {
            "schema_version": "1.0",
            "model": raw_metadata.get("model"),
            "response_id": raw_metadata.get("id"),
            "created": raw_metadata.get("created"),
            "finish_reason": raw_metadata.get("finish_reason"),
            "usage": raw_metadata.get("usage"),
            "endpoint": "<REDACTED_OPENAI_COMPATIBLE_ENDPOINT>",
            "credentials_persisted": False,
            "topic_count": 10,
            "topic_ids": sorted(ids),
        },
    )
    print(json.dumps({"topic_count": 10, "topic_ids": sorted(ids)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
