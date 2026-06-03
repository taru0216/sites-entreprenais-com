#!/usr/bin/env bash
#
# test_changed_targets.sh — scripts/changed_targets.sh のユニットテスト。
# 変更ファイルパス → ビルド対象 "{site_type} {id}" 導出ロジックを検証する。
#
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CT="${SCRIPT_DIR}/scripts/changed_targets.sh"

PASS=0
FAIL=0

assert_eq() {
  local desc="$1" expected="$2" actual="$3"
  if [[ "${expected}" == "${actual}" ]]; then
    echo "PASS: ${desc}"
    PASS=$((PASS + 1))
  else
    echo "FAIL: ${desc}"
    echo "  expected: [${expected}]"
    echo "  actual:   [${actual}]"
    FAIL=$((FAIL + 1))
  fi
}

# 1. foodre store.json → "foodre {id}"
out="$(printf 'stores/47/100001625579/store.json\n' | bash "${CT}")"
assert_eq "foodre store.json を foodre 対象に変換" "foodre 100001625579" "${out}"

# 2. cities data → "cities {code}"
out="$(printf 'data/cities/32525.json\n' | bash "${CT}")"
assert_eq "cities data を cities 対象に変換" "cities 32525" "${out}"

# 3. HTML 生成物・docs などは無視
out="$(printf 'foodre/100001625579/index.html\nARCHITECTURE.md\ncities/32525/index.html\n' | bash "${CT}")"
assert_eq "生成物・docs は無視" "" "${out}"

# 4. 複数混在 + 重複排除 + ソート
out="$(printf 'stores/47/100001625579/store.json\ndata/cities/32525.json\nstores/47/100001625579/store.json\nREADME.md\n' | bash "${CT}")"
expected="$(printf 'cities 32525\nfoodre 100001625579')"
assert_eq "混在入力を uniq + sort して変換" "${expected}" "${out}"

# 5. 非数字 id は除外（パストラバーサル防止）
out="$(printf 'stores/47/abc/store.json\ndata/cities/foo.json\n' | bash "${CT}")"
assert_eq "非数字 id を除外" "" "${out}"

# 6. 空入力
out="$(printf '' | bash "${CT}")"
assert_eq "空入力は空出力" "" "${out}"

echo ""
echo "==== ${PASS} passed, ${FAIL} failed ===="
[[ "${FAIL}" -eq 0 ]]
