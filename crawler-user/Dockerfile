# 회원 인증 PHP 서버
FROM php:8.1-apache-bookworm

# Redis 확장
RUN pecl install redis \
    && docker-php-ext-enable redis

# MySQL 확장
RUN docker-php-ext-install pdo_mysql

# 오류 내용 외부 노출 차단
RUN echo 'display_errors=Off' > "$PHP_INI_DIR/conf.d/crawler-user.ini"

# 소스 복사
COPY ./src /var/www/html