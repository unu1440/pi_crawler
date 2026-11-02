# MySQL 8.0 기반
FROM mysql:8.0

# 초기 테이블 구조 복사 (빈 볼륨에서 최초 1회 실행)
COPY ./init /docker-entrypoint-initdb.d/