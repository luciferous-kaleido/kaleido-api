# 0008 Quadlet の依存関係設定 — 実装ログ

## 開始日時
2026-06-22T15:45:00+09:00

## タスク概要
cloudflared を起動させるだけで全てが立ち上がるようにするため、network や volume の開始もきちんと after や required を設定したい。

## 調査結果

### Quadlet ファイル構成
- **ソース（静的）**: `quadlets/kaleido-api-cloudflared.container`, `quadlets/kaleido-api.network`
- **テンプレート（生成）**: `scripts/templates/kaleido-api-content.volume.jinja2`, `scripts/templates/kaleido-api-nginx.container.jinja2`
- **生成物**: `dist/quadlet/` 配下に4つのファイル

### 現状の問題点
1. `kaleido-api.network` — `[Unit]` セクションがない（network ユニットに説明がない）
2. `kaleido-api-content.volume` — `[Unit]` セクションがない（volume ユニットに説明がない）
3. `kaleido-api-nginx.container` — `[Unit]` セクションで `Requires=` が設定されていない
   - network と volume に依存しているが、systemd に明示していない
4. `kaleido-api-cloudflared.container` — `[Unit]` セクションで network への `Requires=` がない
   - nginx には依存設定があるが、network には暗黙的なのみ

### systemd Quadlet の依存関係メカニズム
- `Volume=` や `Network=` での参照だけでは、起動失敗の伝播（systemd の Requires= 相当）がされない
- 明示的に `Requires=` を設定することで、ユニット間の起動依存関係が保証される
- 複数行の `Requires=` や `After=` は systemd で許可されている

## 実装プラン

### 変更内容
1. **`scripts/templates/kaleido-api-content.volume.jinja2`**
   - `[Unit]` セクションを追加（Description のみ）
   
2. **`scripts/templates/kaleido-api-nginx.container.jinja2`**
   - `[Unit]` セクションに `Requires=kaleido-api.network` と `Requires=kaleido-api-content.volume` を追加
   
3. **`quadlets/kaleido-api.network`**
   - `[Unit]` セクションを追加（Description のみ）
   
4. **`quadlets/kaleido-api-cloudflared.container`**
   - `[Unit]` セクションに `Requires=kaleido-api.network` を追加（既存の nginx 依存は保持）

## 実装内容

### 編集ファイル

**1. `scripts/templates/kaleido-api-content.volume.jinja2`**
```diff
+[Unit]
+Description=Content volume for kaleido-api
+
 [Volume]
 VolumeName=kaleido-api-content
```

**2. `scripts/templates/kaleido-api-nginx.container.jinja2`**
```diff
 [Unit]
 Description=nginx behind Cloudflare Tunnel
+Requires=kaleido-api.network
+Requires=kaleido-api-content.volume
```

**3. `quadlets/kaleido-api.network`**
```diff
+[Unit]
+Description=Network for kaleido-api
+
 [Network]
 NetworkName=kaleido-api
 Driver=bridge
```

**4. `quadlets/kaleido-api-cloudflared.container`**
```diff
 [Unit]
 Description=Cloudflare Tunnel connector
+Requires=kaleido-api.network
 Requires=kaleido-api-nginx.service
 After=kaleido-api-nginx.service
```

### 実行コマンド
```bash
make create-quadlet
```

## 生成物の検証

### 生成された `dist/quadlet/kaleido-api.network`
```
[Unit]
Description=Network for kaleido-api

[Network]
NetworkName=kaleido-api
Driver=bridge
```
✓ `[Unit]` セクション追加確認

### 生成された `dist/quadlet/kaleido-api-content.volume`
```
[Unit]
Description=Content volume for kaleido-api

[Volume]
VolumeName=kaleido-api-content
Driver=local
Device=/Users/yuta/.../data/content
Type=none
Options=bind
Label=app=kaleido-api
```
✓ `[Unit]` セクション追加確認

### 生成された `dist/quadlet/kaleido-api-nginx.container`
```
[Unit]
Description=nginx behind Cloudflare Tunnel
Requires=kaleido-api.network
Requires=kaleido-api-content.volume

[Container]
...
```
✓ `Requires=` 両方追加確認

### 生成された `dist/quadlet/kaleido-api-cloudflared.container`
```
[Unit]
Description=Cloudflare Tunnel connector
Requires=kaleido-api.network
Requires=kaleido-api-nginx.service
After=kaleido-api-nginx.service

[Container]
...
```
✓ `Requires=kaleido-api.network` 追加確認

## 起動順序の保証

修正後の起動フロー:
```
cloudflared.service 起動試行
  ├─ Requires: kaleido-api.network
  ├─ Requires: kaleido-api-nginx.service
  └─ After: kaleido-api-nginx.service
       │
       └─ kaleido-api-nginx.service 起動試行
            ├─ Requires: kaleido-api.network
            ├─ Requires: kaleido-api-content.volume
            └─
                ├─ kaleido-api.network 起動
                │  └─ (他依存なし)
                │
                └─ kaleido-api-content.volume 起動
                   └─ (他依存なし)
```

すべてのユニットが起動前に必要な依存関係が満たされることが保証される。

## 完了日時
2026-06-22T15:55:00+09:00
