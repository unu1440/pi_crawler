-- 한글 깨짐 방지
SET NAMES utf8mb4;

-- 회원 정보
CREATE TABLE users (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    username      VARCHAR(30)  NOT NULL,
    password_hash VARCHAR(255) NOT NULL,  -- 비밀번호 해시
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_username (username)  -- 아이디 중복 방지
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;