#!/usr/bin/env bash
# factory — astro_data_site Bazel ルールが起動する Astro ビルドラッパー。
#
# 参照実装: retty PR #238 bazel/build_astro_site.sh / entreprenais PR #5528
# build_astro_site.sh を factory の site-builder/ 構成に合わせて vendoring したもの。
#
# 「Python で HTML を直接生成しない。astro build を実際に呼ぶ」ことが必須要件。
# 本スクリプトは:
#   1. テンプレート（site-builder）を作業ディレクトリへ展開
#   2. 対象サイトのデータ JSON を site-builder/src/data/{stores|municipality}/{id}.json に配置
#   3. node_modules を用意（site-builder 同梱を symlink、無ければ npm ci）
#   4. `astro build` を実行（getStaticPaths がステージ済み 1 件だけを拾い 1 ページ生成）
#   5. 生成された dist/{site_type}/{id}/ を出力ディレクトリへコピー
#
# 引数:
#   --template-dir DIR   site-builder のルート（src/ astro.config.mjs package.json を含む）
#   --data-json FILE     対象サイトのデータ JSON
#   --site-type TYPE     foodre | cities
#   --site-id ID         retty_id（foodre）/ 自治体コード（cities）
#   --node-modules DIR   事前 install 済み node_modules（任意。あれば symlink して再利用）
#   --out-dir DIR        生成物（dist/{type}/{id}/ の中身）の出力先
set -euo pipefail

TEMPLATE_DIR=""
DATA_JSON=""
SITE_TYPE=""
SITE_ID=""
NODE_MODULES=""
OUT_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --template-dir) TEMPLATE_DIR="$2"; shift 2 ;;
    --data-json)    DATA_JSON="$2"; shift 2 ;;
    --site-type)    SITE_TYPE="$2"; shift 2 ;;
    --site-id)      SITE_ID="$2"; shift 2 ;;
    --node-modules) NODE_MODULES="$2"; shift 2 ;;
    --out-dir)      OUT_DIR="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

[[ -n "$TEMPLATE_DIR" ]] || { echo "--template-dir required" >&2; exit 2; }
[[ -n "$DATA_JSON"    ]] || { echo "--data-json required" >&2; exit 2; }
[[ -n "$SITE_TYPE"    ]] || { echo "--site-type required" >&2; exit 2; }
[[ -n "$SITE_ID"      ]] || { echo "--site-id required" >&2; exit 2; }
[[ -n "$OUT_DIR"      ]] || { echo "--out-dir required" >&2; exit 2; }

# id バリデーション（数字のみ。パストラバーサル防止）
[[ "$SITE_ID" =~ ^[0-9]+$ ]] || { echo "--site-id は数字のみ（received: '$SITE_ID'）" >&2; exit 2; }

# データ JSON のステージ先 / dist 内パスを site_type から決める
case "$SITE_TYPE" in
  foodre) DATA_SUBDIR="stores"       ; DIST_REL="foodre/${SITE_ID}" ;;
  cities) DATA_SUBDIR="municipality" ; DIST_REL="cities/${SITE_ID}" ;;
  *) echo "--site-type は foodre | cities（received: '$SITE_TYPE'）" >&2; exit 2 ;;
esac

# 絶対パス化（Bazel は相対パスで渡してくる）
abspath() { (cd "$(dirname "$1")" >/dev/null 2>&1 && echo "$(pwd)/$(basename "$1")"); }
TEMPLATE_DIR="$(cd "$TEMPLATE_DIR" && pwd)"
DATA_JSON="$(abspath "$DATA_JSON")"
[[ -n "$NODE_MODULES" ]] && NODE_MODULES="$(cd "$NODE_MODULES" && pwd)" || true

# 作業ディレクトリ（Bazel sandbox 内 or TMPDIR）
WORK="$(mktemp -d "${TMPDIR:-/tmp}/astro_site.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

# 1. テンプレート展開（node_modules / dist / .astro は除外）
cp -R "$TEMPLATE_DIR/src" "$WORK/src"
cp "$TEMPLATE_DIR/astro.config.mjs" "$WORK/"
cp "$TEMPLATE_DIR/package.json" "$WORK/"
[[ -f "$TEMPLATE_DIR/package-lock.json" ]] && cp "$TEMPLATE_DIR/package-lock.json" "$WORK/" || true
[[ -f "$TEMPLATE_DIR/tsconfig.json" ]] && cp "$TEMPLATE_DIR/tsconfig.json" "$WORK/" || true

# 2. ステージング領域を毎回クリーン（前回ビルドの取り残し防止 = 厳密に 1 件だけ）し、
#    対象サイトのデータ JSON だけを配置する。getStaticPaths はこの 1 件だけを拾う。
mkdir -p "$WORK/src/data/$DATA_SUBDIR"
rm -f "$WORK/src/data/$DATA_SUBDIR"/*.json
cp "$DATA_JSON" "$WORK/src/data/$DATA_SUBDIR/${SITE_ID}.json"

# 3. node_modules を用意（優先順位: --node-modules > $FACTORY_NODE_MODULES env >
#    テンプレート同梱 > npm ci）。事前 install 済みを symlink すれば全店でも高速。
[[ -z "$NODE_MODULES" && -n "${FACTORY_NODE_MODULES:-}" ]] && NODE_MODULES="$FACTORY_NODE_MODULES"
if [[ -n "$NODE_MODULES" && -d "$NODE_MODULES" ]]; then
  ln -s "$NODE_MODULES" "$WORK/node_modules"
elif [[ -d "$TEMPLATE_DIR/node_modules" ]]; then
  ln -s "$TEMPLATE_DIR/node_modules" "$WORK/node_modules"
else
  echo "[build_astro_site] node_modules 未検出 → npm ci 実行" >&2
  ( cd "$WORK" && npm ci --no-audit --no-fund 2>&1 || npm install --no-audit --no-fund 2>&1 )
fi

# 4. astro build を実行（これが本要件）
echo "[build_astro_site] astro build: type=$SITE_TYPE id=$SITE_ID" >&2
ASTRO_BIN="$WORK/node_modules/.bin/astro"
if [[ -x "$ASTRO_BIN" ]]; then
  ( cd "$WORK" && "$ASTRO_BIN" build )
else
  ( cd "$WORK" && npx --no-install astro build )
fi

# 5. dist/{site_type}/{id}/ を出力先へコピー
DIST_PAGE="$WORK/dist/${DIST_REL}"
[[ -d "$DIST_PAGE" ]] || { echo "astro build produced no dist/${DIST_REL}/" >&2; exit 1; }
mkdir -p "$OUT_DIR"
cp -R "$DIST_PAGE/." "$OUT_DIR/"
echo "[build_astro_site] done -> $OUT_DIR ($DIST_REL)" >&2
