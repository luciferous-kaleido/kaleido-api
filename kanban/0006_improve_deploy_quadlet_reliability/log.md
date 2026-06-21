# タスク 0006: deploy-quadlet ターゲットのエラーチェック強化 — ログ

## メタデータ
- **開始時刻**: 2026-06-22T03:07:42+09:00
- **ステータス**: 完了
- **完了時刻**: 2026-06-22T03:08:19+09:00

## タスク概要
タスク 0005 で特定した Quadlet generator エラー（nginx.container の NetworkAlias キー未対応）を早期に検知するため、以下を実装：
1. `scripts/templates/kaleido-api-nginx.container.jinja2` の修正（既実装）
2. Makefile の `deploy-quadlet` ターゲットに dry-run チェック機能を追加

## 調査結果

### テンプレート修正の確認
`scripts/templates/kaleido-api-nginx.container.jinja2` は既に修正済み：
```
Network=kaleido-api.network:alias=nginx
```
（修正前は `Network=kaleido-api.network` と `NetworkAlias=nginx` の2行）

### Makefile 現状確認
Makefile の `deploy-quadlet` ターゲット（18-21行目）：
```makefile
deploy-quadlet: check-secret create-quadlet
	mkdir -p "$$HOME/.config/containers/systemd"
	cp dist/quadlet/* "$$HOME/.config/containers/systemd/"
	systemctl --user daemon-reload
```
干支 systemctl --user daemon-reload` で終了、その後のチェックなし。

### 追加するチェック手順
タスク 0005 での診断で使用した dry-run コマンド：
```bash
/usr/libexec/podman/quadlet -dryrun -user 2>&1
```
エラーがある場合はエラーメッセージが stderr に出力される。この実行結果でエラー有無を判定できる。

## 実装プラン

### Makefile 修正内容
`deploy-quadlet` ターゲットに以下を追加：
- `systemctl --user daemon-reload` 後に `quadlet -dryrun -user` を実行
- エラーがあれば（終了コード 0 以外）、エラーメッセージを出力して deploy を失敗させる（exit 1）
- 成功時（終了コード 0）は何も出力せず続行

具体的な修正方法：
```makefile
deploy-quadlet: check-secret create-quadlet
	mkdir -p "$$HOME/.config/containers/systemd"
	cp dist/quadlet/* "$$HOME/.config/containers/systemd/"
	systemctl --user daemon-reload
	@/usr/libexec/podman/quadlet -dryrun -user > /dev/null || { \
		echo "Error: Quadlet generation failed" >&2; \
		exit 1; \
	}
```

- `@` で echo コマンド自体の出力を抑制（エラーメッセージだけが表示される）
- `> /dev/null` で正常系の出力を抑制（エラーがあった場合だけメッセージ表示）
- `||` で前のコマンドが失敗した場合のみ後ろを実行
- stderr に "Error: Quadlet generation failed" を出力
- `exit 1` で make を失敗させる

## プランニング経緯
- 初回プランで、テンプレート修正（既実装）と dry-run チェック追加（本実装）の2ステップを整理
- dry-run チェックをどこに埋め込むか、どの形式が最適か検討
- 最もシンプルで堅牢な方法は、generator の存在チェック（完全なエラーハンドリング）より、dry-run 実行結果でエラー有無を判定する方式
- Makefile の表現として、可読性と簡潔さを両立させるため上記形式に決定

## 会話内容
（プランモードでの検討）
- タスク 0005 の成果物（原因特定、テンプレート修正）を確認
- テンプレート修正は既に実装済みであることを確認
- dry-run チェック追加の位置・形式を検討
- Makefile のシェルスクリプト構文（`||`, `{}`, `exit` など）の活用方法を確認

## 編集ファイル

### 1. Makefile（22-25行目追加）
変更内容：`deploy-quadlet` ターゲットに `kaleido-api-nginx.service` 生成確認チェック機能を追加。

**初版（実装後に修正前判定で変更）**：
```makefile
@/usr/libexec/podman/quadlet -dryrun -user > /dev/null || { \
    echo "Error: Quadlet generation failed" >&2; \
    exit 1; \
}
```
問題: systemd generator はエラーを stderr に出力して exit 0 を返す可能性が高い（0005 の「静かな失敗」の根拠）。したがって `||` が作動せず、チェックが機能しない。

**最終版（修正後）**：
```makefile
@systemctl --user list-unit-files | grep -q '^kaleido-api-nginx\.service' || { \
    echo "Error: kaleido-api-nginx.service was not generated" >&2; \
    exit 1; \
}
```
改良点：
- exit code に依存せず、実際の結果（`.service` が存在するか）で判定
- 0005 で実際に発生した問題（`kaleido-api-nginx.service` が生成されない）を直接検知
- systemd のバージョンや generator の quirk に依存しない、堅牢な実装

### 2. scripts/templates/kaleido-api-nginx.container.jinja2（既に修正済み）
確認結果：7行目が `Network=kaleido-api.network:alias=nginx` になっており、修正済み。
（修正前は 7-8 行に `Network=kaleido-api.network` と `NetworkAlias=nginx` の2行があった）

## 実行コマンド
（ローカル環境での修正作業なのでコマンド実行なし。`make deploy-quadlet` の実行はサーバー側で実施）

## 判断・意思決定
- **初版の方針（却下）**: `/usr/libexec/podman/quadlet -dryrun -user` の exit code でエラー判定
  - 理由: systemd generator の標準的な動作として、エラーを stderr に出力して exit 0 を返す傾向がある
  - 0005 での「make deploy-quadlet は成功したがユニット生成が失敗している」という事象から推定
  - この方法では `||` が作動せず、チェック機能が dead code になるリスク → 却下

- **最終案採用**: `systemctl --user list-unit-files` で実際の生成結果を確認
  - 理由: exit code の quirk に依存しない、より堅牢な実装
  - 0005 で実際に起きた問題（`.service` が生成されない）を直接チェック
  - systemd のバージョン差異の影響を受けない
  
- advisor の指摘により、exit code 方式の脆弱性を認識し、修正を実施

## エラー・問題
### 解決済み
- 初版の exit code 方式が脆牢性に欠ける問題を修正

### 残存する制限
- `/usr/libexec/podman/quadlet` パスは server-only（Mac では `make deploy-quadlet` が失敗する）
  - ただし、このターゲットはデプロイ用なのでサーバー環境での実行が前提
  - 問題にはならない

### サーバー側での確認待ち
実装は完了したが、サーバー上で実際に動作することを確認する必要がある：
- テンプレート修正（既に確認済み）
- Makefile の新しいチェック機能が正常に動作すること
