#!/usr/bin/env bash
#
# build_one.sh — 指定 1 サイトだけを astro build して factory の該当パスに反映する。
#
# 「ターゲットを指定して、そのサイトだけ」をビルドするための単体ビルドスクリプト。
# build-site.yml（workflow_dispatch）から呼ばれるが、ローカルでも単体実行できる。
#
# 仕組み:
#   - site-builder/ に自己完結の Astro プロジェクトがある（foodre restaurant /
#     cities municipality の両テンプレートを同梱）。
#   - 対象 1 件のデータ JSON だけを site-builder/src/data/ にステージする。
#   - 各テンプレートの getStaticPaths は src/data/ をグロブするため、ステージされた
#     1 件だけを生成する → 1397 店フルビルドにならず「1 サイトだけ・短時間」で完了。
#   - 生成物（dist/{foodre|cities}/{id}/）をリポジトリの該当パスにだけ反映する
#     （他パスは触らない）。
#
# 使い方:
#   scripts/build_one.sh foodre 100001317893
#   scripts/build_one.sh cities 32525
#
# データソース（永続化先）:
#   foodre: stores/{id末尾2桁}/{id}/store.json
#   cities: data/cities/{id}.json   ← 出力先 cities/{id}/ の外に置く
#           （出力反映時に cities/{id}/ を rm -rf するため、ソースを中に置かない）
#
set -euo pipefail

SITE_TYPE="${1:-}"
SITE_ID="${2:-}"

if [[ -z "${SITE_TYPE}" || -z "${SITE_ID}" ]]; then
  echo "usage: $0 <foodre|cities> <id>" >&2
  echo "  foodre: id=retty_id（例 100001317893）" >&2
  echo "  cities: id=自治体コード（例 32525）" >&2
  exit 2
fi

# id バリデーション（数字のみ。パストラバーサル防止）
if [[ ! "${SITE_ID}" =~ ^[0-9]+$ ]]; then
  echo "ERROR: id は数字のみ指定してください（received: '${SITE_ID}'）" >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILDER_DIR="${REPO_ROOT}/site-builder"
cd "${BUILDER_DIR}"

# ステージング領域を毎回クリーン（前回ビルドの取り残し防止 = 厳密に 1 件だけ）
rm -f src/data/stores/*.json src/data/municipality/*.json

OUT_REL=""  # リポジトリルートからの反映先（例: foodre/100001317893）
DIST_REL="" # dist 内の生成パス（例: foodre/100001317893）

case "${SITE_TYPE}" in
  foodre)
    SHARD="${SITE_ID: -2}"
    SRC_JSON="${REPO_ROOT}/stores/${SHARD}/${SITE_ID}/store.json"
    if [[ ! -f "${SRC_JSON}" ]]; then
      echo "ERROR: store.json が見つかりません: ${SRC_JSON}" >&2
      exit 1
    fi
    cp "${SRC_JSON}" "src/data/stores/${SITE_ID}.json"
    OUT_REL="foodre/${SITE_ID}"
    DIST_REL="foodre/${SITE_ID}"
    ;;
  cities)
    SRC_JSON="${REPO_ROOT}/data/cities/${SITE_ID}.json"
    if [[ ! -f "${SRC_JSON}" ]]; then
      echo "ERROR: municipality.json が見つかりません: ${SRC_JSON}" >&2
      echo "       data/cities/${SITE_ID}.json にソースデータを配置してください。" >&2
      exit 1
    fi
    cp "${SRC_JSON}" "src/data/municipality/${SITE_ID}.json"
    OUT_REL="cities/${SITE_ID}"
    DIST_REL="cities/${SITE_ID}"
    ;;
  *)
    echo "ERROR: site_type は foodre | cities のいずれか（received: '${SITE_TYPE}'）" >&2
    exit 2
    ;;
esac

# 依存インストール（node_modules があればスキップ）
if [[ ! -d node_modules ]]; then
  echo "==> npm install (astro)"
  if [[ -f package-lock.json ]]; then
    npm ci
  else
    npm install --no-audit --no-fund
  fi
fi

echo "==> astro build (${SITE_TYPE} / ${SITE_ID})"
rm -rf dist
npx --no-install astro build

DIST_PAGE="${BUILDER_DIR}/dist/${DIST_REL}"
if [[ ! -f "${DIST_PAGE}/index.html" ]]; then
  echo "ERROR: 生成物が見つかりません: ${DIST_PAGE}/index.html" >&2
  echo "       astro build が ${DIST_REL}/ を生成しませんでした。" >&2
  exit 1
fi

# 該当パスにだけ反映（他パスは触らない）
DEST_PAGE="${REPO_ROOT}/${OUT_REL}"
mkdir -p "$(dirname "${DEST_PAGE}")"
rm -rf "${DEST_PAGE}"
cp -r "${DIST_PAGE}" "${DEST_PAGE}"

echo "==> done: ${OUT_REL}/index.html を更新しました"
echo "    https://factory.entreprenais.com/${OUT_REL}/"
