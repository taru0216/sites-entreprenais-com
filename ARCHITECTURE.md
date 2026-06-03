# foodre — 飲食店HP自動生成システム アーキテクチャ

> 飲食店の **公開情報** から、多言語対応の静的ホームページを大量に自動生成して公開するシステムです。
> このリポジトリ（`taru0216/factory-entreprenais-com`）はそのまま **fork / clone して自由に利用** できます。
> 本ドキュメントは外部パートナーのエンジニア向けに、全体像と「fork して自社サイトに組み込むまで」を高レベルで説明します。

> **EntreprenAIs とは**: AI エージェントが開発・運用を担うプラットフォーム（経営 AI スタック）です。本 foodre システムも、その上で AI エージェントが構築・運用しています。
> 他にも EntreprenAIs で作成したホームページの事例は **[ホームページ作成事例（ショーケース）](https://entreprenais.com/eai/showcase/)** をご覧ください。

---

## 1. 概要

- **やること**: 飲食店の公開情報をクロールし、店舗ごとの SSOT（`store.json`）に正規化したうえで、店舗ごとの静的HP（`index.html`）と店舗一覧ページを生成し、GitHub Pages で公開します。
- **特徴**:
  - 生成物は **完全に自己完結した静的 HTML**（外部 CSS フレームワーク・JS フレームワーク非依存）。そのままどんな配信基盤にも載せられます。
  - 飲食店情報は **1 ファイル 1 店舗の `store.json`** に集約（Single Source of Truth）。HTML はこの JSON から生成されます。
  - **多言語対応**（日本語に加え en / zh / ko / th / vi / zh-TW のフィールドを持つ）。
- **スコープ**: 本ドキュメントは飲食店カテゴリ（`foodre/`）を対象に説明します。同じ仕組みは他カテゴリ（例: 地域情報 `cities/`）にも横展開可能です。

---

## 2. 全体データフロー

このシステムの設計の核心は、**`store.json` をサイトの単一の情報源（SSOT）として中心に据える**ことです。
店舗情報の入り口は 3 系統あり、**どの経路で入った情報も同じ `store.json` に集約**されます。
そして `store.json` の変更を起点に、**GitHub Actions が Astro を自動ビルド**して HP を生成・公開します。

```mermaid
flowchart LR
    A[クロール<br/>外部グルメサイトの公開情報] -->|自動取得して埋め込み| C
    H[飲食店オーナー<br/>→ LINE] -->|自然文を AI が反映| C
    O[パートナー側オペレーター<br/>→ EntreprenAIs Desktop / Slack] -->|AI 補助での編集| C
    C[(store.json<br/>サイトの情報DB / SSOT)] -->|GitHub Actions が Astro を自動ビルド| D[静的 HTML<br/>foodre/{id}/index.html]
    C -->|一覧・検索インデックス更新| E[sitemap.json /<br/>search-index.json]
    D -->|push to main| F[GitHub Actions が<br/>GitHub Pages へ公開]
    E --> F
```

テキストで表すと:

```
[クロール（外部グルメサイトの公開情報）]                  ┐
[飲食店オーナー → LINE]                                    ├→ store.json（情報DB / SSOT）→ GitHub Actions が Astro を自動ビルド → 公開HP
[パートナー側オペレーター → EntreprenAIs Desktop(Mac) / Slack] ┘
```

### 情報の入り口（3系統）

| 経路 | 入力手段 | 内容 |
|------|---------|------|
| **クロール** | 自動バッチ | 外部の飲食店情報サイト（グルメサイト）の公開情報を自動取得して `store.json` に埋め込む（`scripts/crawl_retty.py`）。公開ページのみが対象で、内部 API には一切アクセスしません。レートリミット配慮のため sleep を挟んだ夜間バッチ（GitHub Actions の `crawl-stores.yml`）で実行します。 |
| **飲食店オーナーによる直接入力** | **LINE** | オーナーが LINE で自然文を送ると、AI がその内容を `store.json` に反映します。メニュー・オーナーメッセージ・多言語フィールドなどを手軽に充実させられます。 |
| **パートナー側オペレーターによる直接入力** | **EntreprenAIs Desktop（Mac アプリ）または Slack** | パートナー内部のオペレーターが Desktop アプリまたは Slack から、AI 補助で `store.json` を編集します。 |

> **設計思想**: クロールによる自動取得だけでなく、人＋AI による直接編集（飲食店は LINE、パートナー内部は Desktop アプリ or Slack）も **すべて同じ `store.json` に集約**されます。入力手段は経路ごとに異なりますが、最終的な情報源は `store.json` ただ一つ（SSOT）であり、その変更を起点に GitHub Actions が自動ビルドする——という一貫した構造が、データの整合性と多店舗の大量生成を両立させています。

### ビルド・公開

- **HTML 生成（Astro 自動ビルド）は GitHub Actions が担います。** `store.json` を起点に、本リポジトリ同梱の Astro プロジェクト（`site-builder/`）を CI 上でビルドし、生成された静的 HTML を `foodre/`（自治体は `cities/`）にコミットします。手動でローカルにビルド環境を用意する必要はありません。
- **公開**は GitHub Actions（`deploy.yml`）が、`main` への push を起点に GitHub Pages へリポジトリのルートをそのままデプロイします。
- ワークフローの詳細は「6. ビルド・デプロイ（GitHub Actions）」を参照してください。

---

## 3. 公開 URL

| 用途 | URL |
|------|-----|
| 店舗一覧 | https://factory.entreprenais.com/foodre/ |
| 各店舗ページ | https://factory.entreprenais.com/foodre/{retty_id}/ |

`{retty_id}` は店舗ごとの ID（10 桁以上の数字）です。

---

## 4. リポジトリ構成

リポジトリ: **[`taru0216/factory-entreprenais-com`](https://github.com/taru0216/factory-entreprenais-com)**（public・fork 可能）

```
factory-entreprenais-com/
├── foodre/                      # 生成された飲食店HP（静的 HTML）
│   └── {retty_id}/index.html    #   店舗ごとのページ
│   └── index.html               #   店舗一覧ページ
├── stores/                      # store.json データ（SSOT）
│   ├── store.schema.json        #   store.json の JSON Schema（draft-07）
│   └── {NN}/{retty_id}/store.json  # 店舗データ（NN = retty_id 末尾2桁でシャーディング）
├── site-builder/                # Astro プロジェクト（store.json → 静的 HTML ビルド機構）
│   ├── astro.config.mjs         #   Astro 設定
│   ├── package.json             #   ビルド依存（GitHub Actions が npm ci で解決）
│   └── src/                     #   ページテンプレート・ビルドロジック
├── scripts/
│   ├── crawl_retty.py           # 公開サイトのクローラ（標準ライブラリのみで動作）
│   ├── build_one.sh             # 1 サイト（1 店舗 / 1 自治体）だけを単体ビルド
│   ├── update_sitemap.py        # sitemap.json / search-index.json 更新
│   └── validate_store.py        # store.json のスキーマ検証
├── .github/workflows/
│   ├── crawl-stores.yml         # 夜間クロール → store.json 生成・コミット
│   ├── build-site.yml           # 特定サイトを単体ビルド（手動 dispatch）
│   └── deploy.yml               # main への push で GitHub Pages 公開
├── cities/                      # （別カテゴリ。同じ仕組みの横展開例）
├── CNAME                        # factory.entreprenais.com
└── .nojekyll
```

> **`stores/{NN}/`** の `NN` は `retty_id` の末尾2桁です。1 ディレクトリに数万件が並ぶのを避けるためのシャーディングで、深い意味はありません。

---

## 5. `store.json` スキーマ（要点）

各店舗の情報は `stores/{NN}/{retty_id}/store.json` に格納された **SSOT** です。HTML はすべてこの JSON から生成されます。正式なスキーマは [`stores/store.schema.json`](stores/store.schema.json)（JSON Schema draft-07）を参照してください。主なフィールドは以下のとおりです。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `retty_id` | string | 店舗 ID（10桁以上の数字）。**必須** |
| `slug` | string | URL 用スラッグ。**必須** |
| `hp_status` | string | HP 生成状態（`not_generated` / `generated` / `published` / `archived`）。**必須** |
| `name` | string | 店名。**必須** |
| `category` / `categories` | string / string[] | 主カテゴリ / 全カテゴリ |
| `address` / `postal_code` | string | 住所・郵便番号 |
| `tel` | string | 電話番号 |
| `hours` | object | 曜日別営業時間（`mon`..`sun` / `holiday` → `{open, close}`） |
| `budget` | object | 予算目安（`lunch` / `dinner`） |
| `geo` | object | 緯度・経度（`lat` / `lng`） |
| `nearest_station` | string | 最寄り駅 |
| `payment_accepted` | string | 支払い方法 |
| `photos`（`retty_photos` / `owner_photos`） | string[] | 写真 URL 群 |
| `reservation_url` / `sns` | string / object | 予約 URL・SNS リンク |
| `owner_message` / `featured_menu` / `special_info` | string / array | オーナー編集フィールド（任意に上書き可能） |
| `i18n` | object | 多言語フィールド（`en` / `zh` / `ko` / `th` / `vi` / `zh-TW`） |

> フィールドは「クロール由来」「オーナー編集」「多言語」の3系統に分かれます。`additionalProperties: true` なので、自社用途のフィールドを追加しても壊れません。

---

## 6. ビルド・デプロイ（GitHub Actions）

`store.json` → 静的 HTML の生成は **本リポジトリ同梱の Astro プロジェクト（`site-builder/`）を GitHub Actions が CI 上で自動ビルド**する方式です。ビルド設定（`site-builder/`）もワークフロー（`.github/workflows/`）もすべてこのリポジトリに同梱されているため、**fork すればそのまま同じパイプラインを自分のリポジトリで回せます**。

> 一方で、**生成物を「使うだけ」ならビルド環境は不要**です。`foodre/`（および `cities/`）配下の HTML は CI でビルド済みの成果物としてコミットされており、そのまま配信・組み込みできます（パターン A）。

### 6.1 ワークフロー一覧

| ワークフロー | トリガー | 役割 |
|------------|---------|------|
| `crawl-stores.yml` | `schedule`（cron `0 18 * * *` = **03:00 JST** の夜間バッチ）+ `workflow_dispatch` | 外部グルメサイトの公開情報をクロールし `store.json` / `sitemap.json` / `search-index.json` を生成してコミット。レートリミット（HTTP 429）回避のため `sleep`（既定 5 秒）を挟む。`workflow_dispatch` の inputs: `area_url` / `max_count`（既定 2000）/ `sleep`（既定 5）。 |
| `build-site.yml` | `workflow_dispatch`（手動） | **特定サイトを 1 件だけ単体ビルド**して該当パスに反映する。全店フルビルドを回さずに 1 店舗 / 1 自治体だけを短時間で再生成するためのワークフロー。`site-builder/` の依存を `npm ci` で解決し、`scripts/build_one.sh` を実行。inputs: `site_type`（`foodre` / `cities`）/ `id`（`foodre` は `retty_id`、`cities` は自治体コード）。 |
| `deploy.yml` | `push`（`main` ブランチ）+ `workflow_dispatch` | リポジトリのルートをそのまま **GitHub Pages へデプロイ**して公開する。`crawl-stores.yml` / `build-site.yml` がコミットを `main` に push すると、本ワークフローが連鎖して公開まで到達する。 |

### 6.2 ビルドフロー

```
crawl-stores.yml（夜間 / 手動）
   └─ クロール → store.json 生成・コミット → main へ push
                                                   │
build-site.yml（手動・1 サイト単体）               │
   └─ site_type + id を指定 → 該当サイトだけ        │
      Astro ビルド → 該当パスをコミット → main へ push
                                                   ▼
                                            deploy.yml（push:main）
                                               └─ GitHub Pages へ公開
```

### 6.3 今後の拡張（設計済み）

- **自動インクリメンタルビルド**: `store.json` の変更を検知し、対応するサイトのみを自動でインクリメンタルビルドする。
- **フルビルドの sharding**: 全店フルビルドは **GitHub Actions の matrix によるシャーディング**で並列化し、店舗数が増えても CI 時間を抑える。

> ビルドパイプラインの詳細・カスタマイズについてのご相談は、本リポジトリの Issue までお寄せください。

---

## 7. fork / clone / 組み込み手順

### 7.1 取得

```bash
# fork する場合: GitHub 上で Fork ボタン → 自分の組織/アカウントへ
# clone する場合:
git clone https://github.com/taru0216/factory-entreprenais-com.git
cd factory-entreprenais-com
```

最新の生成物・データを取り込むには `git pull` で十分です。

### 7.2 自社サイトへの組み込みパターン

用途に応じて、以下の 3 パターンから選べます（組み合わせも可）。

#### パターン A: 生成済みの静的 HTML をそのまま使う（最短）

`foodre/` 配下の HTML は自己完結しています（スタイルは各ページの `<style is:global>` にインライン化され、外部 CSS/JS フレームワークに依存しません。読み込む外部リソースは Web フォントと店舗写真の画像 CDN のみ）。そのため、どんな配信基盤にも載せられます。

- **サブパス配信**: 既存サイトの `/restaurants/` 等に `foodre/` の中身を配置する。
- **静的アセット取り込み**: 自社の静的サイトジェネレータ・CMS に HTML/画像を取り込む。
- **iframe 埋め込み**: 個別店舗ページを既存ページ内に `<iframe>` で埋め込む（最も手軽だが SEO/レイアウト面では非推奨）。

> ページ内のリンクは `/foodre/...` を起点とした絶対パスです。別のサブパスに配置する場合は、配信側のリライト設定で吸収するか、パスの基点を調整してください。

#### パターン B: `store.json` スキーマを流用する（データ駆動）

`stores/store.schema.json` を自社のデータモデルとして採用し、HTML 生成は自社のテンプレート/フレームワークで行うパターンです。

- 飲食店情報の正規化済みスキーマ（営業時間・予算・多言語など）をそのまま利用できます。
- `scripts/validate_store.py` でスキーマ検証が可能です。
- デザインや機能を自社ブランドに合わせて完全に作り替えられます。

#### パターン C: クロール・ビルド機構を再利用する（フルパイプライン）

`scripts/crawl_retty.py`（クローラ・標準ライブラリのみ）、`site-builder/`（Astro プロジェクト）、GitHub Actions ワークフロー（`crawl-stores.yml` / `build-site.yml` / `deploy.yml`）を自社リポジトリに取り込み、クロール → 自動ビルド → 公開までを自前で回すパターンです。fork すればこのパイプライン一式がそのまま動きます。

- 対象エリア・更新頻度・公開先（自社 GitHub Pages 等）を自由に設定できます。
- クロールは公開ページのみを対象とし、レートリミット配慮の sleep を挟んだ夜間バッチ構成です。

---

## 8. 多言語・スタイル

- **多言語**: 各 `store.json` の `i18n`（`en` / `zh` / `ko` / `th` / `vi` / `zh-TW`）から、Astro が言語別のページ要素を生成します。初回クロール時点では空で、後から多言語フィールドを埋めると反映されます。
- **スタイル**: 生成 HTML は `<style is:global>` でスタイルを自己完結させています。外部 CSS フレームワークに依存しないため、移植・組み込みが容易です（外部からの読み込みは Web フォントと写真 CDN のみ）。

---

## 9. ライセンス・利用範囲

本リポジトリの **利用条件（ライセンス・再配布・商用利用の可否等）は別途ご相談ください。** 現時点では確定的なライセンスを定めていません。

> なお、各店舗ページに含まれる写真・店舗情報など、第三者に権利が帰属するコンテンツの取り扱いについては、利用者側でも各権利元の利用規約をご確認ください。

---

## 10. 横展開について

同じ「公開情報クロール → SSOT(JSON) → 静的HP生成 → GitHub Pages 公開」の仕組みは、飲食店（`foodre/`）以外のカテゴリ（例: 地域情報 `cities/`）にも展開可能です。

---

## 11. 関連リンク

- **[ホームページ作成事例（ショーケース）](https://entreprenais.com/eai/showcase/)** — EntreprenAIs で作成したホームページの事例集
- [`taru0216/factory-entreprenais-com`](https://github.com/taru0216/factory-entreprenais-com) — 本リポジトリ（public・fork 可能）

---

ご不明な点・組み込み方法のご相談は、本リポジトリの Issue またはお問い合わせ窓口までお寄せください。
