#!/usr/bin/env bash
#
# changed_targets.sh — 変更されたデータファイルパスのリスト（stdin, 1 行 1 パス）から
# ビルド対象 "{site_type} {id}" を導出して stdout に出力する。
#
# 対応パターン:
#   stores/{NN}/{retty_id}/store.json      → "foodre {retty_id}"
#   data/cities/{code}.json                → "cities {code}"
#
# それ以外のパスは無視する（HTML 生成物・docs など）。
# 出力は uniq 済み・id は数字のみのものに限定（パストラバーサル防止）。
#
# 使い方:
#   git diff --name-only A B | scripts/changed_targets.sh
#   printf 'stores/47/100001625579/store.json\n' | scripts/changed_targets.sh
#
set -euo pipefail

while IFS= read -r path; do
  [[ -z "${path}" ]] && continue
  case "${path}" in
    stores/*/*/store.json)
      # stores/{NN}/{retty_id}/store.json
      id="$(basename "$(dirname "${path}")")"
      [[ "${id}" =~ ^[0-9]+$ ]] && echo "foodre ${id}"
      ;;
    data/cities/*.json)
      # data/cities/{code}.json
      id="$(basename "${path}" .json)"
      [[ "${id}" =~ ^[0-9]+$ ]] && echo "cities ${id}"
      ;;
    *)
      : # 対象外パスは無視
      ;;
  esac
done | sort -u
