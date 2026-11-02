"""수집과 결과 조회 API."""

from fastapi import Depends, FastAPI, HTTPException

from app.auth import CurrentUser, redis_client, require_user

app = FastAPI(title="pi_crawler API")


@app.get("/health")
def health() -> dict:
    """Redis 연결 상태 확인."""
    try:
        redis_client.ping()
    except Exception as error:
        raise HTTPException(status_code=503, detail="Redis에 연결할 수 없습니다.") from error

    return {"status": "ok"}


@app.get("/session")
def read_session(user: CurrentUser = Depends(require_user)) -> dict:
    """PHP에서 로그인한 사용자 확인."""
    return {"server": "crawler-api", "user_id": user.user_id, "username": user.username}