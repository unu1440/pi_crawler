# crawler-user: 회원과 인증을 맡는 PHP 서버
FROM php:8.1-apache-bookworm

# phpredis 확장 설치: PHP에서 Redis에 접속하기 위해 필요
RUN pecl install redis \
    && docker-php-ext-enable redis

# 소스를 이미지에 복사해 다른 PC에서도 바인드 마운트 없이 실행되게 함
COPY ./src /var/www/html
