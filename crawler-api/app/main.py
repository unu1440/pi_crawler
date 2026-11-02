"""수집과 결과 조회 API."""
from datetime import datetime

import pymysql
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field

from app.auth import CurrentUser, redis_client, require_user
from app.collector import run_collection
from app.db import open_connection

app = FastAPI(title="pi_crawler API")

MAX_KEYWORDS_PER_USER = 20   # 외부 요청량 제한
MYSQL_DUPLICATE_ENTRY = 1062 # UNIQUE 제약 위반 코드
COLLECT_LOCK_SECONDS = 60  # 사용자별 수집 간격
KEYWORD_SEPARATOR = "\x1f" # 키워드 묶음 구분 문자

# 로그인 사용자의 글로 제한하는 공통 FROM
USER_ARTICLES_FROM = """
    FROM articles a
    JOIN article_keywords ak ON ak.article_id = a.id
    JOIN keywords k ON k.id = ak.keyword_id AND k.user_id = %s
    LEFT JOIN categories c ON c.id = a.category_id
    LEFT JOIN categories p ON p.id = c.parent_id
"""

class KeywordCreate(BaseModel):
    """키워드 추가 요청."""

    keyword: str = Field(max_length=200)
    category_id: int


@app.get("/health")
def health() -> dict:
    """Redis, MySQL 연결 상태 확인."""
    try:
        redis_client.ping()
        with open_connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as error:
        raise HTTPException(status_code=503, detail="의존 서비스에 연결할 수 없습니다.") from error

    return {"status": "ok"}


@app.get("/session")
def read_session(user: CurrentUser = Depends(require_user)) -> dict:
    """PHP에서 로그인한 사용자 확인."""
    return {"server": "crawler-api", "user_id": user.user_id, "username": user.username}


@app.get("/categories")
def list_categories(user: CurrentUser = Depends(require_user)) -> list[dict]:
    """대주제와 소주제 트리 조회."""
    with open_connection() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id, parent_id, name FROM categories ORDER BY sort_order, id")
        rows = cursor.fetchall()

    tree = [{"id": row["id"], "name": row["name"], "children": []} for row in rows if row["parent_id"] is None]
    tree_by_id = {node["id"]: node for node in tree}

    for row in rows:
        if row["parent_id"] is not None:
            tree_by_id[row["parent_id"]]["children"].append({"id": row["id"], "name": row["name"]})

    return tree


@app.get("/keywords")
def list_keywords(user: CurrentUser = Depends(require_user)) -> list[dict]:
    """내 키워드 조회."""
    with open_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT k.id, k.keyword, k.category_id, c.name AS category_name
            FROM keywords k
            JOIN categories c ON c.id = k.category_id
            WHERE k.user_id = %s
            ORDER BY k.id
            """,
            (user.user_id,),
        )
        return cursor.fetchall()


@app.post("/keywords", status_code=201)
def add_keyword(body: KeywordCreate, user: CurrentUser = Depends(require_user)) -> dict:
    """키워드 추가."""
    keyword = body.keyword.strip()

    if not 1 <= len(keyword) <= 50:
        raise HTTPException(status_code=400, detail="키워드는 1~50자로 입력하세요.")

    with open_connection() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT name FROM categories WHERE id = %s", (body.category_id,))
        category = cursor.fetchone()
        if category is None:
            raise HTTPException(status_code=400, detail="없는 분류입니다.")

        # 동시 요청의 개수 제한 초과 방지
        cursor.execute("SELECT id FROM users WHERE id = %s FOR UPDATE", (user.user_id,))
        cursor.execute("SELECT COUNT(*) AS keyword_count FROM keywords WHERE user_id = %s", (user.user_id,))
        if cursor.fetchone()["keyword_count"] >= MAX_KEYWORDS_PER_USER:
            raise HTTPException(status_code=400, detail=f"키워드는 {MAX_KEYWORDS_PER_USER}개까지 등록할 수 있습니다.")

        try:
            cursor.execute(
                "INSERT INTO keywords (user_id, category_id, keyword) VALUES (%s, %s, %s)",
                (user.user_id, body.category_id, keyword),
            )
        except pymysql.err.IntegrityError as error:
            if error.args[0] == MYSQL_DUPLICATE_ENTRY:
                raise HTTPException(status_code=409, detail="이미 등록한 키워드입니다.") from error
            raise

        return {
            "id": cursor.lastrowid,
            "keyword": keyword,
            "category_id": body.category_id,
            "category_name": category["name"],
        }


@app.delete("/keywords/{keyword_id}", status_code=204)
def delete_keyword(keyword_id: int, user: CurrentUser = Depends(require_user)) -> Response:
    """내 키워드 삭제. 다른 사용자 키워드는 404."""
    with open_connection() as connection, connection.cursor() as cursor:
        cursor.execute("DELETE FROM keywords WHERE id = %s AND user_id = %s", (keyword_id, user.user_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="키워드를 찾을 수 없습니다.")

    return Response(status_code=204)

def to_iso(value: datetime | None) -> str | None:
    """UTC 시각을 ISO 8601 문자열로 변환."""
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def escape_like(text: str) -> str:
    """LIKE 와일드카드 문자 이스케이프."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@app.post("/collect")
def collect(user: CurrentUser = Depends(require_user)) -> dict:
    """내 키워드와 고정 소스 수집. 사용자별 1분에 1회."""
    if not redis_client.set(f"collect_lock:{user.user_id}", "1", nx=True, ex=COLLECT_LOCK_SECONDS):
        raise HTTPException(status_code=429, detail="잠시 후 다시 시도하세요.")

    result = run_collection(user.user_id, "manual")

    return {
        "fetched": result.fetched,
        "inserted": result.inserted,
        "failed_sources": result.failed_sources,
        "runs": result.runs,
    }


@app.get("/articles")
def list_articles(
    category_id: int | None = None,
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(require_user),
) -> dict:
    """내 키워드에 연결된 글 조회. 최신순."""
    conditions = ["a.status <> 'duplicate'"]
    parameters: list = [user.user_id]

    # 대주제 선택 시 소주제 포함
    if category_id is not None:
        conditions.append("(c.id = %s OR c.parent_id = %s)")
        parameters += [category_id, category_id]

    if q:
        conditions.append("a.title LIKE %s ESCAPE '\\\\'")
        parameters.append(f"%{escape_like(q)}%")

    where_clause = " AND ".join(conditions)

    with open_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"SELECT COUNT(DISTINCT a.id) AS total {USER_ARTICLES_FROM} WHERE {where_clause}",
            parameters,
        )
        total = cursor.fetchone()["total"]

        cursor.execute(
            f"""
            SELECT a.id, a.title, a.url, a.publisher, a.excerpt, a.summary,
                   a.published_at, a.collected_at, a.status,
                   c.id AS category_id, c.name AS category_name,
                   p.id AS parent_id, p.name AS parent_name,
                   GROUP_CONCAT(DISTINCT k.keyword SEPARATOR %s) AS keyword_list
            {USER_ARTICLES_FROM}
            WHERE {where_clause}
            GROUP BY a.id
            ORDER BY COALESCE(a.published_at, a.collected_at) DESC, a.id DESC
            LIMIT %s OFFSET %s
            """,
            [KEYWORD_SEPARATOR, *parameters, limit, offset],
        )
        rows = cursor.fetchall()

    items = [
        {
            "id": row["id"],
            "title": row["title"],
            "url": row["url"],
            "publisher": row["publisher"],
            "excerpt": row["excerpt"],
            "summary": row["summary"],
            "published_at": to_iso(row["published_at"]),
            "collected_at": to_iso(row["collected_at"]),
            "status": row["status"],
            "category": {"id": row["category_id"], "name": row["category_name"]} if row["category_id"] else None,
            "parent_category": {"id": row["parent_id"], "name": row["parent_name"]} if row["parent_id"] else None,
            "keywords": row["keyword_list"].split(KEYWORD_SEPARATOR) if row["keyword_list"] else [],
        }
        for row in rows
    ]

    return {"total": total, "items": items}