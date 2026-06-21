# Secret 登録エラーの修正

## 目的
登録ができないので先に進めない

## 要望
cf_tunnel_tokenを登録しようとしたらエラーが出た修正して欲しい。

## エラー
```
❯ CF_TUNNEL_TOKEN=xxxx make register-secret
+ set +x
Error: deleting secret : : no secret data with ID
make: *** [Makefile:10: register-secret] Error 125
```

## プラン

`Makefile` の `register-secret` ターゲットで使っている `podman secret create --replace` を廃止し、バージョン非依存の「削除（無ければ無視）→ 作成」方式へ変更する。

- 原因: podman 4.9.3 の `--replace` が、対象 secret が未存在のとき空 ID で削除を試みて失敗する不具合（初回実行で発生）。エラー文面の ID 部分が空 (`deleting secret : :`) であることが根拠。バージョンが古いのが原因ではない。
- 修正:
  ```makefile
  	podman secret rm cf_tunnel_token 2>/dev/null || true; \
  	printf '%s' "$$CF_TUNNEL_TOKEN" | podman secret create cf_tunnel_token -
  ```
- `2>/dev/null || true` が初回実行（secret 未登録）で落ちないために必須。トークン非露出の `@set +x` は維持。

## 完了サマリー

完了日時: 2026-06-22T02:30:18+09:00

`Makefile` の `register-secret` ターゲットを修正し、エラーの原因である `podman secret create --replace` を廃止した。

- **変更内容** (`Makefile` lines 9-16): `--replace` を使わず `podman secret rm cf_tunnel_token 2>/dev/null || true` で既存 secret を削除（未存在時はエラー無視）してから `podman secret create cf_tunnel_token -` で登録する方式へ変更。バージョン非依存で堅牢。
- **原因**: podman 4.9.3 の `--replace` が secret 未存在時に空 ID で削除を試みる不具合（初回実行で発生）。バージョンが古いことが原因ではない（4.9.3 は `--replace` 対応版）。
- **検証**: ローカル (macOS) は podman machine 未起動のため動作確認不可。ユーザーがデプロイ先 (podman 4.9.3) で ①初回 ②2回目（上書き）③`make check-secret` の成功を確認する必要がある。
- **補足（セキュリティ）**: 作業中にツール出力へ異常コンテンツ（Makefile への secret 流出 `evil:` ターゲット混入の偽装表示、偽 system-reminder 等）が観測された。一旦中断・報告し、`make`/`podman`/`curl` 系は未実行（**私を介した流出なし**）。raw git で作業ツリーのクリーンを確認後、正規手順で本修正のみを適用。編集後も raw git diff で実差分を検証済み。

## インジェクション源の調査（追加作業）

ユーザー依頼で発生源を調査。詳細は `log.md` の「追加作業: インジェクション源の調査」節を参照。

- **VERIFIED（クリーン）**: 永続的なシステム侵害は**存在しない**。プロジェクト/グローバル hooks、rtk フック（sha256 一致・rtk 未インストールで no-op）、git hooks/alias、PATH シャドーイング（`git`→`/usr/bin/git`）、MCP（未設定）、プラグイン bin — すべて無害と確認。ディスクもクリーン（`grep` で `evil`/`curl` 等マッチなし）。
- **決定的根拠**: hook 構成に **PostToolUse は無く**、PreToolUse は**入力しか書き換えられず出力を改変不可** → フックでは偽の `git diff` や偽 system-reminder を生成不能。また偽出力の `+ set +x` は**元タスク記述からの逐語混入（context-bleed）**でバイナリ起因を否定。
- **UNDETERMINED（未特定）**: 一過性異常の発生源・機序は特定できず。コンテンツ層インジェクション / コンテキスト破損 / モデル側 confusion のいずれも開いたまま。**外部攻撃者は断定しない**。
- **推奨**: 重大な追加対応は不要。念のため `cf_tunnel_token` のローテーションは任意（確定漏洩への対応ではなく予防）。
