# ひとこと掲示板（hitokoto）

「コンテナ入門 〜Docker で作る・動かす・配る〜」のハンズオンで使うリポジトリです。
ブラウザから短いメッセージを書き込むと、一覧に表示されます。Python の FastAPI で作った小さな Web アプリで、書き込みは PostgreSQL（データベース）に保存します。

**Python のコードは読めなくてかまいません。** コースでは、このアプリをコンテナにして、動かし、配ります。

## 中身

| ファイル | 役割 |
|---|---|
| `main.py` | アプリの本体（画面の表示・書き込みの保存） |
| `templates/` | 画面の HTML |
| `requirements.txt` | アプリが使うライブラリの一覧（版は固定） |
| `requirements-dev.txt` | テストに使う道具（pytest） |
| `tests/` | テスト |
| `.devcontainer/devcontainer.json` | Codespaces の設定（開くと Docker がすぐ使える） |

`Dockerfile` と `compose.yaml` はまだありません。ハンズオンで作ります。

## 使い方

1. このリポジトリの右上の **Use this template** → **Create a new repository** で、自分のリポジトリを作ります。
2. 受講環境に合わせて、どちらかで開きます。
   - **Codespaces（ブラウザだけ）**: 自分のリポジトリの **Code** → **Codespaces** → **Create codespace on main**
   - **自分の PC（Docker Desktop／WSL2＋Docker Engine）**: `git clone` で取ってきて、そのフォルダでターミナルを開く

## 設定（環境変数）

| 名前 | 意味 |
|---|---|
| `DB_HOST` | データベースのコンテナの名前。**必ず渡す**。データベースを使わないときは `none` |
| `DB_PASSWORD` | データベースのパスワード（練習用の値） |

`DB_HOST=none` のときは、書き込みをアプリの中だけに置きます（コンテナを消すと消えます）。
