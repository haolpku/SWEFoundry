from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Iterable


def export_jsonl_shards(records: Iterable[dict], output_dir: Path, *, prefix: str, shard_size: int = 500) -> dict:
    if shard_size < 1:
        raise ValueError("shard_size must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    temporary: list[Path] = []
    handle = None
    count = 0
    try:
        for item in records:
            if count % shard_size == 0:
                if handle is not None:
                    handle.close()
                path = output_dir / f".{prefix}-{len(temporary):05d}.jsonl.tmp"
                temporary.append(path)
                handle = path.open("w", encoding="utf-8")
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    finally:
        if handle is not None:
            handle.close()

    width = max(5, len(str(max(len(temporary) - 1, 0))))
    files: list[str] = []
    checksums: dict[str, str] = {}
    for index, path in enumerate(temporary):
        final = output_dir / f"{prefix}-{index:0{width}d}-of-{len(temporary):0{width}d}.jsonl"
        path.replace(final)
        files.append(final.name)
        checksums[final.name] = "sha256:" + hashlib.sha256(final.read_bytes()).hexdigest()
    manifest = {
        "schema_version": "hf-shards-v1",
        "format": "jsonl",
        "records": count,
        "shard_size": shard_size,
        "files": files,
        "checksums": checksums,
    }
    (output_dir / f"{prefix}-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
