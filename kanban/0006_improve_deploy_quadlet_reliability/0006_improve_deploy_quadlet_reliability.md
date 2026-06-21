# deploy-quadlet ターゲットのエラーチェック強化

## 目的
正常に生成が行われるようにしたい。

## 要望
0005 の追加作業として、dry-run の追加と jinja2 テンプレートの修正を行ってほしい。具体的には：
- Makefile の `deploy-quadlet` ターゲットに、デプロイ後に Quadlet generator が正常にユニットを生成できたかを検証するステップを追加
- `scripts/templates/kaleido-api-nginx.container.jinja2` の NetworkAlias キーを修正し、より広い podman バージョンで動作する形式に変更

## プラン
1. **テンプレート修正（既実装）**: `Network=kaleido-api.network:alias=nginx` に統一済み
2. **nginx.service 生成確認チェック追加**: Makefile の `deploy-quadlet` ターゲットに以下を追加
   ```makefile
   @systemctl --user list-unit-files | grep -q '^kaleido-api-nginx\.service' || { \
       echo "Error: kaleido-api-nginx.service was not generated" >&2; \
       exit 1; \
   }
   ```
   これにより、daemon-reload 後に `kaleido-api-nginx.service` が実際に生成されたことを検証。0005 で発生した「静かな失敗」を検知できる

## 完了サマリー

**完了日時**: 2026-06-22T03:08:19+09:00

### 実装内容
1. **Makefile の修正（22-25行目追加）**
   - `systemctl --user daemon-reload` の後に `systemctl --user list-unit-files` で確認
   - `kaleido-api-nginx.service` が生成されているか grep で判定
   - 生成されていなければ stderr に "Error: kaleido-api-nginx.service was not generated" を出力して exit 1
   - 生成されていれば何も出力せず続行
   - この方法は generator の exit code に依存せず、0005 で実際に発生した「静かな失敗」を直接検知できる

2. **テンプレート修正（既実装の確認）**
   - `scripts/templates/kaleido-api-nginx.container.jinja2` の 7 行目が `Network=kaleido-api.network:alias=nginx` になっていることを確認
   - cloudflared からネットワークエイリアス `nginx` で接続可能になる形式に統一

### 残課題
**サーバー上での動作確認が必要**（実装は完了）。以下を実施して確認：
```bash
make deploy-quadlet          # エラーメッセージが出ないことを確認（成功）
systemctl --user list-unit-files | grep kaleido   # nginx を含む4ユニットが generated に
systemctl --user status kaleido-api-nginx.service  # active (running)
```

修正前に同じサーバーで「既知の悪い状態」を再現して、新しいチェックが正しく検知するか確認することも推奨（テンプレートを一時的に旧形式に戻す など）。
