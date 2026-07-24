#!/usr/bin/env python3
"""Generate bounded task-file repairs from independent QA failures."""

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
from terminal_data_factory.repair import (
    build_task_snapshot,
    classify_task_failure,
    validate_repair_payload,
)


def _call(
    *,
    task_result: dict,
    task_root: Path,
    output_root: Path,
    prompt: str,
    model: str,
    base_url: str,
    token: str,
    max_tokens: int,
    retries: int,
) -> dict:
    task_id = task_result["task_id"]
    output = output_root / task_id / "repair.json"
    metadata = output_root / task_id / "repair.meta.json"
    if output.is_file() and metadata.is_file():
        return {"task_id": task_id, "status": "cached"}
    classification = classify_task_failure(task_result)
    if not classification["repairable"]:
        return {
            "task_id": task_id,
            "status": "failed",
            "error": "task classification is not model-repairable",
        }
    snapshot = build_task_snapshot(task_root / task_id)
    user = (
        prompt
        + "\n\n===== FAILURE CLASSIFICATION =====\n"
        + json.dumps(classification, ensure_ascii=False, indent=2)
        + "\n\n===== INDEPENDENT QA RESULT =====\n"
        + json.dumps(task_result, ensure_ascii=False, indent=2)
        + "\n\n===== CURRENT TASK SNAPSHOT =====\n"
        + json.dumps(snapshot, ensure_ascii=False)
    )
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You repair executable benchmark tasks. Return only valid "
                    "JSON matching the requested repair schema."
                ),
            },
            {"role": "user", "content": user},
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "reasoning_effort": "medium",
    }
    body = json.dumps(payload, ensure_ascii=False).encode()
    started = time.monotonic()
    last_error: Exception | None = None
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
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            repair = validate_repair_payload(
                json.loads(content),
                expected_task_id=task_id,
            )
            atomic_json(output, repair)
            atomic_json(
                metadata,
                {
                    "schema_version": "1.0",
                    "task_id": task_id,
                    "model": model,
                    "response_id": raw.get("id"),
                    "created": raw.get("created"),
                    "finish_reason": raw.get("choices", [{}])[0].get(
                        "finish_reason"
                    ),
                    "usage": raw.get("usage"),
                    "attempt": attempt,
                    "latency_seconds": round(time.monotonic() - started, 3),
                    "endpoint": "<REDACTED_OPENAI_COMPATIBLE_ENDPOINT>",
                    "credentials_persisted": False,
                },
            )
            return {
                "task_id": task_id,
                "status": "succeeded",
                "attempt": attempt,
                "latency_seconds": round(time.monotonic() - started, 3),
                "usage": raw.get("usage"),
                "repair_files": len(repair["files"]),
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
        "status": "failed",
        "latency_seconds": round(time.monotonic() - started, 3),
        "error": f"{type(last_error).__name__}: {last_error}",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks-root", type=Path, required=True)
    parser.add_argument("--qa-report", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--task-id", action="append")
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("TDF_SYNTHESIS_BASE_URL"),
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-tasks", type=int, default=10)
    parser.add_argument("--max-tokens", type=int, default=24000)
    parser.add_argument("--retries", type=int, default=2)
    args = parser.parse_args()
    token = os.environ.get("TDF_SYNTHESIS_API_KEY")
    if not token:
        raise SystemExit("TDF_SYNTHESIS_API_KEY is required")
    if not args.base_url:
        raise SystemExit("--base-url or TDF_SYNTHESIS_BASE_URL is required")
    qa = json.loads(args.qa_report.read_text(encoding="utf-8"))
    selected = set(args.task_id or [])
    task_results = [
        item
        for item in qa.get("tasks", [])
        if not item.get("passed")
        and (not selected or item.get("task_id") in selected)
    ]
    if args.max_tasks < 1 or len(task_results) > args.max_tasks:
        raise SystemExit(
            f"repair target count {len(task_results)} exceeds --max-tasks "
            f"{args.max_tasks}"
        )
    prompt = args.prompt.read_text(encoding="utf-8")
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.workers
    ) as pool:
        futures = [
            pool.submit(
                _call,
                task_result=item,
                task_root=args.tasks_root,
                output_root=args.output_root,
                prompt=prompt,
                model=args.model,
                base_url=args.base_url,
                token=token,
                max_tokens=args.max_tokens,
                retries=args.retries,
            )
            for item in task_results
        ]
        results = [
            future.result()
            for future in concurrent.futures.as_completed(futures)
        ]
    results.sort(key=lambda item: item["task_id"])
    summary = {
        "schema_version": "1.0",
        "model": args.model,
        "task_count": len(results),
        "succeeded": sum(
            item["status"] in {"cached", "succeeded"} for item in results
        ),
        "failed": sum(item["status"] == "failed" for item in results),
        "results": results,
    }
    atomic_json(args.summary, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
