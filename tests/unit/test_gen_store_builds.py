#!/usr/bin/env python3
"""gen_store_builds.py のユニットテスト（外部通信なし・一時ディレクトリ使用）。"""
import importlib
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import gen_store_builds as g  # noqa: E402


class TestRender(unittest.TestCase):
    def test_per_store_build_references_macro_and_id(self):
        files = g.render_store_files([("46", "100000003346")])
        rel = os.path.join("stores", "46", "100000003346", "BUILD.bazel")
        self.assertIn(rel, files)
        content = files[rel]
        self.assertIn("foodre_site_package", content)
        self.assertIn('retty_id = "100000003346"', content)
        self.assertIn('load("//bazel:astro_site.bzl"', content)

    def test_stores_aggregate_lists_all_sites(self):
        stores = [("00", "100000000200"), ("46", "100000003346")]
        files = g.render_store_files(stores)
        agg = files[os.path.join("stores", "BUILD.bazel")]
        self.assertIn("sites_aggregate", agg)
        self.assertIn('"//stores/00/100000000200:site"', agg)
        self.assertIn('"//stores/46/100000003346:site"', agg)

    def test_no_literal_double_braces_in_header(self):
        # ヘッダコメントに format エスケープ残骸 {{ }} が漏れていないこと
        files = g.render_store_files([("00", "100000000200")])
        agg = files[os.path.join("stores", "BUILD.bazel")]
        self.assertNotIn("{{", agg)
        self.assertNotIn("}}", agg)

    def test_cities_build_uses_city_macro_and_aggregate(self):
        files = g.render_cities_files(["32525"])
        rel = os.path.join("data", "cities", "BUILD.bazel")
        body = files[rel]
        self.assertIn('cities_site_package(city_code = "32525")', body)
        self.assertIn('":site_32525"', body)
        self.assertIn("sites_aggregate", body)


class TestDiscover(unittest.TestCase):
    def test_discover_stores_only_numeric_with_store_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            # 数字でない店舗 / store.json 無しは無視されること
            os.makedirs(os.path.join(tmp, "stores", "00", "100000000200"))
            open(os.path.join(tmp, "stores", "00", "100000000200", "store.json"), "w").write("{}")
            os.makedirs(os.path.join(tmp, "stores", "01", "notnumeric"))
            open(os.path.join(tmp, "stores", "01", "notnumeric", "store.json"), "w").write("{}")
            os.makedirs(os.path.join(tmp, "stores", "02", "100000000300"))  # store.json 無し
            g.REPO_ROOT = tmp
            importlib.reload  # no-op, REPO_ROOT を直接差し替え
            found = g.discover_stores()
            self.assertEqual(found, [("00", "100000000200")])

    def test_discover_cities_only_numeric_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "data", "cities"))
            open(os.path.join(tmp, "data", "cities", "32525.json"), "w").write("{}")
            open(os.path.join(tmp, "data", "cities", "README.json"), "w").write("{}")
            g.REPO_ROOT = tmp
            found = g.discover_cities()
            self.assertEqual(found, ["32525"])


if __name__ == "__main__":
    unittest.main()
