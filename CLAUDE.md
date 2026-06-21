# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 概要

`kaleido-api` は、**grok による画像生成 Web アプリの API バックエンド**。本命は **FastAPI による API サーバー**で、nginx が `/api/*` をリバースプロキシし、Cloudflare Tunnel で外部公開する構成を目指す。

現状はその前段階として、**マスタデータ (JSON) 配信用の静的コンテンツ配信**を nginx + Cloudflare Tunnel の Podman (rootless systemd / Quadlet) 構成で実装している段階。アプリケーションコード (`src/main.py`) はまだ空。

### ロードマップ (現状と方向性)

1. **(済/進行中)** nginx による静的コンテンツ (マスタデータ JSON) 配信 — Cloudflare Tunnel で公開。
2. **(次)** Cloudflare Access の Service Token によるアクセス制限を実装 (API サーバー設置前に行う)。
3. **(本命)** FastAPI で API サーバーを実装。nginx で `/api/*` をリバースプロキシし、cloudflared 経由で公開。

## コマンド

```bash
make create-quadlet   # uv run scripts/create_quadlets.py を実行し dist/quadlet/ に Quadlet を生成
uv run <script>       # Python スクリプトの実行 (Python >=3.14)
uv sync               # 依存 (dev グループ: black / isort / jinja2) のインストール
```

テストフレームワークやリンタの実行設定は未整備。フォーマットは dev 依存に `black` / `isort` が含まれる。

## アーキテクチャ

Quadlet 生成は 2 系統に分かれる (`scripts/create_quadlets.py`)。出力先はすべて `dist/quadlet/` (gitignore 対象、生成物)。

1. **テンプレート生成** — `scripts/templates/*.jinja2` を Jinja2 でレンダリングし、ホスト絶対パスを埋め込む。
   - `kaleido-api-content.volume` — `data/content/` を bind mount するボリューム定義 (`content_dir` を注入)。
   - `kaleido-api-nginx.container` — nginx コンテナ。`data/nginx/conf.d/` を `/etc/nginx/conf.d` に ro mount (`volume_dir` を注入)、上記ボリュームを `/usr/share/nginx/html` に ro mount。
2. **静的コピー** — パス埋め込み不要な `quadlets/` 配下をそのままコピー。
   - `quadlets/kaleido-api.network` — bridge ネットワーク `kaleido-api`。
   - `quadlets/kaleido-api-cloudflared.container` — cloudflared コネクタ。nginx サービスに依存し、トンネルトークンを Podman secret `cf_tunnel_token` から読む。

実行時の経路: Cloudflare Tunnel → cloudflared → (ネットワーク `kaleido-api`, alias `nginx`) → nginx。現状 nginx は `/statics/` 配下のみ配信し `/` は 404 を返す (`data/nginx/conf.d/default.conf`)。今後この nginx 設定に `/api/*` の FastAPI へのリバースプロキシが追加される予定。nginx / cloudflared コンテナは `NoNewPrivileges`、nginx は `ReadOnly` + tmpfs で堅牢化されている。

### パス解決の前提

生成される Quadlet にはこのリポジトリのホスト上の絶対パスが直接埋め込まれる (`scripts_dir.parent` 基準)。**リポジトリを移動すると再生成が必要**。`data/content/statics/` 配下が nginx の配信対象実体。

## 開発ワークフロー (kanban-kit)

Claude Code での開発は `kanban-kit` プラグイン (`.claude/settings.json` で有効) によるカンバンワークフローで進める。ワークフローの正式な詳細は `/kanban-kit:kanban` スキルの `references/kanban-workflow.md` を参照すること (以下は要点)。

- **タスク起票**: `/add-kanban` または手動で `kanban/{xxxx}_{title}/{xxxx}_{title}.md` を作成。`## 目的` (Why) と `## 要望` (How/What) を記載する。`## 目的` は `/kanban` 実行時に存在チェックされる必須項目。
- **タスク実行**: `/kanban` (引数なしで未完了タスクの最大番号を選択、または番号指定)。**まずプランモードで計画を立てて承認を得てから実装**する。
- **ログ必須**: 実装中は `kanban/{xxxx}_{title}/log.md` に**段階的に**作業ログを残す。ログは要約・省略禁止の完全な記録 (調査結果・実装プラン完全版・プランニング経緯・会話・編集ファイル・実行コマンド・判断・エラー)。kanban ファイルの `## プラン` は要約版、`log.md` が完全版という関係。
- **完了時**: kanban ファイルに `## 完了サマリー` を追記する (これが未完了/完了の判定基準)。
- **規約**: 連番 `xxxx` は4桁0パディング。タイムスタンプは JST の ISO 8601 (`TZ=Asia/Tokyo date +"%Y-%m-%dT%H:%M:%S+09:00"`)。
