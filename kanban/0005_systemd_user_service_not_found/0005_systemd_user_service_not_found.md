# systemd ユーザーサービス kaleido-api-nginx が見つからない

## 目的
デプロイで足りていないものがあるのなら修正したいから。

## 要望
make deploy-quadlet をした後 `systemctl --user status kaleido-api-nginx` としたら見つからないとエラーが出た。何故か教えて。

## エラー
```
❯ systemctl --user status kaleido-api-nginx
Unit kaleido-api-nginx.service could not be found.
```

## 完了サマリー

**完了日時**: 2026-06-22T03:01:30+09:00

### 原因
nginx の Quadlet (`kaleido-api-nginx.container`) だけが `.service` に変換されておらず、これが "Unit not found" の正体だった。サーバー（Ubuntu/kagoya, systemd 255）上で `/usr/libexec/podman/quadlet -dryrun -user` を実行したところ、決定的なエラーを確認:

```
converting "kaleido-api-nginx.container": unsupported key 'NetworkAlias' in group 'Container'
```

`scripts/templates/kaleido-api-nginx.container.jinja2` の `NetworkAlias=nginx` 独立キーを、サーバーの podman が認識できなかった。このため Quadlet generator が nginx.container の変換に失敗し、`.service` が生成されなかった（他の3ユニットは正常に generated されていた）。

（注: `NetworkAlias=` がサポートされるか否かは podman のバージョンに依存するが、サーバーの `podman --version` は未確認。`:alias=` 形式は広いバージョンで有効なため、いずれにせよ修正は妥当。）

ファイルの生成・コピー・systemd バージョンはいずれも正常で、問題はテンプレートの記述のみだった。

### 修正
`scripts/templates/kaleido-api-nginx.container.jinja2` を移植性の高い `:alias=` 形式に変更:

```diff
-Network=kaleido-api.network
-NetworkAlias=nginx
+Network=kaleido-api.network:alias=nginx
```

`:alias=` オプションは podman の広いバージョンでサポートされており、エイリアス機能（cloudflared からの `nginx` 名前解決）を維持しつつバージョン差異に依存しない。`dist/quadlet/` は生成物のためテンプレートのみ修正（再デプロイ時に再生成）。

### 検証手順（サーバー上で実施）
```bash
make deploy-quadlet
# まず dry-run で nginx がエラーなく変換されることを直接確認（最も確実な signal）
/usr/libexec/podman/quadlet -dryrun -user 2>&1 | grep -i nginx   # エラーが出ず alias=nginx が含まれること
systemctl --user list-unit-files | grep kaleido                  # nginx を含む4つが generated になること
systemctl --user start kaleido-api-nginx
systemctl --user status kaleido-api-nginx                        # active (running) を確認
```
> dry-run を再実行するのは、generator が最初の未対応キーで停止する性質があるため。`NetworkAlias` の裏に第二の未対応キーが隠れていないこと、`:alias=` 形式自体がこの podman で有効なことを、この一手で同時に確認できる。

### 残課題
- 原因特定・修正は完了。**サーバー上での再デプロイ・動作確認はユーザー側で実施が必要**（上記検証手順）。
- (任意の改善案) 今回 `make deploy-quadlet` はユニット生成が静かに失敗したのに成功扱いになっていた。deploy ターゲット末尾に `quadlet -dryrun` のエラーチェックを一行加えると、この種の失敗を次回以降検知できる。本タスクの範囲外のため別途検討。
