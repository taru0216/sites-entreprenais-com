#!/usr/bin/env python3
"""validate_store.py — store.json を store.schema.json に対して検証する（#229）。

jsonschema が利用可能ならそれを使い、なければ必須フィールド・型の軽量チェックに
フォールバックする（外部依存なしで CI を通すため）。

使い方:
  python3 scripts/validate_store.py stores/46/100000003346/store.json
  python3 scripts/validate_store.py --all stores
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "stores", "store.schema.json")


def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def lightweight_validate(store: dict) -> list[str]:
    """jsonschema 不在時の軽量検証。必須・主要型のみ確認。"""
    errors: list[str] = []
    required = ["retty_id", "slug", "hp_status", "name"]
    for k in required:
        if k not in store or store[k] in (None, ""):
            errors.append(f"missing required field: {k}")
    rid = store.get("retty_id", "")
    if rid and not re.fullmatch(r"[0-9]{10,}", str(rid)):
        errors.append(f"retty_id must be 10+ digits: {rid!r}")
    hp = store.get("hp_status")
    if hp not in (None, "not_generated", "generated", "published", "archived"):
        errors.append(f"invalid hp_status: {hp!r}")
    if "retty_rating" in store and store["retty_rating"] is not None:
        if not isinstance(store["retty_rating"], (int, float)):
            errors.append("retty_rating must be number or null")
    if "retty_review_count" in store and store["retty_review_count"] is not None:
        if not isinstance(store["retty_review_count"], int):
            errors.append("retty_review_count must be integer or null")
    return errors


def validate_one(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        store = json.load(f)
    try:
        import jsonschema  # type: ignore

        schema = load_schema()
        v = jsonschema.Draft7Validator(schema)
        return [f"{'/'.join(map(str, e.path))}: {e.message}" for e in v.iter_errors(store)]
    except ImportError:
        return lightweight_validate(store)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", help="store.json path(s)")
    ap.add_argument("--all", metavar="STORES_DIR", help="STORES_DIR 配下の全 store.json を検証")
    args = ap.parse_args()

    paths = list(args.paths)
    if args.all:
        paths += sorted(glob.glob(os.path.join(args.all, "*", "*", "store.json")))
    if not paths:
        print("no store.json paths given", file=sys.stderr)
        return 2

    total_err = 0
    for p in paths:
        errs = validate_one(p)
        if errs:
            total_err += len(errs)
            print(f"FAIL {p}")
            for e in errs:
                print(f"   - {e}")
        else:
            print(f"OK   {p}")
    print(f"\n[validate_store] {len(paths)} files, {total_err} errors")
    return 0 if total_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
