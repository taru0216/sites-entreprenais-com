"""
tests/unit/test_select_template.py

scripts/select_template.py のユニットテスト（#78）
飲食店カテゴリ → デザインテンプレート自動選択ロジックを検証する。

work-retty PR #276 の tests/unit/test_select_template.py を
factory-entreprenaisan-com に移植（35件テスト）。
"""
import json
import sys
import unittest
from pathlib import Path

# プロジェクトルートを sys.path に追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.select_template import (
    TEMPLATE_A,
    TEMPLATE_B,
    TEMPLATE_C,
    select_template,
    select_template_from_store,
)


class TestSelectTemplate(unittest.TestCase):
    """select_template() — カテゴリ名 → テンプレート選択"""

    # --- Pattern A: ストーリードリブン ---
    def test_pattern_a_cafe(self):
        self.assertEqual(select_template("カフェ"), TEMPLATE_A)

    def test_pattern_a_bakery(self):
        self.assertEqual(select_template("パン屋"), TEMPLATE_A)

    def test_pattern_a_sweets(self):
        self.assertEqual(select_template("スイーツ"), TEMPLATE_A)

    def test_pattern_a_cake(self):
        self.assertEqual(select_template("ケーキ屋"), TEMPLATE_A)

    def test_pattern_a_takeout(self):
        self.assertEqual(select_template("テイクアウト"), TEMPLATE_A)

    def test_pattern_a_veggie(self):
        self.assertEqual(select_template("野菜料理"), TEMPLATE_A)

    # --- Pattern B: コンバージョン直球型 ---
    def test_pattern_b_yakiniku(self):
        self.assertEqual(select_template("焼肉"), TEMPLATE_B)

    def test_pattern_b_sushi(self):
        self.assertEqual(select_template("寿司"), TEMPLATE_B)

    def test_pattern_b_teppan(self):
        self.assertEqual(select_template("鉄板焼き"), TEMPLATE_B)

    def test_pattern_b_steak(self):
        self.assertEqual(select_template("ステーキ"), TEMPLATE_B)

    def test_pattern_b_french(self):
        self.assertEqual(select_template("フレンチ"), TEMPLATE_B)

    def test_pattern_b_italian(self):
        self.assertEqual(select_template("イタリアン"), TEMPLATE_B)

    def test_pattern_b_japanese(self):
        self.assertEqual(select_template("日本料理"), TEMPLATE_B)

    def test_pattern_b_kaiseki(self):
        self.assertEqual(select_template("懐石料理"), TEMPLATE_B)

    def test_pattern_b_kappo(self):
        self.assertEqual(select_template("割烹・小料理屋"), TEMPLATE_B)

    # --- Pattern C: コンテンツ更新型（デフォルト）---
    def test_pattern_c_izakaya(self):
        self.assertEqual(select_template("居酒屋"), TEMPLATE_C)

    def test_pattern_c_bar(self):
        self.assertEqual(select_template("バー"), TEMPLATE_C)

    def test_pattern_c_dining_bar(self):
        self.assertEqual(select_template("ダイニングバー"), TEMPLATE_C)

    def test_pattern_c_wine_bar(self):
        self.assertEqual(select_template("ワインバー"), TEMPLATE_C)

    def test_pattern_c_standing(self):
        self.assertEqual(select_template("立ち飲み"), TEMPLATE_C)

    # --- デフォルトフォールバック ---
    def test_default_unknown_category(self):
        """未知のカテゴリはデフォルト Pattern C にフォールバックする"""
        self.assertEqual(select_template("ハンバーガー"), TEMPLATE_C)

    def test_default_empty_category(self):
        """空のカテゴリは Pattern C にフォールバックする"""
        self.assertEqual(select_template(""), TEMPLATE_C)

    def test_default_none_like_empty(self):
        """None 相当の空文字は Pattern C にフォールバックする"""
        self.assertEqual(select_template(""), TEMPLATE_C)

    # --- 部分一致フォールバック ---
    def test_partial_match_b(self):
        """「イタリアン」を含む複合カテゴリは Pattern B に（部分一致）"""
        self.assertEqual(select_template("ビストロ（イタリアン）"), TEMPLATE_B)

    def test_partial_match_a(self):
        """「カフェ」を含む複合カテゴリは Pattern A に（部分一致）"""
        self.assertEqual(select_template("カフェ・スイーツ"), TEMPLATE_A)


class TestSelectTemplateFromStore(unittest.TestCase):
    """select_template_from_store() — store.json dict からテンプレート選択"""

    def _make_store(self, category="", template_pattern=None):
        store = {
            "retty_id": "100000000001",
            "slug": "test",
            "hp_status": "not_generated",
            "name": "テスト店",
            "category": category,
        }
        if template_pattern is not None:
            store["template_pattern"] = template_pattern
        return store

    def test_auto_category_yakiniku(self):
        store = self._make_store(category="焼肉")
        self.assertEqual(select_template_from_store(store), TEMPLATE_B)

    def test_auto_category_cafe(self):
        store = self._make_store(category="カフェ")
        self.assertEqual(select_template_from_store(store), TEMPLATE_A)

    def test_auto_category_izakaya(self):
        store = self._make_store(category="居酒屋")
        self.assertEqual(select_template_from_store(store), TEMPLATE_C)

    def test_explicit_override_takes_precedence(self):
        """template_pattern が明示されている場合は category より優先される"""
        store = self._make_store(category="焼肉", template_pattern=TEMPLATE_A)
        self.assertEqual(select_template_from_store(store), TEMPLATE_A)

    def test_explicit_override_b_on_cafe(self):
        """カフェでも template_pattern=B を明示すれば B が返る"""
        store = self._make_store(category="カフェ", template_pattern=TEMPLATE_B)
        self.assertEqual(select_template_from_store(store), TEMPLATE_B)

    def test_invalid_explicit_falls_back(self):
        """不正な template_pattern は無視してカテゴリ判定する"""
        store = self._make_store(category="焼肉", template_pattern="restaurant-unknown")
        self.assertEqual(select_template_from_store(store), TEMPLATE_B)

    def test_no_category_no_explicit(self):
        """category も template_pattern もない場合はデフォルト Pattern C"""
        store = self._make_store(category="")
        self.assertEqual(select_template_from_store(store), TEMPLATE_C)


class TestTemplateConstants(unittest.TestCase):
    """テンプレート名定数の検証"""

    def test_template_a_name(self):
        self.assertEqual(TEMPLATE_A, "restaurant-pattern-a")

    def test_template_b_name(self):
        self.assertEqual(TEMPLATE_B, "restaurant-pattern-b")

    def test_template_c_name(self):
        self.assertEqual(TEMPLATE_C, "restaurant-pattern-c")


if __name__ == "__main__":
    unittest.main()
