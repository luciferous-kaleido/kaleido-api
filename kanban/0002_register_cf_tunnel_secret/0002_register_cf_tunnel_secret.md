# cf_tunnel_token の Podman Secret 登録コマンドを Makefile に追加

## 目的
登録用コマンドを用意することで 登録/運用 を容易にする

## 要望
cf_tunnel_tokenをpodman secretに登録するコマンドをMakefileに追加してください。トークンは環境変数で渡します。

## プラン
`Makefile` に `register-secret` ターゲットを追加する（`check-secret` の対になる登録コマンド）。

```makefile
register-secret:
	@set +x; \
	if [ -z "$${CF_TUNNEL_TOKEN:-}" ]; then \
		echo "Error: CF_TUNNEL_TOKEN is not set" >&2; \
		exit 1; \
	fi; \
	printf '%s' "$$CF_TUNNEL_TOKEN" | podman secret create --replace cf_tunnel_token -
```

- 環境変数 `CF_TUNNEL_TOKEN` でトークンを渡す。secret 名は `cf_tunnel_token` 固定。
- `--replace` でべき等（既存があれば上書き、トークン更新が容易）。
- トークン漏洩対策: 既存 `SHELL = bash -xeuo pipefail` の `-x` トレースで漏れるため、
  `@set +x` でトレース無効化 + `@` でエコー抑制 + make 変数でなくシェル変数 `$$CF_TUNNEL_TOKEN`
  を使用 + stdin 経由（一時ファイル・argv に残さない）。
- 未設定なら `-u` 下でも安全な `$${CF_TUNNEL_TOKEN:-}` で判定し、エラー表示して exit 1。
- `.PHONY` に `register-secret` を追加。

詳細は `log.md` を参照。

## 完了サマリー
完了日時: 2026-06-22T01:55:43+09:00

`Makefile` に `register-secret` ターゲットを追加した。`CF_TUNNEL_TOKEN` 環境変数で
トークンを渡し、`podman secret create --replace cf_tunnel_token -` で secret `cf_tunnel_token`
を登録する。`--replace` によりべき等（トークン更新も容易）。`.PHONY` にも追加。

トークン漏洩対策として `@set +x`（`-x` トレース無効化）+ `@`（エコー抑制）+ シェル変数
`$$CF_TUNNEL_TOKEN`（make に値を展開させない）+ stdin 経由（一時ファイル・argv に残さない）を実装。

検証:
- 漏洩テスト `env CF_TUNNEL_TOKEN=dummy make register-secret 2>&1 | grep -c dummy` → `0`（漏洩なし）。合格。
- 未設定チェック `env -u CF_TUNNEL_TOKEN make register-secret` → `Error: CF_TUNNEL_TOKEN is not set` / exit 1。合格。
- 実機登録は Podman machine 未起動（Error 125）のため未実施。Podman 稼働環境で実行すれば登録される。
  なお漏洩テストは Podman 非依存で確認できたため、タスク 0001 が諦めたセキュリティ検証を本タスクでは実機確認できた。
