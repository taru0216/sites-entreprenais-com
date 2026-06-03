// foodre — store.json 型 & 表示ヘルパー（複数店舗を1ビルドで生成するため store を引数で受ける）

export interface MenuItem {
  name: string;
  price?: string | number;
  description?: string;
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
  retty_rating?: number | null;
  retty_review_count?: number | null;
  geo?: { lat?: number; lng?: number } | null;
  sns?: Record<string, string>;
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
