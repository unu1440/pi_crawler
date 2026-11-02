<?php
// MySQL 연결 공통 함수

function db_connection(): PDO
{
    // 요청 안에서 연결 재사용
    static $connection = null;

    if ($connection === null) {
        $dsn = sprintf(
            'mysql:host=%s;port=%s;dbname=%s;charset=utf8mb4',
            getenv('DB_HOST'),
            getenv('DB_PORT'),
            getenv('DB_NAME')
        );

        $connection = new PDO($dsn, getenv('DB_USER'), getenv('DB_PASSWORD'), [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,      // 오류 시 예외 발생
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC, // 연관 배열로 조회
            PDO::ATTR_EMULATE_PREPARES => false,              // 서버측 prepared statement
        ]);
    }

    return $connection;
}