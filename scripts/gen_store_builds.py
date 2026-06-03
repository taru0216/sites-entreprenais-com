#!/usr/bin/env python3
"""gen_store_builds.py — per-site BUILD.bazel ジェネレータ（epic #243 ②）。

各 stores/{shard}/{retty_id}/ に foodre_site_package を呼ぶ BUILD.bazel を生成し、
stores/BUILD.bazel に sites_aggregate（//stores:all）の明示リストを生成する。
cities も同様（data/cities/{code}.json → cities/BUILD.bazel）。

native.glob はサブパッケージ境界を越えないため、集約は明示リストで持つ必要がある。
店舗の追加・削除時に本スクリプトを再実行して BUILD.bazel を再生成する。

使い方:
  python3 scripts/gen_store_builds.py            # 全 BUILD.bazel を生成
  python3 scripts/gen_store_builds.py --check     # 生成物が最新か検証（CI 用・書き込みなし）
"""
import argparse
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PER_STORE_TEMPLATE = '''\
# foodre per-store ビルド（自動生成: scripts/gen_store_builds.py）。
#
# この店舗の store.json を入力に dist/foodre/{retty_id}/ を生成する。
# store.json のハッシュが変わったときだけ :site が再ビルドされる（インクリメンタル）。
# 共有テンプレート（//site-builder:template）が変わると全店舗が再ビルドされる。
#
# ビルド: bazel build //stores/{shard}/{retty_id}:site
load("//bazel:astro_site.bzl", "foodre_site_package")

package(default_visibility = ["//visibility:public"])

foodre_site_package(retty_id = "{retty_id}")
'''

STORES_AGGREGATE_HEADER = '''\
# foodre — 全店舗HPのインクリメンタルビルド（親グルーピング・自動生成）。
#
# 各 stores/{shard}/{retty_id}/ は独立 package（:site）。本ファイルは sites_aggregate
# で全 :site を明示リスト集約する（native.glob はサブパッケージ境界を越えないため）。
#
# ターゲット:
#   //stores/{shard}/{retty_id}:site  — 単一店舗HP
#   //stores:all                      — 登録済み全店舗HP の集約
#   //stores/...:site                 — ワイルドカード（全 :site を一括ビルド）
#
# 再生成: python3 scripts/gen_store_builds.py
load("//bazel:astro_site.bzl", "sites_aggregate")

package(default_visibility = ["//visibility:public"])

sites_aggregate(
    name = "all",
    sites = [
'''

CITIES_AGGREGATE_HEADER = '''\
# cities — 全自治体HPのインクリメンタルビルド（自動生成）。
#
# data/cities/{code}.json を入力に dist/cities/{code}/ を生成する per-city ターゲット。
# 共有テンプレート（//site-builder:template）が変わると全自治体が再ビルドされる。
#
# ターゲット:
#   //data/cities:site_{code}  — 単一自治体HP
#   //data/cities:all          — 全自治体HP の集約
#
# 再生成: python3 scripts/gen_store_builds.py
load("//bazel:astro_site.bzl", "cities_site_package", "sites_aggregate")

package(default_visibility = ["//visibility:public"])

'''


def discover_stores():
    """stores/{shard}/{retty_id}/store.json を走査して (shard, retty_id) を返す。"""
    stores_dir = os.path.join(REPO_ROOT, "stores")
    out = []
    if not os.path.isdir(stores_dir):
        return out
    for shard in sorted(os.listdir(stores_dir)):
        shard_path = os.path.join(stores_dir, shard)
        if not os.path.isdir(shard_path):
            continue
        for rid in sorted(os.listdir(shard_path)):
            store_json = os.path.join(shard_path, rid, "store.json")
            if rid.isdigit() and os.path.isfile(store_json):
                out.append((shard, rid))
    return out


def discover_cities():
    """data/cities/{code}.json を走査して code を返す。"""
    cities_data = os.path.join(REPO_ROOT, "data", "cities")
    out = []
    if not os.path.isdir(cities_data):
        return out
    for fn in sorted(os.listdir(cities_data)):
        if fn.endswith(".json"):
            code = fn[:-5]
            if code.isdigit():
                out.append(code)
    return out


def render_store_files(stores):
    """{path: content} を返す（per-store BUILD.bazel + stores/BUILD.bazel）。"""
    files = {}
    site_labels = []
    for shard, rid in stores:
        rel = os.path.join("stores", shard, rid, "BUILD.bazel")
        files[rel] = PER_STORE_TEMPLATE.format(shard=shard, retty_id=rid)
        site_labels.append("//stores/%s/%s:site" % (shard, rid))

    agg = STORES_AGGREGATE_HEADER
    for label in site_labels:
        agg += '        "%s",\n' % label
    agg += "    ],\n)\n"
    files[os.path.join("stores", "BUILD.bazel")] = agg
    return files


def render_cities_files(cities):
    """{path: content} を返す（cities/BUILD.bazel）。

    data/cities/ のシンボル（municipality JSON）を package 内から相対参照するため、
    cities package の BUILD は data/cities/ を参照する。data/cities に BUILD.bazel を置く。
    """
    files = {}
    site_labels = []
    body = CITIES_AGGREGATE_HEADER
    for code in cities:
        body += 'cities_site_package(city_code = "%s")\n' % code
        site_labels.append(":site_%s" % code)
    body += "\nsites_aggregate(\n    name = \"all\",\n    sites = [\n"
    for label in site_labels:
        body += '        "%s",\n' % label
    body += "    ],\n)\n"
    files[os.path.join("data", "cities", "BUILD.bazel")] = body
    return files


def write_or_check(files, check):
    """check=False なら書き込み、True なら差分検証（差分があれば exit 1）。"""
    stale = []
    for rel, content in files.items():
        path = os.path.join(REPO_ROOT, rel)
        existing = None
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                existing = f.read()
        if existing == content:
            continue
        if check:
            stale.append(rel)
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
    return stale


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="生成物が最新か検証（書き込みなし・CI 用）")
    args = ap.parse_args()

    stores = discover_stores()
    cities = discover_cities()
    files = {}
    files.update(render_store_files(stores))
    files.update(render_cities_files(cities))

    stale = write_or_check(files, args.check)

    if args.check:
        if stale:
            print("STALE BUILD.bazel (再生成が必要):", file=sys.stderr)
            for s in stale:
                print("  " + s, file=sys.stderr)
            print("  → python3 scripts/gen_store_builds.py", file=sys.stderr)
            sys.exit(1)
        print("OK: 全 BUILD.bazel は最新（stores=%d cities=%d）" % (len(stores), len(cities)))
    else:
        print("生成完了: stores=%d cities=%d, BUILD.bazel=%d files"
              % (len(stores), len(cities), len(files)))


if __name__ == "__main__":
    main()
