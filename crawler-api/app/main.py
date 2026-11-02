"""수집과 결과 조회 API."""

import pymysql
from fastapi import Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from app.auth import CurrentUser, redis_client, require_user
from app.db import open_connection

app = FastAPI(title="pi_crawler API")

MAX_KEYWORDS_PER_USER = 20   # 외부 요청량 제한
MYSQL_DUPLICATE_ENTRY = 1062 # UNIQUE 제약 위반 코드


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