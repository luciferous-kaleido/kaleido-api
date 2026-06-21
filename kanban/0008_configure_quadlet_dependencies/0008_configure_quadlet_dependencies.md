# Quadlet の依存関係設定

## 目的
cloudflared を起動させるだけで全てが立ち上がるようにするため、network や volume の開始順序・依存関係を適切に設定する。

## 要望
network や volume の開始もきちんと after や required を設定したい

## プラン
- `kaleido-api-content.volume.jinja2` に `[Unit]` セクションを追加
- `kaleido-api-nginx.container.jinja2` の `[Unit]` セクションに `Requires=kaleido-api.network` と `Requires=kaleido-api-content.volume` を追加
- `quadlets/kaleido-api.network` に `[Unit]` セクションを追加
- `quadlets/kaleido-api-cloudflared.container` の `[Unit]` セクションに `Requires=kaleido-api.network` を追加

## 完了サマリー
**完了日時**: 2026-06-22T15:55:00+09:00

### 実施内容
- 4つのファイルを修正して Quadlet の依存関係を設定
- `make create-quadlet` で Quadlet ファイルを再生成
- 生成物を検証して、すべての依存関係が正しく設定されたことを確認

### 変更ファイル
1. `scripts/templates/kaleido-api-content.volume.jinja2` — `[Unit]` セクション追加
2. `scripts/templates/kaleido-api-nginx.container.jinja2` — `Requires=` 追加
3. `quadlets/kaleido-api.network` — `[Unit]` セクション追加
4. `quadlets/kaleido-api-cloudflared.container` — `Requires=kaleido-api.network` 追加

### 起動順序
cloudflared を起動すると、systemd が自動的に network → volume → nginx の順に起動してから、cloudflared を起動するようになった。
