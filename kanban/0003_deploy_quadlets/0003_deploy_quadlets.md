# Quadlet の生成と配置を行うコマンドを追加

## 目的
生成から配置を一つのコマンドで実行できるようにしつつ、secret の確認を行い、なければ失敗するようにしたい。

## 要望
生成したquadletのファイルを配置するコマンドをMakefileに追加して。そのコマンドではsecretの確認とquadletのファイル生成の二つをこの順で実行してから動かすようにして。配置先のディレクトリは `make -p`で作成して。

## プラン
`Makefile` に新ターゲット `deploy-quadlet` を追加する。

- prerequisite に `check-secret create-quadlet` をこの順で指定し、secret 確認 → Quadlet 生成の順に実行（secret がなければ `check-secret` が失敗し全体が止まる）。
- レシピ本体: `mkdir -p "$HOME/.config/containers/systemd"` → `cp dist/quadlet/* "$HOME/.config/containers/systemd/"` → `systemctl --user daemon-reload`。
- `.PHONY` に `deploy-quadlet` を追加。
- タスク文の「`make -p`」は `mkdir -p` の誤記と解釈。配置先は rootless Podman 標準の `~/.config/containers/systemd/`。

## 完了サマリー

- **完了日時**: 2026-06-22T02:10:37+09:00
- **対応内容**: `Makefile` に `deploy-quadlet` ターゲットを追加した。
  - prerequisite `check-secret create-quadlet` により「secret 確認 → Quadlet 生成」の順序を保証。secret 未登録時は `check-secret` が失敗し処理が止まる。
  - レシピ本体で配置先ディレクトリを `mkdir -p` で作成 → `dist/quadlet/*` をコピー → `systemctl --user daemon-reload` で systemd に登録。
  - `.PHONY` に `deploy-quadlet` を追加。
- **検証**: `make -n deploy-quadlet` の dry-run で「`podman secret exists` → `uv run scripts/create_quadlets.py` → `mkdir -p` → `cp` → `daemon-reload`」の順序を確認。実機実行は配置先 (Linux) 環境で行う想定。
- **編集ファイル**: `Makefile`
