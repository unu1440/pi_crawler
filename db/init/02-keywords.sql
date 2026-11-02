SET NAMES utf8mb4;

-- 대주제와 소주제. parent_id가 NULL이면 대주제
CREATE TABLE categories (
    id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
    parent_id  INT UNSIGNED NULL,
    name       VARCHAR(50)  NOT NULL,
    sort_order INT          NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uq_categories_parent_name (parent_id, name),
    CONSTRAINT fk_categories_parent FOREIGN KEY (parent_id) REFERENCES categories (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 사용자별 관심 키워드
CREATE TABLE keywords (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id     BIGINT UNSIGNED NOT NULL,
    category_id INT UNSIGNED    NOT NULL,
    keyword     VARCHAR(50)     NOT NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_keywords_user_category_keyword (user_id, category_id, keyword),
    CONSTRAINT fk_keywords_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_keywords_category FOREIGN KEY (category_id) REFERENCES categories (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 대주제
INSERT INTO categories (id, parent_id, name, sort_order) VALUES
    (1, NULL, '대학', 1),
    (2, NULL, '대학원', 2),
    (3, NULL, 'AI 국제정세', 3);

-- 소주제
INSERT INTO categories (id, parent_id, name, sort_order) VALUES
    (10, 1, '본교(가천대)', 1),
    (20, 2, '입학·모집', 1),
    (21, 2, '연구실 소식', 2),
    (22, 2, '장학·지원', 3),
    (23, 2, '관심 연구자', 4),
    (29, 2, '기타', 9),
    (30, 3, '미국', 1),
    (31, 3, '중국', 2),
    (32, 3, '유럽연합', 3),
    (33, 3, '일본', 4),
    (34, 3, '한국', 5),
    (39, 3, '기타', 9);