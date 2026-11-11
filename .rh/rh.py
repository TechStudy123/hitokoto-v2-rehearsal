# -*- coding: utf-8 -*-
"""ハンズオンの説明資料（HTML）のリハーサル用の部品（2026-10-08 fastapiai で作成。ガイドの改善依頼
「コードを書くハンズオンも通しのリハーサルを必須に」）。

ねらい: 説明資料に書いたコマンド・コードを、**HTML から抜き出して**そのとおりに実行し、資料と実際の動きのずれを無くす。
資料とリハーサルで別の手順を書かない。

1) 説明資料を作るとき（hlib の出力に印を付ける）
    import rh
    rh.mark(hlib.win_mac(win, mac), t="cmd")                    # コマンド（PowerShell とターミナルの両方）
    rh.mark(hlib.cmd("uv run python check.py"), t="cmd")         # どちらの OS でも同じコマンド
    rh.mark(hlib.cmd("uv run python err.py"), t="cmd", rc=1)    # エラーで終わるのが正しい手順（終了コード1を期待。2026-10-19 fastapiai で追加）
    rh.mark(hlib.cmd("uv run fastapi dev app/main.py"), t="cmd", bg=True, wait="http://127.0.0.1:8000/docs")  # 起動したままにする
    rh.mark(hlib.file(1, "app/main.py", "新しく作る"), t="file", path="app/main.py")       # ファイルを作る・置き換える
    rh.mark(hlib.out("…"), t="expect", contains=["Application startup complete"])          # 直前のコマンドの出力の確かめ
    rh.check(t="http", method="GET", url="http://127.0.0.1:8000/hello", status=200, json={"message": "こんにちは"})  # 画面の操作の代わりの確かめ（見えない印）
    rh.check(t="tree", root="helpdesk-api", files=["pyproject.toml", "app/__init__.py"], absent=["src"])  # 「この時点の構成」
    rh.check(t="stop")                                            # 起動したものを止める（Ctrl＋C）
    rh.mark(hlib.cmd("uv run procrastinate worker"), t="cmd", bg=True, name="worker", wait="log:Starting worker")  # HTTP の入り口が無いもの: ログにその文字が出たら起動完了（2026-10-21 genaiops）
    rh.check(t="stop", name="worker")                             # 名前を付けた bg だけ止める（ほかは動かしたまま。止めた後のログが次の照合の出力になる）
    rh.check(t="stop", name="worker", ctrlc=2)                    # Ctrl＋C を2回（1回目の後 grace 秒〔既定5〕待ち、まだ動いていればもう1回。Linux／macOS。Windows は今までどおり強制終了）
    rh.check(t="secret", path=".env", key="GEMINI_API_KEY")      # キーを貼る手順（リハーサルでは用意したキーを入れる）
    rh.check(t="copy", src="完成プロジェクト/第1章/helpdesk-api", dst="helpdesk-api")  # 配布資料（展開した zip）からコピーする手順
    rh.check(t="http", method="POST", url=".../auth/login", form={...}, save={"token": "access_token"})   # 返ってきた値を覚える
    rh.check(t="http", url=".../me/usage", headers={"Authorization": "Bearer {token}"})               # {token} に置き換えて使う
    rh.check(t="http", method="POST", url=".../documents", files={"file": "docs/就業規則.md"}, headers=…)  # ファイルを送る（multipart）
    rh.check(t="env", key="JWT_SECRET", value="{random}")         # .env の1行を設定する（{random} は乱数）
    llm=True を付けた手順は、AI のサービスを呼ぶもの。キーのファイルが無い環境（クラウド）では飛ばす（Windows のリハーサルで確かめる）。
    飛ばした手順の直後の「表示される内容」は照合しない（比べる出力が無い扱い。2026-10-21）
    コマンドの出力の改行（Windows の \r\n）は \n にそろえてから expect・照合に使う（2026-10-21）
    Windows の bg は powershell -Command で起動する（-File の .ps1 だと fastapi dev の読み込み直しが効かなかった。2026-10-21 genaiops。
    戻すときは環境変数 RH_BG_WIN=file）
    印の付いていないコマンドは実行しない（VS Code の操作・AI ツールへの指示など）。`code .` のようにエディターを開くだけの行は、印があっても実行しない。skip=True で、表示はするが実行しないことを明示できる。

   印の無い「表示される内容」（hlib.out の <div class="code-block out">）も "out" の手順として抜き出し、
   直前のコマンドの実際の出力に、その行が同じ順で出るかを照合する（WARN。NG にはしない。2026-10-15 追加。ガイド01 §28 の 7）。
   日時・番号・ID などの数字はゆるく比べ、「…」「...」だけの行は飛ばし、行の中の「…」は何が入ってもよいとみなす。
   ラベルに「並び」と「変わ」を含む（例「並び方は環境によって変わります」）ときは、順番は見ずに、行があるかだけを見る。
   照合を止めるときは run に --no-out-check。

2) 抜き出す:  python3 rh.py extract <説明資料.html> > steps.json
3) 実行する:
    - Linux／macOS の手順: python3 rh.py run steps.json --os mac --work <作業フォルダ> [--env-file キーのファイル]
    - Windows の手順: rh_win.py（ユーザーの PC の受付係から。PowerShell で同じ steps.json を実行する）
   どちらも、結果を JSON とログに書く（NG の手順・期待との違い）。
"""
import html as _html
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

_OPEN = urllib.request.build_opener(urllib.request.ProxyHandler({})).open   # 手元の API はプロキシを通さない
from html.parser import HTMLParser


def _attr(d):
    return _html.escape(json.dumps(d, ensure_ascii=False), quote=True)


def mark(block_html: str, **d) -> str:
    """hlib が返した HTML の最初の要素に data-rh を付ける"""
    m = re.match(r"\s*<(\w+)", block_html)
    if not m:
        raise ValueError("HTML の先頭に要素がありません")
    i = m.end()
    return block_html[:i] + f' data-rh="{_attr(d)}"' + block_html[i:]


def check(**d) -> str:
    """画面には出ない確かめの印（ブラウザで開く・/docs で実行する、などの代わりに HTTP で確かめる）"""
    return f'<template data-rh="{_attr(d)}"></template>'


# ---------------------------------------------------------------- 抜き出し
class _P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.steps = []
        self.stack = []        # (tag, step or None, depth-info)
        self.cur = None        # 抜き出し中の step
        self.depth = 0
        self.in_pre = 0
        self.label = None
        self.in_label = False
        self.buf = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("br", "img", "input", "meta", "link"):
            return
        self.depth += 1
        cls0 = (a.get("class", "") or "").split()
        if self.cur is None and tag == "div" and "code-block" in cls0 and "out" in cls0:
            # 2026-10-15: 印の無い「表示される内容」も抜き出す（実際の出力と行の順番を照合する。WARN）
            self.cur = {"t": "out", "_depth": self.depth, "_blocks": []}
        if "data-rh" in a:
            st = json.loads(a["data-rh"])
            if tag == "template" or st.get("t") in ("http", "tree", "stop", "secret", "wait", "env", "copy", "expect"):
                self.steps.append(st)
            else:
                st["_depth"] = self.depth
                st["_blocks"] = []
                self.cur = st
        if self.cur is not None:
            cls = a.get("class", "") or ""
            if tag == "span" and "label" in cls.split():
                self.in_label = True
                self.label = []
            if tag == "pre":
                self.in_pre += 1
                self.buf = []

    def handle_endtag(self, tag):
        if tag in ("br", "img", "input", "meta", "link"):
            return
        if self.cur is not None:
            if tag == "span" and self.in_label:
                self.in_label = False
            if tag == "pre" and self.in_pre:
                self.in_pre -= 1
                lab = "".join(self.label or [])
                self.cur["_blocks"].append({"label": lab, "text": "".join(self.buf)})
            if self.depth == self.cur["_depth"]:
                st = self.cur
                st.pop("_depth")
                self.steps.append(st)
                self.cur = None
        self.depth -= 1

    def handle_data(self, data):
        if self.cur is not None:
            if self.in_label and self.label is not None:
                self.label.append(data)
            if self.in_pre:
                self.buf.append(data)


def extract(path):
    p = _P()
    p.feed(open(path, encoding="utf-8").read())
    out = []
    for st in p.steps:
        bl = st.pop("_blocks", None)
        if bl is not None:
            if st["t"] == "cmd":
                win = [b["text"] for b in bl if b["label"].startswith("PowerShell")]
                mac = [b["text"] for b in bl if b["label"].startswith("ターミナル")]
                both = [b["text"] for b in bl if not (b["label"].startswith("PowerShell") or b["label"].startswith("ターミナル"))]
                if len(bl) == 1 and not win and not mac:
                    win = mac = both
                if len(bl) == 1 and (win or mac) and not (win and mac):
                    # ラベルが「ターミナル」だけの1つのブロックは、両方の OS で同じコマンド
                    win = mac = win or mac
                st["win"] = win[0] if win else None
                st["mac"] = mac[0] if mac else None
            elif st["t"] in ("file", "expect", "out"):
                st["text"] = bl[0]["text"] if bl else ""
                st["label"] = bl[0]["label"] if bl else ""
        out.append(st)
    return out


# ---------------------------------------------------------------- 実行（Linux／macOS の手順）
def _fill(v, vars):
    """{名前} を、前の手順で保存した値に置き換える（文字列・辞書・リストの中も）"""
    if isinstance(v, str):
        for k, x in vars.items():
            v = v.replace("{" + k + "}", str(x))
        return v
    if isinstance(v, dict):
        return {k: _fill(x, vars) for k, x in v.items()}
    if isinstance(v, list):
        return [_fill(x, vars) for x in v]
    return v


def _multipart(files, fields, cwd):
    import uuid
    b = "----rh" + uuid.uuid4().hex
    parts = []
    for k, v in (fields or {}).items():
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for k, path in files.items():
        p = os.path.join(cwd, path)
        name = os.path.basename(p)
        ct = "application/pdf" if name.lower().endswith(".pdf") else "text/markdown" if name.lower().endswith(".md") else "application/octet-stream"
        # ブラウザ（/docs の画面）と同じく、ファイル名は UTF-8 のまま送る（% で符号化すると、API 側にそのまま残る）
        head = (f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{name}"\r\n'
                f"Content-Type: {ct}\r\n\r\n").encode("utf-8")
        parts.append(head + open(p, "rb").read() + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={b}"


def _http(st, vars=None, cwd="."):
    """st: method・url・body（JSON）・form・files（{欄: ファイル}）・headers・status・json（一部一致）・contains・save（{名前: JSON のキー}）"""
    vars = vars if vars is not None else {}
    st = _fill(dict(st), vars)
    data = None
    headers = {}
    if "body" in st:
        data = json.dumps(st["body"], ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json"
    if "form" in st and "files" not in st:
        data = urllib.parse.urlencode(st["form"]).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if "files" in st:
        data, headers["Content-Type"] = _multipart(st["files"], st.get("form"), cwd)
    headers.update(st.get("headers", {}))
    req = urllib.request.Request(st["url"], data=data, method=st.get("method", "GET"), headers=headers)
    try:
        with _OPEN(req, timeout=st.get("timeout", 120)) as r:
            code, body = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        code, body = e.code, e.read().decode("utf-8", "replace")
    ok = code == st.get("status", 200)
    msg = f"{st.get('method','GET')} {st['url']} → {code}"
    got = None
    try:
        got = json.loads(body)
    except Exception:
        pass
    if ok and "json" in st:
        if not isinstance(got, dict):
            ok = False
            msg += "（JSON ではない）"
        else:
            for k, v in st["json"].items():
                if got.get(k) != v:
                    ok = False
                    msg += f"（{k}: 期待 {v!r} / 実際 {got.get(k)!r}）"
    if ok and "contains" in st:
        for c in st["contains"]:
            if c not in body:
                ok = False
                msg += f"（「{c}」が無い）"
    if ok and st.get("save"):
        for name, key in st["save"].items():
            if isinstance(got, dict) and key in got:
                vars[name] = got[key]
            else:
                ok = False
                msg += f"（保存する {key} が無い）"
    return ok, msg, body[:2000]



# ---------------------------------------------------------------- OS ごとの実行
WIN_WORK = "C:\\work"     # 説明資料に書いた作業フォルダ（Windows）。リハーサルでは --work に置き換える
MAC_WORK = "~/work"
# 2026-10-09: 作業フォルダの例をユーザーフォルダの handson にしたコース（fastapiai。動画と同じ）のため、こちらも置き換える
WIN_WORKS = (WIN_WORK, "~\\handson")
MAC_WORKS = (MAC_WORK, "~/handson")


def _subst(text, os_name, work):
    if os_name == "mac":
        for w in MAC_WORKS:
            text = re.sub(re.escape(w) + r"(?=/|\s|$)", lambda m: work, text)
        return text
    for w in WIN_WORKS:
        text = re.sub(re.escape(w) + r"(?=\\|\s|$)", lambda m: work, text, flags=re.I)
    return text


def _read(p):
    try:
        b = open(p, "rb").read()
    except OSError:
        return ""
    for enc in ("utf-8", "cp932"):
        try:
            return b.decode(enc).replace("\r\n", "\n")
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", "replace").replace("\r\n", "\n")


def _ps_script(text, cwd_marker=True):
    """PowerShell 5.1 でも、外部コマンドの失敗（終了コード）で止まるようにする"""
    lines = ["$ErrorActionPreference = 'Continue'", "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8",
             "$OutputEncoding = [System.Text.Encoding]::UTF8", "$global:LASTEXITCODE = 0"]
    for l in text.split("\n"):
        if not l.strip():
            continue
        lines.append(l)
        lines.append("if ((-not $?) -or ($LASTEXITCODE -ne 0)) { Write-Output \"__EXIT__=$LASTEXITCODE\"; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } else { exit 1 } }")
    if cwd_marker:
        lines.append('Write-Output "__CWD__=$((Get-Location).Path)"')
    return "\r\n".join(lines) + "\r\n"


def _last_cwd(out):
    """出力から作業の場所（__CWD__=）を読む。行の先頭にあり、絶対パス（/ か X:\ で始まる）の、最後の1つだけを使う。
    2026-10-13 修正: ps aux | grep などの出力に、実行中の命令の文字（echo __CWD__=$PWD）が写り込み、
    '$PWD' を作業の場所と読み違えた（linuxnyumon H7）。"""
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("__CWD__="):
            v = line[len("__CWD__="):].strip()
            if v.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", v):
                return v
    return None


def _run_fg(text, cwd, os_name, timeout):
    if os_name == "mac":
        cp = subprocess.run(["bash", "-lc", "set -e\n" + text + "\necho __CWD__=$PWD"], cwd=cwd, capture_output=True, text=True, timeout=timeout)
        outp = (cp.stdout + cp.stderr).replace("\r\n", "\n")
        return cp.returncode, outp, _last_cwd(cp.stdout)
    import tempfile
    fd, ps1 = tempfile.mkstemp(suffix=".ps1")
    os.close(fd)
    open(ps1, "w", encoding="utf-8-sig").write(_ps_script(text))
    cp = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1], cwd=cwd,
                        capture_output=True, timeout=timeout)
    os.remove(ps1)
    outp = (cp.stdout or b"").decode("utf-8", "replace") + (cp.stderr or b"").decode("utf-8", "replace")
    outp = outp.replace("\r\n", "\n")
    return cp.returncode, outp, _last_cwd(outp)


def _start_bg(text, cwd, logf, os_name):
    if os_name == "mac":
        return subprocess.Popen(["bash", "-lc", text], cwd=cwd, stdout=open(logf, "w"), stderr=subprocess.STDOUT, start_new_session=True)
    # 別のコンソールで動かす（見えない窓）。-Command で起動する（-File の .ps1 で起動すると、fastapi dev が保存で
    # 「Reloading...」と出してもサーバーが止まらず、古いコードのまま動き続けた。2026-10-21 genaiops H3→H4 の Windows で調べた結果）。
    # 以前の -File の起動に戻すときは環境変数 RH_BG_WIN=file
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0
    if os.environ.get("RH_BG_WIN", "").lower() != "file":
        lines = [l for l in text.split("\n") if l.strip()]
        cmd = "; ".join(["Set-Location -LiteralPath '" + str(cwd).replace("'", "''") + "'"] + lines)
        return subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd], cwd=cwd,
                                stdout=open(logf, "wb"), stderr=subprocess.STDOUT,
                                creationflags=subprocess.CREATE_NEW_CONSOLE, startupinfo=si)
    import tempfile
    fd, ps1 = tempfile.mkstemp(suffix=".ps1")
    os.close(fd)
    open(ps1, "w", encoding="utf-8-sig").write(_ps_script(text, cwd_marker=False))
    # 別のコンソールで動かす（見えない窓）。uvicorn の自動の読み込み直しは Windows で Ctrl＋C の信号を同じコンソールの
    # すべてのプロセスに送るため、同じコンソールだと受付係（runner.py）まで止まる（2026-10-08 fastapiai H2 で発生）
    return subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1], cwd=cwd,
                            stdout=open(logf, "wb"), stderr=subprocess.STDOUT,
                            creationflags=subprocess.CREATE_NEW_CONSOLE, startupinfo=si)


def _free_port(url, os_name, log=print):
    """待つ URL のポートを、前の回の残りのサーバーが使っていれば止める（2026-10-08 fastapiai: 受付係が止まった後に
    H2 の API が残り、H3 以降が古い API にアクセスして 404 になった）"""
    from urllib.parse import urlparse
    port = urlparse(url).port or 80
    try:
        _OPEN(url, timeout=2)
        busy = True
    except urllib.error.HTTPError:
        busy = True
    except Exception:
        busy = False
    if not busy:
        return True
    log(f"      ポート {port} を前のサーバーが使っているので止める")
    if os_name == "mac":
        subprocess.run(["bash", "-lc", f"(fuser -k {port}/tcp || lsof -ti tcp:{port} | xargs -r kill -9) 2>/dev/null"], capture_output=True)
    else:
        ps = (f"Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue | "
              f"ForEach-Object {{ taskkill /T /F /PID $_.OwningProcess | Out-Null }}")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
    for _ in range(10):
        time.sleep(1)
        try:
            _OPEN(url, timeout=2)
        except urllib.error.HTTPError:
            continue
        except Exception:
            return True
    return False


def _stop(p, os_name, ctrlc=1, grace=5):
    """ctrlc=2: Ctrl＋C を2回（1回目の後 grace 秒待ち、まだ動いていればもう1回。Linux／macOS）"""
    try:
        if os_name == "mac":
            os.killpg(p.pid, signal.SIGINT)
            if ctrlc >= 2:
                try:
                    p.wait(timeout=grace)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGINT)
            p.wait(timeout=15)
        else:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
            p.wait(timeout=15)
    except Exception:
        try:
            if os_name == "mac":
                os.killpg(p.pid, signal.SIGKILL)
            else:
                p.kill()
        except Exception:
            pass


_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def _line_pat(line):
    """資料の1行を、ゆるい正規表現にする（数字・16進の ID・空白の数はゆるく、「…」は何でもよい）"""
    parts = re.split(r"…|\.\.\.", line.strip())
    out = []
    for p in parts:
        q = re.escape(p)
        q = re.sub(r"(?:\\\s|\s)+", r"\\s+", q)            # 空白の数
        q = re.sub(r"[0-9]+", "[0-9]+", q)                       # 日時・番号・大きさ
        out.append(q)
    return re.compile(".*".join(out))


def out_order(expected, actual, ordered=True):
    """資料の「表示される内容」の行が、実際の出力に同じ順で出るかを見る。違いの一覧を返す（空なら OK）。"""
    act = [_ANSI.sub("", l).replace("\\", "/").rstrip() for l in actual.replace("\r", "").split("\n")]
    act = [re.sub(r"\b[0-9a-f]{7,64}\b", "0", l) for l in act]
    diffs, pos = [], 0
    for line in expected.replace("\r", "").split("\n"):
        e = line.strip()
        if not e or re.fullmatch(r"[…\.⋮・\s]+", e):
            continue
        e2 = re.sub(r"\b[0-9a-f]{7,64}\b", "0", e.replace("\\", "/"))
        pat = _line_pat(e2)
        hit = next((j for j in range(pos if ordered else 0, len(act)) if pat.search(act[j])), None)
        if hit is not None:
            if ordered:
                pos = hit + 1
            continue
        anywhere = any(pat.search(a) for a in act)
        diffs.append(f"「{e}」" + ("の順番が違う" if anywhere else "が実際の出力に無い"))
    return diffs


def run(steps, os_name, work, env_file=None, log=print, dist=None, out_check=True):
    os.makedirs(work, exist_ok=True)
    # Streamlit の初回の「メールアドレスを入力」の問いで止まらないようにする（画面の無い実行）
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    cwd = work
    bg = []
    vars = {}
    results = []
    last_out = ""
    cmp_out = None     # 「表示される内容」と比べる出力（直前のコマンドを実行しなかったときは None）
    n_warn = 0
    home = os.path.expanduser("~")
    for i, st in enumerate(steps, 1):
        t = st["t"]
        r = {"n": i, "t": t, "ok": True, "msg": ""}
        if t == "out":
            if not out_check:
                continue
            if cmp_out is None:
                r["msg"] = "表示される内容: 比べる出力が無い（直前のコマンドを実行していない）"
                results.append(r)
                continue
            lab = st.get("label", "") or ""
            ordered = not ("並び" in lab and "変わ" in lab)
            diffs = out_order(st.get("text", ""), cmp_out, ordered)
            if diffs:
                n_warn += 1
                r.update(warn=diffs, msg="表示される内容と実際の出力が違う（WARN）: " + " ".join(diffs[:8]), out=cmp_out[-1500:])
                log(f"[WARN] {i:02d} out: {r['msg'][:600]}")
                log("      " + cmp_out[-1500:].replace("\n", "\n      "))
            else:
                r["msg"] = "表示される内容 OK" + ("（行が同じ順で出た）" if ordered else "（行がすべて出た）")
                log(f"[OK] {i:02d} out: {r['msg']}")
            results.append(r)
            continue
        if st.get("skip"):
            if t == "cmd":
                cmp_out = None
            r["msg"] = "skip（表示だけ）"
            results.append(r)
            continue
        if st.get("llm") and not (env_file and os.path.exists(env_file)):
            r["msg"] = "skip（AI を呼ぶ手順。キーのファイルが無い）"
            r["skipped"] = True
            cmp_out = None     # 直後の「表示される内容」は照合しない（その前のコマンドの出力と比べない）
            log(f"[--] {i:02d} {t}: {r['msg']}")
            results.append(r)
            continue
        try:
            if t == "cmd":
                text = st.get("mac") if os_name == "mac" else st.get("win")
                if text is None:
                    cmp_out = None
                    r["msg"] = "この OS のコマンドは無い"
                    results.append(r)
                    continue
                text = _subst(text, os_name, work)
                # エディターを開くだけの行（code .・code .env）は実行しない（画面の操作）
                text = "\n".join(l for l in text.split("\n") if not re.match(r"^\s*code(\s|$)", l))
                if st.get("bg"):
                    logf = os.path.join(work, f"_bg{i}.log")
                    wait = st.get("wait") or ""
                    logwait = wait[4:] if wait.startswith("log:") else None
                    if wait and logwait is None and not _free_port(wait, os_name, log):
                        r.update(ok=False, msg=f"ポートが空かない（前のサーバーが残っている）: {st['wait']}")
                        log(f"[NG] {i:02d} {t}: {r['msg']}")
                        results.append(r)
                        continue
                    p = _start_bg(text, cwd, logf, os_name)
                    bg.append((st.get("name"), p, logf))
                    ok = False
                    for _ in range(int(st.get("timeout", 120))):
                        time.sleep(1)
                        if logwait is not None:
                            # ログにその文字が出たら起動完了（HTTP の入り口が無いワーカーなど）
                            if logwait in _read(logf):
                                ok = True
                                break
                            if p.poll() is not None:
                                break
                            continue
                        try:
                            _OPEN(st["wait"], timeout=3)
                            ok = True
                            break
                        except urllib.error.HTTPError:
                            ok = True
                            break
                        except Exception:
                            if p.poll() is not None:
                                break
                    last_out = _read(logf)
                    cmp_out = last_out
                    r.update(ok=ok, msg=f"起動 {'OK' if ok else 'NG'}: {text}", out=last_out[-3000:])
                else:
                    code, last_out, newcwd = _run_fg(text, cwd, os_name, st.get("timeout", 900))
                    cmp_out = re.sub(r"(?m)^__CWD__=.*\n?", "", last_out)
                    if newcwd:
                        cwd = newcwd
                    r.update(ok=code == st.get("rc", 0), msg=f"exit {code}" + (f"（期待 {st['rc']}）" if "rc" in st else "") + f": {text}", out=last_out[-3000:])
            elif t == "file":
                p = os.path.join(cwd, st["path"])
                os.makedirs(os.path.dirname(p), exist_ok=True)
                body = st["text"]
                if st.get("mode") == "append":
                    open(p, "a", encoding="utf-8").write(body + "\n")
                else:
                    open(p, "w", encoding="utf-8").write(body + ("\n" if not body.endswith("\n") else ""))
                r["msg"] = f"{st.get('mode','write')}: {st['path']}"
            elif t == "expect":
                norm = last_out.replace("\\", "/")   # Windows の区切り（\）を / にそろえて比べる
                for c in st.get("contains", []):
                    if c not in last_out and c.replace("\\", "/") not in norm:
                        r["ok"] = False
                        r["msg"] += f"「{c}」が出力に無い。"
                r["msg"] = r["msg"] or "出力 OK"
            elif t == "http":
                ok, msg, body = _http(st, vars, cwd)
                r.update(ok=ok, msg=msg, out=body)
            elif t == "tree":
                root = os.path.join(cwd, st.get("root", "")) if st.get("root") and not os.path.isabs(st.get("root")) else cwd
                miss = [f for f in st.get("files", []) if not os.path.exists(os.path.join(root, f))]
                extra = [f for f in st.get("absent", []) if os.path.exists(os.path.join(root, f))]
                listing = sorted(os.listdir(root)) if os.path.isdir(root) else []
                if "exact" in st:
                    want = sorted(st["exact"])
                    got = sorted(x for x in listing if x not in st.get("ignore", []))
                    if want != got:
                        extra.append(f"一覧が違う: 期待 {want} / 実際 {got}")
                r.update(ok=not miss and not extra, msg=f"無い: {miss} / あってはいけない: {extra}" if (miss or extra) else "構成 OK", out=str(listing))
            elif t == "secret":
                key = None
                if env_file and os.path.exists(env_file):
                    for line in open(env_file, encoding="utf-8"):
                        if line.startswith(st["key"] + "="):
                            key = line.strip().split("=", 1)[1]
                p = os.path.join(cwd, st["path"])
                lines = open(p, encoding="utf-8").read().splitlines() if os.path.exists(p) else []
                lines = [f"{st['key']}={key or ''}" if l.startswith(st["key"] + "=") else l for l in lines]
                open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
                if key:
                    r["msg"] = "キーを入れた"
                else:
                    r.update(msg="skip（キーのファイルが無い。キーは空のまま）", skipped=True)
            elif t == "stop":
                name = st.get("name")
                hit = [b for b in bg if name is None or b[0] == name]
                for _, p, _lf in hit:
                    _stop(p, os_name, st.get("ctrlc", 1), st.get("grace", 5))
                bg = [b for b in bg if b not in hit]
                if name is not None:
                    if not hit:
                        r.update(ok=False, msg=f"止める bg（name={name}）が無い")
                    else:
                        time.sleep(0.5)
                        last_out = _read(hit[-1][2])
                        cmp_out = last_out
                        r.update(msg=f"止めた（{name}）", out=last_out[-3000:])
                else:
                    r["msg"] = "止めた"
            elif t == "env":
                p = os.path.join(cwd, st.get("path", ".env"))
                lines = open(p, encoding="utf-8").read().splitlines() if os.path.exists(p) else []
                val = st["value"]
                if val == "{random}":
                    import secrets
                    val = secrets.token_urlsafe(32)
                hit = False
                for j, l in enumerate(lines):
                    if l.startswith(st["key"] + "="):
                        lines[j] = f"{st['key']}={val}"
                        hit = True
                if not hit:
                    lines.append(f"{st['key']}={val}")
                open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
                r["msg"] = f".env の {st['key']} を設定"
            elif t == "copy":
                import shutil
                src = os.path.join(dist or "", st["src"])
                dst = os.path.join(cwd, st.get("dst", os.path.basename(st["src"].rstrip("/"))))
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
                    shutil.copy2(src, dst)
                r["msg"] = f"配布資料から {st['src']} → {os.path.relpath(dst, work)}"
            elif t == "wait":
                time.sleep(st.get("sec", 1))
            elif t == "cd":
                cwd = os.path.join(cwd, st["path"])
        except Exception as e:
            r.update(ok=False, msg=f"{type(e).__name__}: {e}")
        log(f"[{'OK' if r['ok'] else 'NG'}] {i:02d} {t}: {r['msg'][:300]}")
        if not r["ok"] and r.get("out"):
            log("      " + r["out"][-1500:].replace("\n", "\n      "))
        results.append(r)
    for _, p, _lf in bg:
        _stop(p, os_name)
    if n_warn:
        log(f"WARN（表示される内容の違い）: {n_warn} か所。資料の「表示される内容」を、受講者と同じ環境の対話のシェルで取った出力に合わせる（ガイド01 §28 の 7）")
    return results


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="c")
    a = sub.add_parser("extract"); a.add_argument("html")
    b = sub.add_parser("run"); b.add_argument("steps"); b.add_argument("--os", default="mac"); b.add_argument("--work", required=True)
    b.add_argument("--env-file"); b.add_argument("--out"); b.add_argument("--dist", help="配布資料（展開した zip）のフォルダ")
    b.add_argument("--no-out-check", action="store_true", help="「表示される内容」と実際の出力の照合（WARN）をしない")
    x = ap.parse_args()
    if x.c == "extract":
        json.dump(extract(x.html), sys.stdout, ensure_ascii=False, indent=1)
    elif x.c == "run":
        res = run(json.load(open(x.steps, encoding="utf-8")), x.os, os.path.abspath(x.work), x.env_file, dist=x.dist, out_check=not x.no_out_check)
        ng = [r for r in res if not r["ok"]]
        nw = [r for r in res if r.get("warn")]
        print(f"結果: {len(res)} 手順中 NG {len(ng)}" + (f"・WARN {len(nw)}（表示される内容の違い）" if nw else ""))
        if x.out:
            json.dump(res, open(x.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        sys.exit(1 if ng else 0)
