#!/usr/bin/env bash
#
# build_all.sh — 全サイト（foodre 全店 + cities 全自治体）を一括フルビルドして
# factory の該当パスに反映する。
#
# build_one.sh が「対象 1 件だけ」をステージするのに対し、本スクリプトは
# **全データをステージして一括ビルド**する。site-builder の各テンプレートの
# getStaticPaths は src/data/ 配下を glob するため、全件をステージすれば
# 単一の astro build で全ページが生成される（getStaticPaths 一括ビルド）。
#
# 使い方:
#   scripts/build_all.sh             # foodre + cities 全件
#   scripts/build_all.sh foodre      # foodre 全件のみ
#   scripts/build_all.sh cities      # cities 全件のみ
#
# データソース（永続化先）:
#   foodre: stores/{id末尾2桁}/{id}/store.json
#   cities: data/cities/{code}.json
#
# 反映先:
#   foodre/{retty_id}/   （store.json の retty_id ごと）
#   cities/{code}/       （data/cities/{code}.json の code ごと）
#
# 注意: 全件ビルドは重い（foodre 約 1400 店 / 約 130s 程度）。インクリメンタルな
#       変更分だけのビルドは build_one.sh（または auto-build ワークフロー）を使う。
#
set -euo pipefail

SCOPE="${1:-all}"  # all | foodre | cities

case "${SCOPE}" in
  all | foodre | cities) ;;
  *)
    echo "ERROR: scope は all | foodre | cities のいずれか（received: '${SCOPE}'）" >&2
    exit 2
    ;;
esac

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILDER_DIR="${REPO_ROOT}/site-builder"
cd "${BUILDER_DIR}"

# ステージング領域を毎回クリーン（前回ビルドの取り残し防止）
rm -f src/data/stores/*.json src/data/municipality/*.json

BUILD_FOODRE=0
BUILD_CITIES=0
[[ "${SCOPE}" == "all" || "${SCOPE}" == "foodre" ]] && BUILD_FOODRE=1
[[ "${SCOPE}" == "all" || "${SCOPE}" == "cities" ]] && BUILD_CITIES=1

FOODRE_COUNT=0
CITIES_COUNT=0

# --- 全データをステージ ---
if [[ "${BUILD_FOODRE}" -eq 1 ]]; then
  echo "==> staging foodre stores ..."
  while IFS= read -r SRC_JSON; do
    [[ -z "${SRC_JSON}" ]] && continue
    SITE_ID="$(basename "$(dirname "${SRC_JSON}")")"
    cp "${SRC_JSON}" "src/data/stores/${SITE_ID}.json"
    FOODRE_COUNT=$((FOODRE_COUNT + 1))
  done < <(find "${REPO_ROOT}/stores" -mindepth 3 -maxdepth 3 -name store.json 2>/dev/null | sort)
  echo "    staged ${FOODRE_COUNT} foodre store(s)"
fi

if [[ "${BUILD_CITIES}" -eq 1 ]]; then
  echo "==> staging cities municipalities ..."
  if [[ -d "${REPO_ROOT}/data/cities" ]]; then
    while IFS= read -r SRC_JSON; do
      [[ -z "${SRC_JSON}" ]] && continue
      CODE="$(basename "${SRC_JSON}" .json)"
      cp "${SRC_JSON}" "src/data/municipality/${CODE}.json"
      CITIES_COUNT=$((CITIES_COUNT + 1))
    done < <(find "${REPO_ROOT}/data/cities" -maxdepth 1 -name '*.json' 2>/dev/null | sort)
  fi
  echo "    staged ${CITIES_COUNT} cities municipality(ies)"
fi

if [[ "${FOODRE_COUNT}" -eq 0 && "${CITIES_COUNT}" -eq 0 ]]; then
  echo "ERROR: ステージするデータが 1 件もありません（stores/data/cities が空？）" >&2
  exit 1
fi

# 依存インストール（node_modules があればスキップ）
if [[ ! -d node_modules ]]; then
  echo "==> npm install (astro)"
  if [[ -f package-lock.json ]]; then
    npm ci
  else
    npm install --no-audit --no-fund
  fi
fi

echo "==> astro build (full: foodre=${FOODRE_COUNT} / cities=${CITIES_COUNT})"
rm -rf dist
npx --no-install astro build

# --- 生成物を該当パスに反映 ---
reflect_type() {
  local site_type="$1"   # foodre | cities
  local dist_root="${BUILDER_DIR}/dist/${site_type}"
  if [[ ! -d "${dist_root}" ]]; then
    echo "WARN: dist/${site_type}/ が生成されませんでした（対象 0 件？）" >&2
    return 0
  fi
  local reflected=0
  for page_dir in "${dist_root}"/*/; do
    [[ -d "${page_dir}" ]] || continue
    local pid
    pid="$(basename "${page_dir}")"
    local dest="${REPO_ROOT}/${site_type}/${pid}"
    rm -rf "${dest}"
    mkdir -p "$(dirname "${dest}")"
    cp -r "${page_dir%/}" "${dest}"
    reflected=$((reflected + 1))
  done
  echo "    reflected ${reflected} ${site_type} page(s) → ${site_type}/"
}

if [[ "${BUILD_FOODRE}" -eq 1 ]]; then
  reflect_type foodre
fi
if [[ "${BUILD_CITIES}" -eq 1 ]]; then
  reflect_type cities
fi

echo "==> done: full build (foodre=${FOODRE_COUNT} / cities=${CITIES_COUNT})"
