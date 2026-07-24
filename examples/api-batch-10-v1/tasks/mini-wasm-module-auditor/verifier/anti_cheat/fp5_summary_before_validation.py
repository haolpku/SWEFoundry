#!/usr/bin/env python3
import os
import pathlib
import sys

root = pathlib.Path(os.environ.get('TDF_WORKSPACE', '.')).resolve()
path = root / 'environment' / 'codebase' / 'wasm_auditor' / 'audit.py'
text = path.read_text(encoding='utf-8')
old = "    symbols_list: list[WasmSymbol] = []\n    if not problems_list:\n        try:\n            symbols_list = summarize_wasm_symbols(list(sections))\n        except ValueError as exc:\n            problems_list.append(WasmProblem(\"error\", \"symbol-decode\", str(exc), -1, 0))\n            problems_list.sort(key=lambda p: (p.offset, p.code, p.message, p.section_id))\n"
new = "    symbols_list: list[WasmSymbol] = []\n    symbols_list = summarize_wasm_symbols(list(sections))\n"
if old not in text:
    print('fp5 pattern not found', file=sys.stderr)
    sys.exit(2)
path.write_text(text.replace(old, new, 1), encoding='utf-8')
