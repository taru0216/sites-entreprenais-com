// foodre — store.json 型 & 表示ヘルパー（複数店舗を1ビルドで生成するため store を引数で受ける）

export interface MenuItem {
  name: string;
  /** 価格（数値 or 文字列）— featured_menu / menu[] 共通 */
  price?: string | number | null;
  /** 価格表示文字列（"1,500円" 等）— menu[] で使用 */
  price_raw?: string | null;
  description?: string | null;
  /** 写真 URL（featured_menu: photo、menu[]: photo_url どちらも保持） */
  photo?: string | null;
  /** 写真 URL（クローラーが格納する標準フィールド — #255） */
  photo_url?: string | null;
  /** 料理個別ページのスラグ（menu[] のみ）— /foodre/{retty_id}/menu/{dish_slug}/ */
  dish_slug?: string;
}

/** ヒーローの KPI スタッツバッジ（任意）。banwaen 例: { value: '55品', label: '希少部位' } */
export interface StatBadge {
  value: string;
  label?: string;
}

/** 「特徴・こだわり」グリッドの 1 枠（任意）。icon は絵文字 or 短い文字列で素材依存を回避。 */
export interface FeatureItem {
  icon?: string;
  title: string;
  body?: string;
}

/** 顧客レビューの 1 件（任意）。データがあれば表示、無ければセクションごと非表示。 */
export interface ReviewItem {
  body: string;
  author?: string;
  rating?: number;
}

/** 今週のおすすめ食材・メニュー（Pattern C に表示）。*/
export interface WeeklyItem {
  name: string;
  note?: string;
  icon?: string;
}

/** 店主の日誌エントリ（Pattern C に表示）。*/
export interface DiaryEntry {
  date?: string;
  text: string;
}

export interface Store {
  retty_id: string;
  slug: string;
  name: string;
  description?: string | null;
  /** Retty 店舗一言キャッチフレーズ（crawl_retty.py #277）。ヒーローサブタイトルに表示。 */
  catchphrase?: string | null;
  category?: string;
  categories?: string[];
  address?: string;
  postal_code?: string | null;
  tel?: string | null;
  hours?: Record<string, { open?: string; close?: string }> | null;
  hours_raw?: string | null;
  /** 定休日テキスト（crawl_retty.py #277）。アクセスセクションに表示。 */
  holiday?: string | null;
  budget?: { lunch?: number | string | null; dinner?: number | string | null } | null;
  budget_raw?: string | null;
  nearest_station?: string | null;
  payment_accepted?: string | null;
  owner_message?: string;
  /** 代表メニュー（featured_menu: menu[] の先頭 5 件） */
  featured_menu?: MenuItem[];
  /** 全メニュー一覧（クローラーが取得した全件） — #255 */
  menu?: MenuItem[];
  special_info?: string;
  reservation_url?: string;
  retty_url?: string;
  retty_photos?: string[];
  owner_photos?: string[];
  retty_rating?: number | null;
  retty_review_count?: number | null;
  geo?: { lat?: number; lng?: number } | null;
  sns?: Record<string, string>;
  /** ヒーロー KPI バッジ（任意）。無ければ店舗自身の一次情報から自動導出する。 */
  stats?: StatBadge[];
  /** 特徴・こだわりグリッド（任意）。無ければセクション非表示。 */
  features?: FeatureItem[];
  /** 顧客レビュー（任意）。無ければセクション非表示。 */
  reviews?: ReviewItem[];
  /** 口コミ取得件数（crawl_retty.py #262）。fetch_reviews=true 時のみ設定。 */
  review_count?: number | null;
  /** 実名と判定された口コミ件数（crawl_retty.py #262）。 */
  real_name_count?: number | null;
  /** 実名口コミが全口コミの 50% 以上か（crawl_retty.py #262）。 */
  has_real_name_reviews?: boolean | null;
  /** 口コミ（reports）ページ URL（#272）。retty_url + /reports/。 */
  review_url?: string | null;
  /** 公式 SNS リンク（#70）。有時のみ OFFICIAL セクション表示。 */
  official_sns?: {
    instagram?: string | null;
    tiktok?: string | null;
    twitter?: string | null;
    facebook?: string | null;
  } | null;
  /** デザインテンプレート手動指定（省略時はカテゴリから自動選択）。（#78）
   *  Pattern A=ストーリードリブン / B=コンバージョン直球型 / C=コンテンツ更新型 */
  template_pattern?: 'restaurant-pattern-a' | 'restaurant-pattern-b' | 'restaurant-pattern-c' | 'restaurant-default' | null;
  /** 今週のおすすめ食材・メニュー（Pattern C）。（#78） */
  weekly_items?: WeeklyItem[];
  /** 店主の日誌エントリ（Pattern C）。（#78） */
  diary?: DiaryEntry[];
}

/**
 * ヒーローに出す KPI スタッツを返す。
 *
 * 公式サイト=一次情報プラットフォームのため、第三者評価（rating / review_count）は
 * 一切使わない。store.stats があればそれを優先し、無ければ「店舗自身が発信する事実」
 * ＝メニュー数・写真点数・営業日数・ジャンル数から数字が映えるバッジを自動導出する。
 * 一次情報で出せる指標が 1 件も無ければ空配列を返し、hero 側はバッジ行ごと非表示にする
 * （graceful fallback）。「評価」「★」「クチコミ」「レビュー」等の文言・UI は出さない。
 */
export function deriveStats(store: Store): StatBadge[] {
  if (store.stats && store.stats.length) return store.stats.slice(0, 3);
  const out: StatBadge[] = [];

  const menuCount = store.featured_menu?.length ?? 0;
  if (menuCount > 0) {
    out.push({ value: `${menuCount}`, label: 'メニュー' });
  }

  const photoCount = (store.retty_photos?.length ?? 0) + (store.owner_photos?.length ?? 0);
  if (photoCount > 0) {
    out.push({ value: `${photoCount}`, label: '写真' });
  }

  const openDays = store.hours
    ? ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'].filter((d) => {
        const h = store.hours![d];
        return !!h && (!!h.open || !!h.close);
      }).length
    : 0;
  if (openDays > 0) {
    out.push({ value: `${openDays}`, label: '営業日/週' });
  }

  if (out.length < 3) {
    const cats = store.categories && store.categories.length
      ? store.categories
      : (store.category ? [store.category] : []);
    if (cats.length > 0) out.push({ value: `${cats.length}`, label: 'ジャンル' });
  }

  return out.slice(0, 3);
}

/** featured_menu のうち少なくとも 1 件が写真を持つか（= 写真カードグリッドを使うか）を判定する。 */
export function hasMenuPhotos(store: Store): boolean {
  return !!(store.featured_menu && store.featured_menu.some(m => !!(m.photo || m.photo_url)));
}

const DAY_LABELS: Record<string, string> = {
  mon: '月', tue: '火', wed: '水', thu: '木', fri: '金', sat: '土', sun: '日', holiday: '祝',
};

/** hours オブジェクトを表示用文字列の配列に整形する */
export function formatHours(store: Store): string[] {
  if (!store.hours) {
    return store.hours_raw ? [store.hours_raw] : [];
  }
  const order = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'holiday'];
  // 連続する同一時間帯はまとめて表示する
  const segs: { open: string; close: string; days: string[] }[] = [];
  for (const day of order) {
    const h = store.hours[day];
    if (!h || (!h.open && !h.close)) continue;
    const open = h.open ?? '';
    const close = h.close ?? '';
    const last = segs[segs.length - 1];
    if (last && last.open === open && last.close === close) {
      last.days.push(DAY_LABELS[day] ?? day);
    } else {
      segs.push({ open, close, days: [DAY_LABELS[day] ?? day] });
    }
  }
  return segs.map(s => `${s.days.join('・')}: ${s.open}〜${s.close}`);
}

/** 予算（昼/夜）を表示用文字列に整形する */
export function formatBudget(store: Store): string[] {
  const out: string[] = [];
  const b = store.budget;
  const fmt = (v: number | string | null | undefined): string | null => {
    if (v == null || v === '') return null;
    if (typeof v === 'number') return `〜${v.toLocaleString()}円`;
    return String(v);
  };
  if (b) {
    const l = fmt(b.lunch);
    const d = fmt(b.dinner);
    if (l && l !== '営業時間外') out.push(`ランチ ${l}`);
    if (d) out.push(`ディナー ${d}`);
  }
  return out;
}

/** Google Maps 検索 URL を返す（Google Maps URL API 標準形式で店名+住所検索） */
export function gmapsUrl(store: Store): string {
  const q = encodeURIComponent(`${store.name ?? ''} ${store.address ?? ''}`.trim());
  return `https://www.google.com/maps/search/?api=1&query=${q}`;
}

/** Google Maps 埋め込み iframe URL を返す（API キー不要の q= 埋め込み） */
export function gmapsEmbedUrl(store: Store): string {
  const q = store.geo && store.geo.lat && store.geo.lng
    ? `${store.geo.lat},${store.geo.lng}`
    : (store.name ?? '') + ' ' + (store.address ?? '');
  return `https://maps.google.com/maps?q=${encodeURIComponent(q)}&z=16&output=embed`;
}
