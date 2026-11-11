"""ひとこと掲示板（hitokoto）。短いメッセージを書き込むと、一覧に表示される。"""

import logging
import os
from datetime import datetime, timedelta, timezone

# 設定は環境変数で受け取る
DB_HOST = os.environ["DB_HOST"]  # データベースのコンテナの名前（使わないときは none）
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import DateTime, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

logger = logging.getLogger("uvicorn.error")
JST = timezone(timedelta(hours=9), "JST")
templates = Jinja2Templates(directory="templates")
USE_DB = DB_HOST != "none"


class Base(DeclarativeBase):
    pass


class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(140))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(JST)
    )


memory_posts: list[Post] = []  # DB を使わないときの置き場（コンテナを消すと消える）
engine = None
if USE_DB:
    engine = create_engine(
        f"postgresql+psycopg://postgres:{DB_PASSWORD}@{DB_HOST}:5432/postgres",
        pool_pre_ping=True,
    )


def prepare_table() -> None:
    Base.metadata.create_all(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not USE_DB:
        logger.info("データベースを使わずに動きます（DB_HOST=none）")
    else:
        try:
            prepare_table()
            logger.info("データベース %s につながりました", DB_HOST)
        except Exception:
            logger.exception("データベース %s につながりません", DB_HOST)
    yield


app = FastAPI(title="ひとこと掲示板", lifespan=lifespan)


def load_posts() -> list[Post]:
    if not USE_DB:
        return list(reversed(memory_posts))
    prepare_table()
    with Session(engine) as session:
        return list(session.scalars(select(Post).order_by(Post.id.desc()).limit(50)))


def save_post(text: str) -> None:
    if not USE_DB:
        memory_posts.append(
            Post(id=len(memory_posts) + 1, text=text, created_at=datetime.now(JST))
        )
        return
    prepare_table()
    with Session(engine) as session:
        session.add(Post(text=text))
        session.commit()


@app.get("/")
def index(request: Request):
    try:
        posts = load_posts()
    except Exception:
        logger.exception("データベース %s につながりません", DB_HOST)
        return templates.TemplateResponse(
            request, "error.html", {"db_host": DB_HOST}, status_code=500
        )
    return templates.TemplateResponse(
        request,
        "index.html",
        {"posts": posts, "use_db": USE_DB, "db_host": DB_HOST, "jst": JST},
    )


@app.post("/")
def post(text: str = Form(..., min_length=1, max_length=140)):
    save_post(text.strip() or "（空白）")
    return RedirectResponse("/", status_code=303)


@app.get("/health")
def health():
    return {"status": "ok"}
