#!/usr/bin/env bash
# PHP에서 로그인한 세션을 FastAPI에서도 읽는지 검증한다.
# 사용법: ./scripts/verify-session.sh

set -euo pipefail
cd "$(dirname "$0")/.."

# 테스트 계정을 읽음 (값은 화면에 출력하지 않음)
source secrets/dev.env

USER_URL=http://localhost:8013
API_URL=http://localhost:8012

# 쿠키 저장 파일: 끝나면 자동 삭제
COOKIE_JAR=$(mktemp)
trap 'rm -f "$COOKIE_JAR"' EXIT

# 설명, 기대 상태 코드, curl 인자를 받아 결과를 비교한다.
check() {
    local name=$1 expected=$2
    shift 2
    local actual
    actual=$(curl -s -o /dev/null -w '%{http_code}' "$@")
    if [ "$actual" = "$expected" ]; then
        echo "PASS  $name ($actual)"
    else
        echo "FAIL  $name (기대 $expected, 실제 $actual)"
        exit 1
    fi
}

check '비로그인 FastAPI 거부' 401 "$API_URL/session"
check '틀린 비밀번호 거부' 401 -d "username=$TEST_USERNAME" -d 'password=wrong' "$USER_URL/login.php"
check '위조 쿠키 거부' 401 -H "Cookie: CRAWLERSESSID=$(printf 'a%.0s' {1..64})" "$API_URL/session"
check 'PHP 로그인' 200 -c "$COOKIE_JAR" -d "username=$TEST_USERNAME" --data-urlencode "password=$TEST_PASSWORD" "$USER_URL/login.php"
check 'PHP 세션 확인' 200 -b "$COOKIE_JAR" "$USER_URL/me.php"
check 'FastAPI 세션 공유' 200 -b "$COOKIE_JAR" "$API_URL/session"

echo "응답: $(curl -s -b "$COOKIE_JAR" "$API_URL/session")"

check '로그아웃' 200 -X POST -b "$COOKIE_JAR" "$USER_URL/logout.php"
check '로그아웃 후 FastAPI 거부' 401 -b "$COOKIE_JAR" "$API_URL/session"
