"""PHP 서버가 만든 세션 확인."""

import json
import os
import re
from dataclasses import dataclass

import redis
from fastapi import Cookie, HTTPException

# crawler-user와 같은 쿠키 이름
SESSION_COOKIE = "CRAWLERSESSID"

# 세션 ID 형식: 64자리 소문자 16진수
SESSION_ID_PATTERN = re.compile(r"[0-9a-f]{64}")

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "crawler-redis"),
    port=6379,
    decode_responses=True,  # bytes 대신 문자열로 조회
    socket_timeout=2,
)


@dataclass(frozen=True)
class CurrentUser:
    """로그인 사용자."""

    user_id: int
    username: str


def load_session(session_id: str | None) -> CurrentUser | None:
    """세션 ID로 사용자 조회. 없으면 None."""
    if session_id is None or not SESSION_ID_PATTERN.fullmatch(session_id):
        return None

    session_json = redis_client.get(f"session:{session_id}")
    if session_json is None:
        return None

    try:
        session = json.loads(session_json)
        return CurrentUser(int(session["user_id"]), str(session["username"]))
    except (ValueError, KeyError, TypeError):
        # 손상된 세션은 비로그인 처리
        return None


def require_user(
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> CurrentUser:
    """로그인 필수 라우트용 의존성. 세션이 없으면 401."""
    user = load_session(session_id)

    if user is None:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    return user