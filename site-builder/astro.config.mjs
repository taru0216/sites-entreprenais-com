import { defineConfig } from 'astro/config';

// factory site-builder — 単体サイトビルド用 Astro プロジェクト（build-site.yml から呼ばれる）。
//
// site / build.format を本番（factory.entreprenais.com）に合わせる。
// build_one.sh が src/data/ に対象 1 件の JSON だけをステージし、
// 各テンプレートの getStaticPaths がステージ済みの 1 件だけを生成する。
// → 1397 店フルビルドではなく「1 サイトだけ・短時間」のビルドになる。
export default defineConfig({
  site: 'https://factory.entreprenais.com',
  output: 'static',
  build: { format: 'directory' },
});
