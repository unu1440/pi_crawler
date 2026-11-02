# crawler-api: 수집과 결과 조회를 맡는 FastAPI 서버
FROM python:3.12-slim

WORKDIR /srv

# requirements.txt를 먼저 복사해 소스만 바뀌었을 때 설치를 다시 하지 않게 함
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스를 이미지에 복사해 다른 PC에서도 바인드 마운트 없이 실행되게 함
COPY ./app ./app

# 서버를 root가 아닌 일반 사용자로 실행
RUN useradd --create-home appuser
USER appuser

# 0.0.0.0: 컨테이너 밖의 요청도 받도록 모든 주소에서 대기
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
