#!/usr/bin/env python3
"""crawl_retty.py — Retty 公開サイト → store.json クローラ（foodre #230 / #229）

Retty の公開エリア一覧ページをページネーション辿り、各店舗の詳細ページから
JSON-LD（schema.org/Restaurant）＋ HTML を解析して store.json を生成する。

- 内部 API（/API/）には一切アクセスしない。公開ページのみ。
- robots.txt を尊重し、リクエスト間に sleep を入れ、User-Agent を明示する。
- 外部依存なし（標準ライブラリのみ）。requests があれば使うが必須ではない。

使い方:
  python3 scripts/crawl_retty.py \
    --area-url "https://retty.me/area/PRE13/ARE7/SUB701/" \
    --max-count 50 \
    --out-dir stores \
    --sleep 1.5
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from html import unescape

USER_AGENT = (
    "foodre-crawler/0.1 (+https://retty.me; Retty foodre partnership; "
    "contact via taru0216/taruishi-masato-work-retty)"
)

# Retty 店舗詳細 URL に含まれる店舗 ID（10桁以上の数字）
RE_RETTY_ID = re.compile(r"/([0-9]{10,})/")
# エリア配下の店舗詳細リンク（例: /area/PRE13/ARE7/SUB701/100000003346/）
RE_STORE_LINK = re.compile(r'href="(/area/[A-Z0-9/]*?/([0-9]{10,})/)"')
# 「次のページへ」リンク（pager rel="next"）
RE_NEXT = re.compile(r'<a\b[^>]*?href="([^"]+)"[^>]*?rel="next"', re.S)
RE_NEXT_ALT = re.compile(r'<a\b[^>]*?rel="next"[^>]*?href="([^"]+)"', re.S)
# JSON-LD ブロック
RE_LD = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S
)
# 最寄り駅（HTML から）
RE_STATION = re.compile(r"([^\s<>\"\\]{1,18}駅[^\s<>\"\\]{0,4}徒歩[0-9]+分)")
# 写真 URL（店舗 ID を含む ximg の画像）
RE_PHOTO_TMPL = r'(https://ximg\.retty\.me/[^"\s\\]+restaurant/{rid}/[^"\s\\]+)'

BASE = "https://retty.me"


def http_get(url: str, timeout: int = 30) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
    except urllib.error.HTTPError as e:
        print(f"  [WARN] HTTP {e.code} for {url}", file=sys.stderr)
    except Exception as e:  # noqa: BLE001
        print(f"  [WARN] fetch failed {url}: {e}", file=sys.stderr)
    return None


def absolutize(href: str) -> str:
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE + href
    return BASE + "/" + href


def collect_store_ids(area_url: str, max_count: int, sleep: float) -> list[tuple[str, str]]:
    """エリア一覧をページネーション辿り (retty_id, detail_url) を収集する。"""
    seen: dict[str, str] = {}
    url = area_url
    page = 0
    while url and len(seen) < max_count:
        page += 1
        print(f"[list] page {page}: {url}")
        html = http_get(url)
        if not html:
            break
        page_found = 0
        for m in RE_STORE_LINK.finditer(html):
            path, rid = m.group(1), m.group(2)
            if rid not in seen:
                seen[rid] = absolutize(path)
                page_found += 1
            if len(seen) >= max_count:
                break
        print(f"  found {page_found} new ids (total {len(seen)})")
        # 次ページ
        nm = RE_NEXT.search(html) or RE_NEXT_ALT.search(html)
        next_url = absolutize(unescape(nm.group(1))) if nm else None
        if not next_url or next_url == url:
            break
        url = next_url
        time.sleep(sleep)
    return list(seen.items())[:max_count]


def _find_restaurant_ld(blocks: list[str]) -> dict | None:
    for b in blocks:
        try:
            data = json.loads(b)
        except Exception:  # noqa: BLE001
            continue
        items = data if isinstance(data, list) else [data]
        for it in items:
            if isinstance(it, dict) and it.get("@type") == "Restaurant":
                return it
    return None


def _parse_hours(spec) -> tuple[dict, str | None]:
    """openingHoursSpecification -> {mon: {open, close}, ...}"""
    day_map = {
        "Monday": "mon", "Tuesday": "tue", "Wednesday": "wed",
        "Thursday": "thu", "Friday": "fri", "Saturday": "sat",
        "Sunday": "sun", "PublicHolidays": "holiday",
    }
    hours: dict = {}
    if not spec:
        return hours, None
    if isinstance(spec, dict):
        spec = [spec]
    for s in spec:
        if not isinstance(s, dict):
            continue
        days = s.get("dayOfWeek") or []
        if isinstance(days, str):
            days = [days]
        opens, closes = s.get("opens"), s.get("closes")
        for d in days:
            key = day_map.get(str(d).split("/")[-1], None)
            if key:
                hours[key] = {"open": opens, "close": closes}
    return hours, None


def _parse_budget(price_range: str | None) -> tuple[dict, str | None]:
    """'ランチ予算: 〜1000円 ディナー予算: 〜8000円' -> {lunch, dinner}"""
    if not price_range:
        return {"lunch": None, "dinner": None}, None
    out = {"lunch": None, "dinner": None}
    lm = re.search(r"ランチ予算[:：]\s*([^\sディ]+)", price_range)
    dm = re.search(r"ディナー予算[:：]\s*([^\s]+)", price_range)

    def to_val(s: str | None):
        if not s:
            return None
        m = re.search(r"([0-9,]+)\s*円", s)
        if m:
            return int(m.group(1).replace(",", ""))
        return s.strip() or None

    if lm:
        out["lunch"] = to_val(lm.group(1))
    if dm:
        out["dinner"] = to_val(dm.group(1))
    return out, price_range.strip()


def _slug(name: str, rid: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not base:
        base = "store"
    return f"{base}-{rid[-6:]}"


def parse_detail(rid: str, detail_url: str, html: str) -> dict:
    blocks = RE_LD.findall(html)
    rest = _find_restaurant_ld(blocks) or {}

    name = (rest.get("name") or "").strip()
    cuisines = rest.get("servesCuisine") or []
    if isinstance(cuisines, str):
        cuisines = [cuisines]

    addr = rest.get("address") or {}
    address_parts = [
        addr.get("addressRegion", ""),
        addr.get("addressLocality", ""),
        addr.get("streetAddress", ""),
    ]
    address = "".join(p for p in address_parts if p)
    postal = addr.get("postalCode")

    hours, _ = _parse_hours(rest.get("openingHoursSpecification"))

    rating = None
    review_count = None
    agg = rest.get("aggregateRating") or {}
    if isinstance(agg, dict):
        rating = agg.get("ratingValue")
        review_count = agg.get("reviewCount")
    # priceRange / aggregateRating は LD の Restaurant 内に無い場合 HTML から補完
    price_range = rest.get("priceRange")
    if price_range is None:
        pm = re.search(r'"priceRange":"([^"]*)"', html)
        if pm:
            price_range = pm.group(1)
    if rating is None:
        rm = re.search(r'"ratingValue":([0-9.]+),"reviewCount":([0-9]+)', html)
        if rm:
            rating = float(rm.group(1))
            review_count = int(rm.group(2))
    budget, budget_raw = _parse_budget(price_range)

    geo = rest.get("geo") or {}
    geo_out = None
    if isinstance(geo, dict) and geo.get("latitude") is not None:
        geo_out = {"lat": geo.get("latitude"), "lng": geo.get("longitude")}

    # 最寄り駅
    station = None
    sm = RE_STATION.search(html)
    if sm:
        station = sm.group(1).strip()

    # 写真（重複除去・最大20枚）
    photos: list[str] = []
    photo_re = re.compile(RE_PHOTO_TMPL.format(rid=re.escape(rid)))
    main_img = rest.get("image")
    if isinstance(main_img, str):
        photos.append(main_img)
    for pm in photo_re.finditer(html):
        u = pm.group(1)
        if u not in photos:
            photos.append(u)
        if len(photos) >= 20:
            break

    # SNS / 予約 URL
    sns: dict = {}
    same_as = rest.get("sameAs") or []
    if isinstance(same_as, str):
        same_as = [same_as]
    for u in same_as:
        if "x.com" in u or "twitter.com" in u:
            sns["x"] = u
        elif "instagram.com" in u:
            sns["instagram"] = u
        elif "facebook.com" in u:
            sns["facebook"] = u
        else:
            sns.setdefault("web", u)

    reservation_url = ""
    pa = rest.get("potentialAction") or {}
    if isinstance(pa, dict):
        tgt = pa.get("target") or {}
        if isinstance(tgt, dict):
            reservation_url = tgt.get("urlTemplate") or ""

    payment = rest.get("paymentAccepted")
    if payment is None:
        pmt = re.search(r'"paymentAccepted":"([^"]*)"', html)
        if pmt:
            payment = pmt.group(1)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "retty_id": rid,
        "slug": _slug(name, rid),
        "hp_status": "not_generated",
        "last_crawled": now,
        "last_owner_update": None,
        "last_built": None,
        "name": name,
        "category": cuisines[0] if cuisines else "",
        "categories": cuisines,
        "address": address,
        "postal_code": postal,
        "tel": rest.get("telephone"),
        "hours": hours,
        "hours_raw": None,
        "budget": budget,
        "budget_raw": budget_raw,
        "geo": geo_out,
        "retty_url": rest.get("@id") or detail_url,
        "retty_photos": photos,
        "retty_rating": float(rating) if rating is not None else None,
        "retty_review_count": int(review_count) if review_count is not None else None,
        "nearest_station": station,
        "payment_accepted": payment,
        "owner_message": "",
        "owner_photos": [],
        "featured_menu": [],
        "special_info": "",
        "reservation_url": reservation_url,
        "sns": sns,
        "i18n": {
            "en": {"name": "", "description": "", "featured_menu": []},
            "zh": {}, "ko": {}, "th": {}, "vi": {}, "zh-TW": {},
        },
    }


def write_store(store: dict, out_dir: str) -> str:
    rid = store["retty_id"]
    shard = rid[-2:]
    path = os.path.join(out_dir, shard, rid, "store.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description="Retty 公開サイト → store.json クローラ")
    ap.add_argument("--area-url", required=True, help="Retty エリア一覧 URL")
    ap.add_argument("--max-count", type=int, default=50, help="最大クロール件数")
    ap.add_argument("--out-dir", default="stores", help="store.json 出力ルート")
    ap.add_argument("--sleep", type=float, default=1.5, help="リクエスト間 sleep 秒")
    args = ap.parse_args()

    print(f"[crawl_retty] area={args.area_url} max={args.max_count} sleep={args.sleep}s")
    ids = collect_store_ids(args.area_url, args.max_count, args.sleep)
    print(f"[crawl_retty] collected {len(ids)} store ids")

    ok, fail = 0, 0
    written: list[str] = []
    for i, (rid, detail_url) in enumerate(ids, 1):
        print(f"[detail {i}/{len(ids)}] {rid} {detail_url}")
        html = http_get(detail_url)
        if not html:
            fail += 1
            continue
        try:
            store = parse_detail(rid, detail_url, html)
            if not store.get("name"):
                print(f"  [WARN] no name for {rid}, skipping")
                fail += 1
            else:
                path = write_store(store, args.out_dir)
                written.append(path)
                ok += 1
                print(f"  -> {path} ({store['name']})")
        except Exception as e:  # noqa: BLE001
            print(f"  [ERROR] parse failed {rid}: {e}", file=sys.stderr)
            fail += 1
        time.sleep(args.sleep)

    print(f"\n[crawl_retty] DONE: {ok} written, {fail} failed")
    # サマリを GITHUB_OUTPUT に出す（あれば）
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"stores_written={ok}\n")
            f.write(f"stores_failed={fail}\n")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
