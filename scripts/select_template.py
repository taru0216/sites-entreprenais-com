#!/usr/bin/env python3
"""
select_template.py — foodre テンプレート自動選択ロジック（#78）

store.json の category フィールドに基づき、3つのデザインパターンから
最適なテンプレートを自動選択する。

work-retty PR #276 の実装を factory-entreprenaisan-com 構造に適合させて移植。

Pattern A（ストーリードリブン）: カフェ・パン屋・スイーツ系
  - ヒーロー直下に LINE→HP 動的反映デモを統合
  - コンテンツ・ブランドストーリー重視

Pattern B（コンバージョン直球型）: 焼肉・寿司・高単価レストラン系
  - 上半分で予約完結・スマホスティッキー導線
  - 予約・集客を最優先

Pattern C（コンテンツ更新型）: 居酒屋・バー系（デフォルト）
  - NOW OPEN ライブ・店主の日誌・更新コンテンツ
  - 常連醸成・リピート重視

使用例:
    python3 scripts/select_template.py --category "カフェ"
    python3 scripts/select_template.py --store-json stores/46/100000003346/store.json

    # モジュールとして:
    from scripts.select_template import select_template
    template = select_template("焼肉")  # -> "restaurant-pattern-b"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# カテゴリ → パターン マッピング
# ---------------------------------------------------------------------------

# Pattern A: ストーリードリブン（カフェ・パン屋・スイーツ・テイクアウト系）
PATTERN_A_CATEGORIES: set[str] = {
    "カフェ",
    "パン屋",
    "スイーツ",
    "ケーキ屋",
    "テイクアウト",
    "野菜料理",
    "創作料理",
    "コーヒー専門店",
    "紅茶・ハーブティー",
    "デザート",
}

# Pattern B: コンバージョン直球型（焼肉・寿司・高単価レストラン系）
PATTERN_B_CATEGORIES: set[str] = {
    "焼肉",
    "寿司",
    "鉄板焼き",
    "ステーキ",
    "フレンチ",
    "イタリアン",
    "日本料理",
    "懐石料理",
    "割烹・小料理屋",
    "しゃぶしゃぶ",
    "すき焼き",
    "天ぷら",
    "うなぎ",
    "ふぐ",
    "カニ料理",
    "魚介・海鮮料理",
    "和食",
    "中華",
    "スペイン料理",
}

# Pattern C: コンテンツ更新型（居酒屋・バー系）— デフォルト
PATTERN_C_CATEGORIES: set[str] = {
    "居酒屋",
    "バー",
    "ダイニングバー",
    "ワインバー",
    "ビアバー・ビアホール",
    "立ち飲み",
    "焼き鳥",
    "串カツ・串揚げ",
    "お好み焼き",
    "もんじゃ焼き",
}

# テンプレートコンポーネント名（[id].astro の selectPattern と同ロジック）
TEMPLATE_A = "restaurant-pattern-a"
TEMPLATE_B = "restaurant-pattern-b"
TEMPLATE_C = "restaurant-pattern-c"
TEMPLATE_DEFAULT = "restaurant-default"  # 後方互換（= Pattern C と同等）


def select_template(category: str) -> str:
    """
    カテゴリ名からテンプレート名を返す。

    Args:
        category: store.json の category フィールド値

    Returns:
        テンプレート名（"restaurant-pattern-a" / "b" / "c"）
    """
    if not category:
        return TEMPLATE_C

    # 完全一致を優先
    if category in PATTERN_A_CATEGORIES:
        return TEMPLATE_A
    if category in PATTERN_B_CATEGORIES:
        return TEMPLATE_B
    if category in PATTERN_C_CATEGORIES:
        return TEMPLATE_C

    # 部分一致フォールバック（例: "ビストロ（イタリアン）" → Pattern B）
    for kw in PATTERN_B_CATEGORIES:
        if kw in category:
            return TEMPLATE_B
    for kw in PATTERN_A_CATEGORIES:
        if kw in category:
            return TEMPLATE_A

    # デフォルト: Pattern C
    return TEMPLATE_C


def select_template_from_store(store: dict) -> str:
    """
    store.json dict からテンプレートを選択する。

    store.json に template_pattern フィールドが明示されている場合はそれを優先する。
    （オーナー編集による手動上書き対応）

    Args:
        store: store.json を読み込んだ dict

    Returns:
        テンプレート名
    """
    # 明示的な手動指定を優先（オーナー編集）
    explicit = store.get("template_pattern")
    if explicit in (TEMPLATE_A, TEMPLATE_B, TEMPLATE_C, TEMPLATE_DEFAULT):
        return explicit

    category = store.get("category", "")
    return select_template(category)


# ---------------------------------------------------------------------------
# CLI エントリポイント
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="飲食店カテゴリからデザインテンプレートを自動選択する"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--category", "-c", help="カテゴリ名（例: カフェ）")
    group.add_argument(
        "--store-json", "-s", type=Path,
        help="store.json のパス（category フィールドを読む）"
    )
    args = parser.parse_args()

    if args.store_json:
        try:
            store = json.loads(args.store_json.read_text(encoding="utf-8"))
        except FileNotFoundError:
            print(f"ERROR: {args.store_json} が見つかりません", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"ERROR: JSON 解析エラー: {e}", file=sys.stderr)
            sys.exit(1)
        template = select_template_from_store(store)
        category = store.get("category", "(未設定)")
        print(f"{template}  # category={category!r}")
    else:
        template = select_template(args.category)
        print(template)


if __name__ == "__main__":
    main()
