# 수집과 조회 FastAPI 서버
FROM python:3.12-slim

WORKDIR /srv

# 소스만 바뀌면 설치 단계 재사용
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY ./app ./app

# root가 아닌 일반 사용자로 실행
RUN useradd --create-home appuser
USER appuser

# 컨테이너 외부 요청 수신
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]