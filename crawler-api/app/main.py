"""crawler-api: 수집과 결과 조회를 맡는 FastAPI 서버.

지금은 PHP 서버가 만든 세션을 읽을 수 있는지 검증하는 API만 제공한다.
세션 형식은 crawler-user/src/session.php와 같아야 한다.
"""

import json
import os
import re

import redis
from fastapi import Cookie, FastAPI, HTTPException

# 브라우저 쿠키 이름 (crawler-user와 같은 값을 사용해야 함)
SESSION_COOKIE = "CRAWLERSESSID"

# 임의의 문자열이 Redis 키로 쓰이지 않도록 64자리 16진수만 허용
SESSION_ID_PATTERN = re.compile(r"^[0-9a-f]{64}$")

app = FastAPI(title="pi_crawler API")

# decode_responses=True: Redis 값을 bytes가 아닌 문자열로 받음
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "crawler-redis"),
    port=6379,
    decode_responses=True,
    socket_timeout=2,
)


def get_session(session_id: str | None) -> dict | None:
    """쿠키의 세션 ID로 Redis를 조회한다. 없으면 None을 돌려준다."""
    if session_id is None or not SESSION_ID_PATTERN.fullmatch(session_id):
        return None

    data = redis_client.get(f"session:{session_id}")
    if data is None:
        return None

    return json.loads(data)


@app.get("/session")
def read_session(
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> dict:
    """PHP에서 로그인한 사용자를 FastAPI에서 확인한다."""
    session = get_session(session_id)

    if session is None:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    return {"server": "crawler-api", "username": session["username"]}
