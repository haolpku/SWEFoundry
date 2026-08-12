# Repair the JSONL ledger

The repository contains `jsonl_ledger.py`. Repair it without changing the
public API:

```python
append_event(lines: list[str], event: dict) -> list[str]
replay(lines: list[str]) -> dict
```

Requirements:

- Every event has exactly `id`, `account`, and `delta`.
- `id` and `account` are non-empty strings. `delta` is an integer, but booleans
  are not integers for this contract.
- `append_event` rejects a duplicate `id` with `ValueError` and does not mutate
  its input list.
- Appended JSON is canonical: UTF-8 text, sorted keys, compact separators, and
  one trailing newline.
- `replay` rejects malformed JSON, invalid events, and duplicate IDs with
  `ValueError`.
- Replay returns `{"balances": ..., "event_count": ...}`. Balance keys are
  sorted lexicographically and zero balances are retained.
- Processing is deterministic and must not access the network or clock.

Run any local checks you create, but the final score comes from hidden tests.
