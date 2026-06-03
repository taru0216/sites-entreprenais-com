#!/usr/bin/env python3
"""crawl_retty.py のユニットテスト（外部通信なし・fixture を使用）。"""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import crawl_retty as cr  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def _read(name: str) -> str:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read()


class TestListParsing(unittest.TestCase):
    def test_store_link_regex_extracts_ids(self):
        html = _read("list_sample.html")
        ids = [m.group(2) for m in cr.RE_STORE_LINK.finditer(html)]
        self.assertIn("100000003346", ids)
        self.assertIn("100000006312", ids)
        self.assertIn("100000720212", ids)
        # PUR14 など数字 ID でないリンクは含まれない
        self.assertNotIn("14", ids)

    def test_next_page_extraction(self):
        html = _read("list_sample.html")
        m = cr.RE_NEXT.search(html) or cr.RE_NEXT_ALT.search(html)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "/area/PRE13/ARE7/SUB701/page-2/")


class TestDetailParsing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = _read("ebisu_detail_100000003346.html")
        cls.rid = "100000003346"
        cls.url = f"https://retty.me/area/PRE13/ARE7/SUB701/{cls.rid}/"
        cls.store = cr.parse_detail(cls.rid, cls.url, cls.html)

    def test_basic_fields(self):
        s = self.store
        self.assertEqual(s["retty_id"], "100000003346")
        self.assertEqual(s["name"], "恵比寿 かみくら")
        self.assertEqual(s["hp_status"], "not_generated")
        self.assertEqual(s["category"], "懐石料理")
        self.assertIn("懐石料理", s["categories"])

    def test_address_and_tel(self):
        s = self.store
        self.assertIn("東京都", s["address"])
        self.assertIn("渋谷区", s["address"])
        self.assertEqual(s["tel"], "050-5462-9922")
        self.assertEqual(s["postal_code"], "1500022")

    def test_hours_parsed(self):
        s = self.store
        self.assertIn("mon", s["hours"])
        self.assertEqual(s["hours"]["mon"]["open"], "17:00")
        self.assertEqual(s["hours"]["mon"]["close"], "23:00")

    def test_rating_and_reviews(self):
        s = self.store
        self.assertAlmostEqual(s["retty_rating"], 4.15, places=2)
        self.assertEqual(s["retty_review_count"], 10)

    def test_budget(self):
        s = self.store
        # "ディナー予算: 〜8000円"
        self.assertEqual(s["budget"]["dinner"], 8000)
        self.assertIsNotNone(s["budget_raw"])

    def test_geo(self):
        s = self.store
        self.assertIsNotNone(s["geo"])
        self.assertAlmostEqual(s["geo"]["lat"], 35.6459155, places=4)

    def test_photos_and_station(self):
        s = self.store
        self.assertTrue(len(s["retty_photos"]) >= 1)
        self.assertTrue(all(u.startswith("https://ximg.retty.me/") for u in s["retty_photos"]))
        self.assertIn("駅", s["nearest_station"] or "")

    def test_slug_and_i18n_shape(self):
        s = self.store
        self.assertTrue(s["slug"].endswith("003346"))
        self.assertIn("en", s["i18n"])

    def test_shard_path(self):
        # retty_id[-2:] = "46"
        self.assertEqual(self.rid[-2:], "46")


class TestBudgetParser(unittest.TestCase):
    def test_both(self):
        b, raw = cr._parse_budget("ランチ予算: 〜1000円 ディナー予算: 〜8000円")
        self.assertEqual(b["lunch"], 1000)
        self.assertEqual(b["dinner"], 8000)
        self.assertIsNotNone(raw)

    def test_none(self):
        b, raw = cr._parse_budget(None)
        self.assertIsNone(b["lunch"])
        self.assertIsNone(raw)


class TestRidFromUrl(unittest.TestCase):
    def test_area_url(self):
        self.assertEqual(
            cr.rid_from_url("https://retty.me/area/PRE13/ARE7/SUB701/100000003346/"),
            "100000003346",
        )

    def test_restaurant_url(self):
        self.assertEqual(
            cr.rid_from_url("https://retty.me/restaurant/100001568147/"),
            "100001568147",
        )

    def test_no_id(self):
        self.assertIsNone(cr.rid_from_url("https://retty.me/area/PRE13/"))
        self.assertIsNone(cr.rid_from_url(""))

    def test_detail_url_from_rid(self):
        self.assertEqual(
            cr.detail_url_from_rid("100000003346"),
            "https://retty.me/restaurant/100000003346/",
        )


class TestCsvTargets(unittest.TestCase):
    def _write_csv(self, text: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        self.addCleanup(os.remove, path)
        return path

    def test_retty_url_column(self):
        path = self._write_csv(
            "retty_url\n"
            "https://retty.me/area/PRE13/ARE7/SUB701/100000003346/\n"
            "https://retty.me/area/PRE13/ARE7/SUB701/100000072847/\n"
        )
        targets = cr.read_csv_targets(path)
        self.assertEqual(
            targets,
            [
                ("100000003346",
                 "https://retty.me/area/PRE13/ARE7/SUB701/100000003346/"),
                ("100000072847",
                 "https://retty.me/area/PRE13/ARE7/SUB701/100000072847/"),
            ],
        )

    def test_retty_id_column_builds_url(self):
        path = self._write_csv("retty_id\n100000003346\n")
        targets = cr.read_csv_targets(path)
        self.assertEqual(
            targets,
            [("100000003346", "https://retty.me/restaurant/100000003346/")],
        )

    def test_url_preferred_over_id(self):
        # 両列がある場合、retty_url 由来の URL がそのまま使われる
        path = self._write_csv(
            "retty_id,retty_url\n"
            "999999999999,https://retty.me/area/PRE13/ARE7/SUB701/100000003346/\n"
        )
        targets = cr.read_csv_targets(path)
        self.assertEqual(
            targets,
            [("100000003346",
              "https://retty.me/area/PRE13/ARE7/SUB701/100000003346/")],
        )

    def test_url_falls_back_to_id_when_no_id_in_url(self):
        # retty_url 列が空 / ID 抽出不能な行は retty_id 列にフォールバック
        path = self._write_csv(
            "retty_url,retty_id\n"
            ",100000003346\n"
        )
        targets = cr.read_csv_targets(path)
        self.assertEqual(
            targets,
            [("100000003346", "https://retty.me/restaurant/100000003346/")],
        )

    def test_header_case_and_whitespace_tolerant(self):
        path = self._write_csv("  Retty_URL  \nhttps://retty.me/restaurant/100000003346/\n")
        targets = cr.read_csv_targets(path)
        self.assertEqual(
            targets,
            [("100000003346", "https://retty.me/restaurant/100000003346/")],
        )

    def test_dedup_and_blank_lines(self):
        path = self._write_csv(
            "retty_id\n"
            "100000003346\n"
            "\n"
            "100000003346\n"
            "100000072847\n"
        )
        targets = cr.read_csv_targets(path)
        rids = [t[0] for t in targets]
        self.assertEqual(rids, ["100000003346", "100000072847"])

    def test_missing_required_columns_raises(self):
        path = self._write_csv("name,address\nfoo,bar\n")
        with self.assertRaises(ValueError):
            cr.read_csv_targets(path)

    def test_empty_file_raises(self):
        path = self._write_csv("")
        with self.assertRaises(ValueError):
            cr.read_csv_targets(path)

    def test_invalid_rows_skipped(self):
        # 不正な行（ID 無し）はスキップされ、有効行のみ返る
        path = self._write_csv(
            "retty_id\n"
            "not-an-id\n"
            "100000003346\n"
        )
        targets = cr.read_csv_targets(path)
        self.assertEqual(
            targets,
            [("100000003346", "https://retty.me/restaurant/100000003346/")],
        )


class TestArgparseMutualExclusion(unittest.TestCase):
    """--area-url と --csv の排他 / 必須を argparse レベルで検証する。"""

    def _run_main(self, argv):
        import contextlib
        import io
        old = sys.argv
        sys.argv = ["crawl_retty.py"] + argv
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                return cr.main()
        finally:
            sys.argv = old

    def test_neither_provided_exits(self):
        with self.assertRaises(SystemExit):
            self._run_main([])

    def test_both_provided_exits(self):
        with self.assertRaises(SystemExit):
            self._run_main([
                "--area-url", "https://retty.me/area/PRE13/ARE7/SUB701/",
                "--csv", "x.csv",
            ])


if __name__ == "__main__":
    unittest.main()
