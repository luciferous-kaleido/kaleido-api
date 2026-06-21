# 作業ログ: cf_tunnel_token の Podman Secret 登録コマンドを Makefile に追加

タスク: `0002_register_cf_tunnel_secret`
開始時刻: 2026-06-22T01:54:23+09:00

## タスク概要

### 目的 (Why)
登録用コマンドを用意することで 登録/運用 を容易にする。

### 要望 (What/How)
`cf_tunnel_token` を podman secret に登録するコマンドを Makefile に追加する。
トークンは環境変数で渡す。

## 調査結果

Explore エージェントによる調査結果（完全版）。

### 1. Makefile の現在の内容と構造

ファイルパス: `Makefile`

現在の内容:
```makefile
SHELL = /usr/bin/env bash -xeuo pipefail

create-quadlet:
	uv run scripts/create_quadlets.py

check-secret:
	podman secret exists cf_tunnel_token

.PHONY: \
	create-quadlet \
	check-secret \
	message
```

構造の特徴:
- `SHELL` を `bash -xeuo pipefail` に明示設定している
  - `-x`: コマンドエコーを有効化（実行内容を stderr にトレース表示）
  - `-e`: エラー時即座に停止
  - `-u`: 未定義変数の使用を禁止
  - `-o pipefail`: パイプ途中の失敗を検出
- 既存コマンド:
  - `create-quadlet`: `uv run scripts/create_quadlets.py` を実行して Quadlet を生成
  - `check-secret`: `podman secret exists cf_tunnel_token` で secret の存在確認（タスク 0001 で実装済み）
- 環境変数は現在のところ Makefile 内で明示的には使用されていない
- 注: `.PHONY` に `message` というターゲットがリストされているが、対応するターゲット定義は存在しない（既存の状態）

### 2. Podman Secret の使用パターン

Secret の参照箇所: `quadlets/kaleido-api-cloudflared.container`
```
Secret=cf_tunnel_token,type=mount,target=/run/secrets/cf_tunnel_token
Exec=tunnel --no-autoupdate run --token-file /run/secrets/cf_tunnel_token
```

使用パターン:
- Secret 名: `cf_tunnel_token`（固定）
- `type=mount` でコンテナ内 `/run/secrets/cf_tunnel_token` にファイルとしてマウント
- cloudflared は `--token-file` オプションでこのファイルをトンネルトークンとして読む
- 重要: Secret の作成・登録は現状 Makefile や create_quadlets.py では実装されておらず、手動登録が前提

Podman secret 関連コマンド:
- 存在確認: `podman secret exists cf_tunnel_token`（登録済み → exit 0 / 未登録 → exit 1）
- 一覧表示: `podman secret list`
- 詳細確認: `podman secret inspect cf_tunnel_token`
- 作成: `podman secret create cf_tunnel_token <ファイルまたは stdin>`

### 3. タスク 0001 との関係

タスク 0001（`0001_check_secret_exists`）で `check-secret` ターゲットが追加済み。
本タスク 0002 はその対になる「登録」コマンドを追加する。

タスク 0001 の完了サマリーより:
- ローカルは Podman machine 未起動のため接続エラー（exit 125）となり、検証を実機で完遂できなかった。
- 「これは実行環境の問題で Makefile の記述は正しい」と判断して完了している。

## 実装プラン（完全版）

`Makefile` に `register-secret` ターゲットを追加する。

```makefile
register-secret:
	@set +x; \
	if [ -z "$${CF_TUNNEL_TOKEN:-}" ]; then \
		echo "Error: CF_TUNNEL_TOKEN is not set" >&2; \
		exit 1; \
	fi; \
	printf '%s' "$$CF_TUNNEL_TOKEN" | podman secret create --replace cf_tunnel_token -
```

### 設計判断

- 環境変数名: `CF_TUNNEL_TOKEN`（ユーザー確認済み）
- secret 名: `cf_tunnel_token` 固定（cloudflared が参照する唯一の secret）
- 上書き: `--replace` でべき等に（既存 secret があれば置き換え。トークン更新が容易）
- トークン漏洩対策（重要）:
  - 既存 `SHELL = bash -xeuo pipefail` の `-x`（トレース）はコマンドと変数展開を
    stderr に出力するため、そのままだとトークンが漏れる。レシピ先頭で `@set +x` してトレースを無効化。
  - `@` プレフィックスで make 自身のコマンドエコーも抑制。
  - make 変数展開 `$(CF_TUNNEL_TOKEN)` ではなくシェル変数 `$$CF_TUNNEL_TOKEN` を使い、
    トークンが make レベルで展開・記録されないようにする。
- 未設定チェック: `-u` 下でも安全なよう `$${CF_TUNNEL_TOKEN:-}` でデフォルト空。
  未設定なら明示メッセージを stderr に出して `exit 1`。
- stdin 経由: `printf '%s' | ... -` で stdin から渡し、トークンを一時ファイルに残さない。
  `printf '%s'` で末尾改行を付けない（argv にも載らないので `ps` から見えない）。
- 複数行レシピ: 全体を1つのシェル呼び出しにするため `\` で連結（`set +x` の効果を
  後続コマンドに及ぼすため、行を分割しない）。

### .PHONY への追加

既存の `.PHONY` リストに `register-secret` を追加する。

### 検討した代替案

- target-specific variable で `register-secret: SHELL = /usr/bin/env bash -euo pipefail`
  として `-x` をこのターゲットだけ外す案（advisor 提案）。
  → 効果は同等。今回は `@set +x` 方式を採用（既存 SHELL 設定との一貫性、変更が局所的）。

## プランニング経緯

### 初回提案
`register-secret` ターゲットを追加するプランを作成。当初の検証セクションは
タスク 0001 同様「Podman machine 未起動なら検証は実機で完遂できないが Makefile の記述は正しい」
というトーンだった。

### advisor のフィードバック
- 実装方針（`@set +x`、`$$CF_TUNNEL_TOKEN`、stdin 経由）は正しいと確認。
- 重要指摘: トークン漏洩テストは Podman の起動状態に依存しない。`bash -x` のトレースは
  `podman` 実行**前**（`printf` の段階）に出るため、Podman オフラインでも漏洩有無は判定可能。
  タスク 0001 が検証を諦めた点を、ここでは実際に `grep -c dummy` で確認すべき。
- fish シェルでは `VAR=val make` が使えないため `env CF_TUNNEL_TOKEN=dummy make ...` を使う。
- `--replace` は podman ≥ 4.7 が下限。

### 最終プランへの変更
検証セクションを修正:
- 漏洩テスト `env CF_TUNNEL_TOKEN=dummy make register-secret 2>&1 | grep -c dummy`（必ず 0）を
  最重要・Podman 起動不要の検証として明記。
- `env` 経由で環境変数を渡す形式に統一（fish 対応）。
- `--replace` の podman 下限を補足に追記。

その後 ExitPlanMode で承認を得た。

## 会話内容

1. ユーザーが `/add-kanban` でタスク 0002 を起票（要望・目的を指定）。続けて `/kanban 0002` を実行。
2. Claude: プランモードに入り、Explore エージェントで Makefile / Podman secret パターンを調査。
3. Claude: AskUserQuestion で2点確認。
   - 環境変数名 → ユーザー回答: `CF_TUNNEL_TOKEN`
   - 既存 secret がある場合の振る舞い → ユーザー回答: `--replace` で上書き
4. Claude: プランファイル作成 → advisor 相談 → 検証セクションを修正 → ExitPlanMode。
5. ユーザー: プラン承認。

## 編集したファイル

- `Makefile` — `register-secret` ターゲットを `check-secret` の直後に追加。`.PHONY` に
  `register-secret` を追加。実際に追加した内容:
  ```makefile
  register-secret:
  	@set +x; \
  	if [ -z "$${CF_TUNNEL_TOKEN:-}" ]; then \
  		echo "Error: CF_TUNNEL_TOKEN is not set" >&2; \
  		exit 1; \
  	fi; \
  	printf '%s' "$$CF_TUNNEL_TOKEN" | podman secret create --replace cf_tunnel_token -
  ```

## 実行したコマンド

1. `env CF_TUNNEL_TOKEN=dummy make register-secret 2>&1 | grep -c dummy`
   → 出力 `0`。トークン `dummy` が画面に一切出ていない（漏洩なし）。合格。
2. `env -u CF_TUNNEL_TOKEN make register-secret`
   → 出力:
     ```
     + set +x
     Error: CF_TUNNEL_TOKEN is not set
     make: *** [register-secret] Error 1
     ```
     exit_code=2（make の終了コード。レシピは exit 1）。未設定を正しく検出。合格。
     `+ set +x` のトレース1行はトークンを含まないため問題なし。
3. `make check-secret`（Podman 稼働確認）
   → `Cannot connect to Podman ... connection refused` / Error 125。
     Podman machine 未起動。検証3（実機登録）はこの環境では完遂不可。

## 判断・意思決定

- 実機登録テスト（検証3）について、dummy トークンを `--replace` で登録すると既存の
  本物 secret を上書きして壊すリスクがあるため、dummy 登録は実施せず `check-secret` での
  接続確認のみに留めた。結果として Podman 未起動が判明。
- 最重要のトークン漏洩テスト（検証1）は Podman 非依存で実行でき、合格を実機確認した。
  これによりタスク 0001 が実機検証を諦めた点（セキュリティ確認）を本タスクでは実際に確認できた。

## エラー・問題

- `make check-secret` で Podman 接続エラー（Error 125）。これは実行環境（Podman machine 未起動）の
  問題であり、Makefile の記述は正しい。Podman 稼働環境で `make register-secret` を実行すれば
  secret `cf_tunnel_token` が登録される。

## 完了

完了時刻: 2026-06-22T01:55:43+09:00
