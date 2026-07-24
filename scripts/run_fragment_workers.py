#!/usr/bin/env python3
"""Run model fragment workers concurrently without persisting credentials."""

from __future__ import annotations

import argparse
import concurrent.futures
import http.client
import json
import os
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path

from terminal_data_factory.operators.core import atomic_json


def call_worker(
    *,
    task_id: str,
    stage: str,
    model: str,
    base_url: str,
    token: str,
    prompt: str,
    inputs_root: Path,
    fragments_root: Path,
    max_tokens: int,
    reasoning_effort: str,
    retries: int,
) -> dict:
    output = fragments_root / task_id / f"{stage}.json"
    metadata = fragments_root / task_id / f"{stage}.meta.json"
    if output.is_file() and metadata.is_file():
        return {"task_id": task_id, "stage": stage, "status": "cached"}
    contexts = [
        inputs_root / "blueprints" / f"{task_id}.json",
        inputs_root / "contracts" / f"{task_id}.json",
    ]
    if stage == "verification":
        contexts.append(fragments_root / task_id / "core.json")
    user = prompt
    for context in contexts:
        if not context.is_file():
            raise FileNotFoundError(context)
        user += f"\n\n===== CONTEXT: {context.name} =====\n"
        user += context.read_text()
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a principal benchmark engineer. Return only the "
                    "requested valid JSON and make every file executable and auditable."
                ),
            },
            {"role": "user", "content": user},
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "reasoning_effort": reasoning_effort,
    }
    body = json.dumps(payload, ensure_ascii=False).encode()
    last_error: Exception | None = None
    started = time.monotonic()
    for attempt in range(1, retries + 1):
        request = urllib.request.Request(
            base_url.rstrip("/") + "/v1/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                raw = json.loads(response.read().decode())
            content = raw["choices"][0]["message"]["content"].strip()
            parsed = json.loads(content)
            if parsed.get("schema_version") != "1.0":
                raise ValueError("fragment schema_version differs")
            if parsed.get("task_id") != task_id:
                raise ValueError("fragment task_id differs")
            if parsed.get("fragment") != stage:
                raise ValueError("fragment stage differs")
            if not isinstance(parsed.get("files"), list) or not parsed["files"]:
                raise ValueError("fragment files are empty")
            atomic_json(output, parsed)
            atomic_json(
                metadata,
                {
                    "schema_version": "1.0",
                    "task_id": task_id,
                    "fragment": stage,
                    "model": model,
                    "response_id": raw.get("id"),
                    "created": raw.get("created"),
                    "finish_reason": raw.get("choices", [{}])[0].get(
                        "finish_reason"
                    ),
                    "usage": raw.get("usage"),
                    "latency_seconds": round(time.monotonic() - started, 3),
                    "attempt": attempt,
                    "endpoint": "<REDACTED_OPENAI_COMPATIBLE_ENDPOINT>",
                    "credentials_persisted": False,
                },
            )
            return {
                "task_id": task_id,
                "stage": stage,
                "status": "succeeded",
                "latency_seconds": round(time.monotonic() - started, 3),
                "usage": raw.get("usage"),
            }
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            http.client.RemoteDisconnected,
            TimeoutError,
            socket.timeout,
            KeyError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(2 ** (attempt - 1))
    return {
        "task_id": task_id,
        "stage": stage,
        "status": "failed",
        "latency_seconds": round(time.monotonic() - started, 3),
        "error": f"{type(last_error).__name__}: {last_error}",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("core", "verification"), required=True)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--base-url", default=os.environ.get("TDF_SYNTHESIS_BASE_URL"))
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--inputs-root", type=Path, required=True)
    parser.add_argument("--fragments-root", type=Path, required=True)
    parser.add_argument("--task-id", action="append")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--reasoning-effort", default="medium")
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    token = os.environ.get("TDF_SYNTHESIS_API_KEY")
    if not token:
        raise SystemExit("TDF_SYNTHESIS_API_KEY is required")
    if not args.base_url:
        raise SystemExit("--base-url or TDF_SYNTHESIS_BASE_URL is required")
    task_ids = args.task_id
    if not task_ids:
        task_ids = json.loads(
            (args.inputs_root / "TASK_INDEX.json").read_text()
        )["task_ids"]
    if len(task_ids) > 10 or len(set(task_ids)) != len(task_ids):
        raise SystemExit("task ids must be unique and no more than ten")
    prompt = args.prompt.read_text()
    max_tokens = args.max_tokens or (
        18000 if args.stage == "core" else 26000
    )
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.workers
    ) as pool:
        futures = [
            pool.submit(
                call_worker,
                task_id=task_id,
                stage=args.stage,
                model=args.model,
                base_url=args.base_url,
                token=token,
                prompt=prompt,
                inputs_root=args.inputs_root,
                fragments_root=args.fragments_root,
                max_tokens=max_tokens,
                reasoning_effort=args.reasoning_effort,
                retries=args.retries,
            )
            for task_id in task_ids
        ]
        results = [
            future.result()
            for future in concurrent.futures.as_completed(futures)
        ]
    results.sort(key=lambda item: item["task_id"])
    summary = {
        "schema_version": "1.0",
        "stage": args.stage,
        "model": args.model,
        "task_count": len(task_ids),
        "succeeded": sum(item["status"] in {"succeeded", "cached"} for item in results),
        "failed": sum(item["status"] == "failed" for item in results),
        "results": results,
    }
    atomic_json(args.summary, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
