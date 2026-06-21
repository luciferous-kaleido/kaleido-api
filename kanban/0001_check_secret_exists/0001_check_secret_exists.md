# Podman secret登録確認コマンドをMakefileに追加

## 目的
quadletで動かす際にsecretを参照するので、quadletに配置する前に存在を確認したいからです

## 要望
`podman secret exists`を使ってsecretが登録されているか確認するコマンドをMakefileに追加してください

## プラン
`Makefile` に `check-secret` ターゲットを追加する。

- 内容: `podman secret exists cf_tunnel_token`
- secret 名は `cf_tunnel_token` 固定（cloudflared が参照する唯一の secret）
- 未登録時は素の `podman secret exists` の挙動に委ねる（存在 → exit 0 / 未登録 → exit 1、メッセージなし）。SHELL が `bash -xeuo pipefail` のため exit 1 でターゲットがそのまま失敗する
- ターゲット名は既存の `create-quadlet` の命名に合わせる。`.PHONY` に `create-quadlet` と `check-secret` を追加

詳細は `log.md` を参照。

## 完了サマリー
完了日時: 2026-06-22T01:45:47+09:00

`Makefile` に `check-secret` ターゲットを追加した。`make check-secret` で `podman secret exists cf_tunnel_token` を実行し、quadlet 配置前に secret `cf_tunnel_token` の登録有無を確認できる（登録済み → exit 0 / 未登録 → exit 1）。`.PHONY` に `create-quadlet` と `check-secret` も追加。

検証: `make check-secret` 実行でコマンドが正しく呼び出されることを確認。ローカルは Podman machine 未起動のため接続エラー（exit 125）となったが、これは実行環境の問題で Makefile の記述は正しい。Podman 稼働環境で登録状況に応じた終了コードが得られる。
