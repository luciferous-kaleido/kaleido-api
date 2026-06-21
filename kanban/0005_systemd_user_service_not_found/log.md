# タスク 0005: systemd ユーザーサービス kaleido-api-nginx が見つからない — ログ

## メタデータ
- **開始時刻**: 2026-06-22T03:01:30+09:00
- **ステータス**: 原因特定・修正完了（サーバーでの動作確認待ち）

## タスク概要
`make deploy-quadlet` を実行した後、`systemctl --user status kaleido-api-nginx` でサービスが見つからないというエラーが発生している。
エラーメッセージ：
```
Unit kaleido-api-nginx.service could not be found.
```

## 調査結果

### コードベース構造の確認
- Makefile の `deploy-quadlet` ターゲット（18-21行目）:
  - `check-secret` と `create-quadlet` に依存
  - `mkdir -p "$$HOME/.config/containers/systemd"` でディレクトリを作成
  - `cp dist/quadlet/* "$$HOME/.config/containers/systemd/"` で Quadlet ファイルをコピー
  - `systemctl --user daemon-reload` で systemd を再読み込み

- `scripts/create_quadlets.py` の処理:
  - `kaleido-api-content.volume` (テンプレート生成)
  - `kaleido-api-nginx.container` (テンプレート生成)
  - `kaleido-api.network` (静的コピー)
  - `kaleido-api-cloudflared.container` (静的コピー)

- Quadlet テンプレート (`scripts/templates/kaleido-api-nginx.container.jinja2`):
  - `[Unit]`, `[Container]`, `[Service]`, `[Install]` セクションを含む
  - 標準的な Quadlet ファイル形式

### 想定される原因
Quadlet は `*.container` ファイルを `~/.config/containers/systemd/` に配置すると、systemd が自動的にそれを `*.service` に変換します。考えられるエラー原因：

1. **ファイル生成失敗**: `dist/quadlet/` に Quadlet ファイルが生成されていない
   - `uv run scripts/create_quadlets.py` のエラーがある
   - テンプレートがない、またはパスが間違っている
   - パーミッション問題

2. **ファイルコピー失敗**: `cp dist/quadlet/*` がエラーを起こしている
   - `dist/quadlet/` が存在しない
   - Quadlet ファイルが実際には生成されていない

3. **systemd が認識していない**: ファイルはコピーされたが systemd が認識していない
   - `systemctl --user daemon-reload` が失敗している
   - systemd のバージョンが古い (Quadlet は systemd 254+)
   - ファイルのパーミッションが不正

4. **サービスの有効化**: `systemctl --user enable` が必要かもしれない
   - Quadlet は通常、`systemctl --user start` で起動する
   - `enable` は optional だが、ブート時の自動起動が必要な場合は必要

## 実装プラン

### ステップ1: 現状診断（ユーザーが実行）
以下のコマンドを実行して、環境の状態を確認：

```bash
# 1. Quadlet ファイルが生成されているか確認
ls -la dist/quadlet/

# 2. systemd ユーザーサービスディレクトリを確認
ls -la ~/.config/containers/systemd/

# 3. systemd が認識しているサービスを確認
systemctl --user list-unit-files | grep kaleido

# 4. サービスの詳細情報を確認
systemctl --user status kaleido-api-nginx.service

# 5. コンテナの状態を確認
podman ps -a | grep kaleido

# 6. systemd のバージョンを確認
systemctl --version
```

### ステップ2: 原因特定と修正
上記の診断結果から、以下のいずれかが必要：
- Quadlet ファイル生成エラーの修正
- systemd の設定変更
- Makefile への `systemctl --user enable` ステップ追加

### ステップ3: 修正の実装
確認後、必要な修正を実施：
- Makefile の改善
- スクリプトの改善
- テンプレートの確認

## プランニング経緯
- 初回プランで Quadlet システムの動作、Makefile の処理、想定される原因を整理
- ユーザーの環境で診断を実施して、具体的な原因を特定することで、的確な修正が可能になると判断

## 会話内容
（プランモードでの議論経過）
- CLAUDE.md を確認し、プロジェクトの目的（FastAPI API バックエンドの構築）を理解
- Makefile と スクリプト の処理フローを調査
- Quadlet ファイルの生成と systemd への登録プロセスを理解

## 診断結果（サーバー Ubuntu/kagoya 上で実行）

### コマンド1: `ls -la dist/quadlet/` と `~/.config/containers/systemd/`
両方に4ファイルが存在（ubuntu 所有、06-22 02:51 生成）:
- kaleido-api-cloudflared.container
- kaleido-api-content.volume
- kaleido-api-nginx.container
- kaleido-api.network

→ ファイルの生成・コピーは正常。

### コマンド2: `systemctl --user list-unit-files | grep kaleido`
```
kaleido-api-cloudflared.service        generated -
kaleido-api-content-volume.service     generated -
kaleido-api-network.service            generated -
```
→ **nginx だけ `.service` が生成されていない**。他の3つは generated。これが「Unit not found」の直接原因。

### コマンド3: `systemctl --version`
```
systemd 255 (255.4-1ubuntu8.16)
```
→ systemd 255 で Quadlet 対応済み。systemd バージョンは問題ない。

### コマンド4: `/usr/libexec/podman/quadlet -dryrun -user 2>&1`
**決定的なエラーメッセージを発見**:
```
quadlet-generator: converting "kaleido-api-nginx.container": unsupported key 'NetworkAlias' in group 'Container' in /home/ubuntu/.config/containers/systemd/kaleido-api-nginx.container
```
→ サーバーの podman バージョンでは `[Container]` グループの `NetworkAlias=` キーが未対応。このため generator が nginx.container の変換に失敗し、`.service` を生成できなかった。

## 根本原因
`scripts/templates/kaleido-api-nginx.container.jinja2` に記述されていた:
```
Network=kaleido-api.network
NetworkAlias=nginx
```
の `NetworkAlias=` 独立キーが、サーバーの podman バージョンでサポートされていなかった。`NetworkAlias=` は比較的新しい podman でのみ利用可能なキー。

ネットワークエイリアスを指定する移植性の高い方法は、`Network=` 行に `:alias=` オプションを付ける形式:
```
Network=kaleido-api.network:alias=nginx
```
この `:alias=` 形式は古くからサポートされており、podman のバージョン差異の影響を受けない。

なお cloudflared.container は `NetworkAlias` を使っていない（alias は接続先である nginx 側にのみ必要なため）。そのため cloudflared は正常に generated されていた。

## 編集ファイル
- `scripts/templates/kaleido-api-nginx.container.jinja2`
  - 変更前:
    ```
    Network=kaleido-api.network
    NetworkAlias=nginx
    ```
  - 変更後:
    ```
    Network=kaleido-api.network:alias=nginx
    ```

## 実行コマンド（診断）
- `ls -la dist/quadlet/`
- `ls -la ~/.config/containers/systemd/`
- `systemctl --user list-unit-files | grep kaleido`
- `systemctl --version`
- `/usr/libexec/podman/quadlet -dryrun -user 2>&1 | grep -i -A5 nginx`

## 判断・意思決定
- 当初は「リポジトリ移動によるパス埋め込みズレ」を疑ったが、`ls` の出力でサーバー上で正しく再生成されていることを確認し、別原因と判断。
- 「nginx だけ generated されていない」点に着目し、Quadlet generator の dry-run でエラーを直接取得する方針に切り替えた。これが最短で確実だった。
- 修正は `NetworkAlias=` を削除し `Network=...:alias=nginx` 形式へ統一。これによりエイリアス機能（cloudflared からの `nginx` 名前解決）を維持しつつ、podman バージョン差異に依存しない記述にした。
- `dist/quadlet/` は生成物（gitignore 対象）なので直接編集せず、テンプレートのみ修正。再デプロイ時に再生成される。

## エラー・問題
- `unsupported key 'NetworkAlias'` が唯一かつ決定的なエラー。修正により解消される見込み。

## 検証手順（ユーザーがサーバー上で実施）
```bash
make deploy-quadlet
# dry-run で nginx がエラーなく変換されることを直接確認（最も確実な signal）
/usr/libexec/podman/quadlet -dryrun -user 2>&1 | grep -i nginx   # エラーが出ず alias=nginx が含まれること
systemctl --user list-unit-files | grep kaleido   # nginx を含む4つが generated になることを確認
systemctl --user start kaleido-api-nginx
systemctl --user status kaleido-api-nginx          # active (running) を確認
podman ps                                          # コンテナ稼働を確認
```
> generator は最初の未対応キーで停止するため、`NetworkAlias` の裏に第二の未対応キーがないこと・`:alias=` がこの podman で有効なことを dry-run 再実行で同時に確認する。`list-unit-files` でも間接的に分かるが、dry-run が直接の signal。
