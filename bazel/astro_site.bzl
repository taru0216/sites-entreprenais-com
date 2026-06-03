"""astro_data_site — データ駆動 Astro サイトの per-site インクリメンタル Bazel ルール。

このルール/ラッパーは下記の参照実装を factory 向けに vendoring（取り込み）したもの:

  - taru0216/taruishi-masato-work-retty PR #238 の bazel/foodre.bzl
    （restaurant_site ルール + マクロ。store.json ハッシュ変化店のみ再ビルド）
  - entreprenais PR #5528（feat/5527-astro-data-site）の astro_data_site
    （astro_site.bzl + build_astro_site.sh の汎用データ駆動サイトルール）

  帰属: Copyright (c) 2026 樽石デジタル技術研究所合同会社。
  factory は entreprenais の submodule ではない standalone リポジトリのため、
  上記 .bzl/.sh の機構を factory の site-builder/ 構成に合わせて取り込んでいる。

設計の肝（epic #243 ② の核心 = template 依存追跡）:

  - 各サイト（1 店舗 / 1 自治体）の出力は「データ JSON」と「共有 template
    （site-builder/ の Astro プロジェクト一式）」の **両方** を入力に持つ。
  - データ JSON が変われば、その 1 サイトのみ再ビルドされる（他はキャッシュ再利用）。
  - **template（site-builder/ の layout/component 等）が変われば、その template を
    入力に持つ全サイトの出力が invalidate され、全依存サイトが再ビルドされる**。
    これを Bazel の依存グラフが自動で追跡する。これが Step 2 の核心。

  Python で HTML を直接生成しない。実際に `astro build` を回す。
  ビルドは bazel/build_astro_site.sh がホストの node + astro build を起動する
  （rules_js/rules_nodejs を導入せず「まず動く」を優先。#232 の許容方針）。
"""

def _astro_data_site_impl(ctx):
    # dist/{site_type}/{id}/ は可変ファイル集合のため TreeArtifact（ディレクトリ）で受ける
    out_dir = ctx.actions.declare_directory(ctx.attr.output_dir)

    template_files = ctx.files.template
    data_json = ctx.file.data_json
    builder = ctx.file._builder

    # テンプレートのルートディレクトリ（astro.config.mjs のある場所）を推定する。
    template_root = None
    for f in template_files:
        if f.basename == "astro.config.mjs":
            template_root = f.dirname
            break
    if template_root == None:
        fail("template filegroup must include astro.config.mjs")

    args = ctx.actions.args()
    args.add("--template-dir", template_root)
    args.add("--data-json", data_json.path)
    args.add("--site-type", ctx.attr.site_type)
    args.add("--site-id", ctx.attr.site_id)
    args.add("--out-dir", out_dir.path)
    if ctx.attr.node_modules_path:
        args.add("--node-modules", ctx.attr.node_modules_path)

    ctx.actions.run(
        executable = builder,
        arguments = [args],
        # 入力に template_files を含めることで、template 変更が出力を invalidate する。
        inputs = depset(template_files + [data_json, builder]),
        outputs = [out_dir],
        mnemonic = "AstroDataSite",
        progress_message = "astro build: %s site %s" % (ctx.attr.site_type, ctx.label),
        use_default_shell_env = True,
        execution_requirements = {
            # node_modules symlink / npm のため sandbox を緩める（まず動く優先, #232）
            "no-sandbox": "1",
            "requires-network": "1",
        },
    )
    return [DefaultInfo(files = depset([out_dir]))]

astro_data_site = rule(
    implementation = _astro_data_site_impl,
    doc = "データ JSON + 共有 Astro テンプレートから astro build を実行し 1 サイトを生成する。",
    attrs = {
        "data_json": attr.label(
            allow_single_file = [".json"],
            mandatory = True,
            doc = "対象サイトのデータ JSON（site-builder/src/data/ にステージされる）",
        ),
        "template": attr.label(
            mandatory = True,
            doc = "共有 Astro テンプレートの filegroup（//site-builder:template）。" +
                  "変更で全依存サイトが再ビルドされる。",
        ),
        "site_type": attr.string(
            mandatory = True,
            values = ["foodre", "cities"],
            doc = "サイト種別（foodre=店舗 / cities=自治体）。ステージ先と出力パスを決める。",
        ),
        "site_id": attr.string(
            mandatory = True,
            doc = "サイト ID（foodre=retty_id / cities=自治体コード）。",
        ),
        "output_dir": attr.string(
            default = "site",
            doc = "出力ディレクトリ名（dist/{site_type}/{id}/ の中身がここに入る）",
        ),
        "node_modules_path": attr.string(
            default = "",
            doc = "事前 install 済み node_modules の絶対パス（任意。省略時は site-builder 同梱を使用）",
        ),
        "_builder": attr.label(
            default = "//bazel:build_astro_site.sh",
            allow_single_file = True,
            cfg = "exec",
        ),
    },
)

def foodre_site_package(retty_id, template = "//site-builder:template", node_modules_path = ""):
    """各 stores/{shard}/{retty_id}/BUILD.bazel から呼ぶ per-store マクロ。

    その店舗 package 内の store.json を入力に :site（dist/foodre/{id}/ 相当）を生成する。
    store.json のハッシュが変わった店舗だけが再ビルドされる（インクリメンタル）。

    ビルド: bazel build //stores/{shard}/{retty_id}:site
    """
    astro_data_site(
        name = "site",
        data_json = "store.json",
        template = template,
        site_type = "foodre",
        site_id = retty_id,
        output_dir = "site",
        node_modules_path = node_modules_path,
    )

def cities_site_package(city_code, template = "//site-builder:template", node_modules_path = ""):
    """各 data/cities/BUILD.bazel（または cities 用 package）から呼ぶ per-city マクロ。

    その自治体の municipality JSON を入力に :site（dist/cities/{code}/ 相当）を生成する。
    """
    astro_data_site(
        name = "site_%s" % city_code,
        data_json = "%s.json" % city_code,
        template = template,
        site_type = "cities",
        site_id = city_code,
        output_dir = "site_%s" % city_code,
        node_modules_path = node_modules_path,
    )

def sites_aggregate(name = "all", sites = []):
    """親 BUILD.bazel から呼ぶ集約マクロ（//stores:all / //cities:all）。

    各サイト package（subpackage）の :site ターゲットを 1 つの filegroup に集約する。

    注意（Bazel の制約）: native.glob は **サブパッケージ境界を越えない**。各
    stores/{shard}/{retty_id}/ は自身の BUILD.bazel を持つ独立 package なので、親から
    glob しても store.json は拾えない。そのため集約対象は明示リスト sites で渡す
    （ジェネレータ scripts/gen_store_builds.py が自動生成する）。
    """
    native.filegroup(
        name = name,
        srcs = sites,
    )
