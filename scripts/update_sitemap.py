#!/usr/bin/env python3
"""update_sitemap.py — stores/ を走査して sitemap.json / search-index.json を再生成する。

- sitemap.json: 全店舗の retty_id / slug / name / 最終クロール日時の一覧
- search-index.json: Fuse.js 用の検索インデックス（name / category / address / nearest_station）

使い方:
  python3 scripts/update_sitemap.py --stores-dir stores
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone


def load_stores(stores_dir: str) -> list[dict]:
    stores = []
    for path in sorted(glob.glob(os.path.join(stores_dir, "*", "*", "store.json"))):
        try:
            with open(path, encoding="utf-8") as f:
                stores.append(json.load(f))
        except Exception as e:  # noqa: BLE001
            print(f"[WARN] failed to read {path}: {e}", file=sys.stderr)
    return stores


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stores-dir", default="stores")
    args = ap.parse_args()

    stores = load_stores(args.stores_dir)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    sitemap = {
        "generated_at": now,
        "count": len(stores),
        "stores": [
            {
                "retty_id": s.get("retty_id"),
                "slug": s.get("slug"),
                "name": s.get("name"),
                "category": s.get("category"),
                "hp_status": s.get("hp_status"),
                "last_crawled": s.get("last_crawled"),
            }
            for s in stores
        ],
    }

    search_index = [
        {
            "retty_id": s.get("retty_id"),
            "slug": s.get("slug"),
            "name": s.get("name"),
            "category": s.get("category"),
            "categories": s.get("categories", []),
            "address": s.get("address"),
            "nearest_station": s.get("nearest_station"),
        }
        for s in stores
    ]

    sitemap_path = os.path.join(args.stores_dir, "sitemap.json")
    index_path = os.path.join(args.stores_dir, "search-index.json")
    with open(sitemap_path, "w", encoding="utf-8") as f:
        json.dump(sitemap, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(search_index, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"[update_sitemap] {len(stores)} stores -> {sitemap_path}, {index_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
