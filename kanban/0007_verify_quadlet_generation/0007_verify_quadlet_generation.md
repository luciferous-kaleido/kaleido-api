# Quadlet全体の生成確認

## 目的
nginx以外が生成に失敗することもあると思うので。

## 要望
0006に対する追加作業。nginx以外もきちんと作成されたか見て欲しい。

## プラン
1. **Quadlet ファイル生成確認チェック追加**: `deploy-quadlet` ターゲット内で、4 つの Quadlet ファイルが dist/quadlet/ に生成されたか確認
   - kaleido-api-content.volume
   - kaleido-api-nginx.container
   - kaleido-api.network
   - kaleido-api-cloudflared.container
2. **cloudflared.service 確認チェック追加**: systemctl daemon-reload 後に cloudflared.service が生成されたか確認

## 完了サマリー

**完了日時**: 2026-06-22T03:30:00+09:00

### 実装内容
1. **Makefile の修正（18-39行目）**
   - Quadlet ファイル生成確認チェック（19-28行目）：4 ファイル全て dist/quadlet/ に存在するか確認、欠落時は エラー出力して exit 1
   - cloudflared.service 確認チェック（36-39行目）：systemctl --user list-unit-files で kaleido-api-cloudflared.service が生成されたか確認

2. **テスト実施**
   - `make create-quadlet` で 4 ファイル全て生成確認 ✓
   - Quadlet ファイル存在確認チェック正常動作 ✓
   - エラー検出正常動作（ファイル欠落時に適切なエラーメッセージと exit 1） ✓
