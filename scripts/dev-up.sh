#!/usr/bin/env bash
# 세션 공유 검증에 필요한 컨테이너를 순서대로 빌드하고 실행한다.
# 사용법: ./scripts/dev-up.sh

# 명령이 하나라도 실패하면 바로 중단
set -euo pipefail

# 어느 위치에서 실행해도 프로젝트 폴더를 기준으로 동작하게 함
cd "$(dirname "$0")/.."

ENV_FILE=secrets/dev.env
NETWORK=crawler-net

if [ ! -f "$ENV_FILE" ]; then
    echo "$ENV_FILE 파일이 없습니다. .env.example을 참고해 만들어 주세요." >&2
    exit 1
fi

# 이미지 빌드
docker build -t pi-crawler-user:dev ./crawler-user
docker build -t pi-crawler-api:dev ./crawler-api

# 네트워크가 없을 때만 생성
docker network inspect "$NETWORK" >/dev/null 2>&1 \
    || docker network create "$NETWORK"

# 이전에 실행한 프로젝트 컨테이너만 지우고 다시 생성
docker rm -f crawler-redis crawler-user crawler-api >/dev/null 2>&1 || true

# Redis는 내부 서버끼리만 쓰므로 포트를 외부에 열지 않음
docker run -d --name crawler-redis --net "$NETWORK" redis

docker run -d --name crawler-user --net "$NETWORK" \
    -p 8013:80 --env-file "$ENV_FILE" pi-crawler-user:dev

docker run -d --name crawler-api --net "$NETWORK" \
    -p 8012:8000 --env-file "$ENV_FILE" pi-crawler-api:dev
