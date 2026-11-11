"""データベースを使わない設定（DB_HOST=none）で、画面と書き込みを確かめるテスト。"""

import os

os.environ.setdefault("DB_HOST", "none")

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

client = TestClient(app)


def test_トップページが開ける():
    res = client.get("/")
    assert res.status_code == 200
    assert "ひとこと掲示板" in res.text


def test_書き込むと一覧に出る():
    res = client.post("/", data={"text": "はじめまして"})
    assert res.status_code == 200
    assert "はじめまして" in res.text


def test_ヘルスチェック():
    assert client.get("/health").json() == {"status": "ok"}
