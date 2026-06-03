// foodre — store.json 型 & 表示ヘルパー（複数店舗を1ビルドで生成するため store を引数で受ける）

export interface MenuItem {
  name: string;
  price?: string | number;
  description?: string;
  photo?: string;
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

export interface Store {
  retty_id: string;
  slug: string;
  name: string;
  description?: string;
  category?: string;
  categories?: string[];
  address?: string;
  postal_code?: string | null;
  tel?: string | null;
  hours?: Record<string, { open?: string; close?: string }> | null;
  hours_raw?: string | null;
  budget?: { lunch?: number | string | null; dinner?: number | string | null } | null;
  budget_raw?: string | null;
  nearest_station?: string | null;
  payment_accepted?: string | null;
  owner_message?: string;
  featured_menu?: MenuItem[];
  special_info?: string;
  reservation_url?: string;
  retty_url?: string;
  retty_photos?: string[];
  owner_photos?: string[];
  retty_rating?: number | null;
  retty_review_count?: number | null;
  geo?: { lat?: number; lng?: number } | null;
  sns?: Record<string, string>;
  /** ヒーロー KPI バッジ（任意）。無ければ rating / review_count / photos 等から自動導出する。 */
  stats?: StatBadge[];
  /** 特徴・こだわりグリッド（任意）。無ければセクション非表示。 */
  features?: FeatureItem[];
  /** 顧客レビュー（任意）。無ければセクション非表示。 */
  reviews?: ReviewItem[];
}

/**
 * ヒーローに出す KPI スタッツを返す。
 * store.stats があればそれを優先し、無ければ rating / review_count / photo 数 /
 * category 数から「数字が映える」バッジを自動導出する（データ欠落時フォールバック）。
 * 1 件も作れなければ空配列を返し、hero 側はバッジ行ごと非表示にする。
 */
export function deriveStats(store: Store): StatBadge[] {
  if (store.stats && store.stats.length) return store.stats.slice(0, 3);
  const out: StatBadge[] = [];
  if (store.retty_rating != null) {
    out.push({ value: `★${store.retty_rating.toFixed(2)}`, label: '評価' });
  }
  if (store.retty_review_count != null && store.retty_review_count > 0) {
    out.push({ value: `${store.retty_review_count.toLocaleString()}`, label: 'クチコミ' });
  }
  const photoCount = (store.retty_photos?.length ?? 0) + (store.owner_photos?.length ?? 0);
  if (photoCount > 0) {
    out.push({ value: `${photoCount}`, label: '写真' });
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
  return !!(store.featured_menu && store.featured_menu.some(m => !!m.photo));
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

/** Google Maps 検索 URL を返す */
export function gmapsUrl(store: Store): string {
  if (store.geo && store.geo.lat && store.geo.lng) {
    return `https://maps.google.com/?q=${store.geo.lat},${store.geo.lng}`;
  }
  return `https://maps.google.com/?q=${encodeURIComponent((store.name ?? '') + ' ' + (store.address ?? ''))}`;
}

/** Google Maps 埋め込み iframe URL を返す（API キー不要の q= 埋め込み） */
export function gmapsEmbedUrl(store: Store): string {
  const q = store.geo && store.geo.lat && store.geo.lng
    ? `${store.geo.lat},${store.geo.lng}`
    : (store.name ?? '') + ' ' + (store.address ?? '');
  return `https://maps.google.com/maps?q=${encodeURIComponent(q)}&z=16&output=embed`;
}
