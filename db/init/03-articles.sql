SET NAMES utf8mb4;

-- 수집 소스. rss는 고정 주소, google_news는 키워드 검색
CREATE TABLE sources (
    id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
    name        VARCHAR(100) NOT NULL,
    kind        ENUM('rss', 'google_news') NOT NULL,
    url         VARCHAR(500) NULL,
    category_id INT UNSIGNED NULL,
    enabled     TINYINT(1)   NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    UNIQUE KEY uq_sources_name (name),
    CONSTRAINT fk_sources_category FOREIGN KEY (category_id) REFERENCES categories (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 수집한 글. status가 파이프라인 단계
CREATE TABLE articles (
    id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    source_id        INT UNSIGNED    NOT NULL,
    category_id      INT UNSIGNED    NULL,
    url              VARCHAR(2048)   NOT NULL,
    url_hash         CHAR(64)        NOT NULL,  -- 같은 주소 중복 저장 방지
    title            VARCHAR(500)    NOT NULL,
    normalized_title VARCHAR(500)    NULL,      -- 제목 비교용
    publisher        VARCHAR(120)    NULL,
    excerpt          VARCHAR(500)    NULL,      -- 짧은 소개, 전문 저장 안 함
    summary          TEXT            NULL,      -- AI 요약
    published_at     DATETIME        NULL,      -- UTC
    status           ENUM('collected', 'analyzed', 'uploaded', 'duplicate', 'failed')
                                     NOT NULL DEFAULT 'collected',
    duplicate_of     BIGINT UNSIGNED NULL,
    retry_count      INT             NOT NULL DEFAULT 0,
    error_message    VARCHAR(500)    NULL,
    collected_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    analyzed_at      DATETIME        NULL,
    uploaded_at      DATETIME        NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_articles_url_hash (url_hash),
    KEY idx_articles_status (status),
    KEY idx_articles_published (published_at),
    KEY idx_articles_normalized (normalized_title(120)),
    CONSTRAINT fk_articles_source FOREIGN KEY (source_id) REFERENCES sources (id),
    CONSTRAINT fk_articles_category FOREIGN KEY (category_id) REFERENCES categories (id),
    CONSTRAINT fk_articles_duplicate FOREIGN KEY (duplicate_of) REFERENCES articles (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 글과 키워드 연결. 사용자별 결과의 기준
CREATE TABLE article_keywords (
    article_id BIGINT UNSIGNED NOT NULL,
    keyword_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (article_id, keyword_id),
    CONSTRAINT fk_article_keywords_article FOREIGN KEY (article_id) REFERENCES articles (id) ON DELETE CASCADE,
    CONSTRAINT fk_article_keywords_keyword FOREIGN KEY (keyword_id) REFERENCES keywords (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 수집 실행 기록. 수집 성공률 측정용
CREATE TABLE collect_runs (
    id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    source_id      INT UNSIGNED    NOT NULL,
    keyword_id     BIGINT UNSIGNED NULL,
    trigger_type   ENUM('manual', 'schedule') NOT NULL,
    status         ENUM('success', 'failed')  NOT NULL,
    fetched_count  INT             NOT NULL DEFAULT 0,
    inserted_count INT             NOT NULL DEFAULT 0,
    error_message  VARCHAR(500)    NULL,
    started_at     DATETIME        NOT NULL,
    finished_at    DATETIME        NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_collect_runs_source FOREIGN KEY (source_id) REFERENCES sources (id),
    CONSTRAINT fk_collect_runs_keyword FOREIGN KEY (keyword_id) REFERENCES keywords (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 수집 소스 등록
INSERT INTO sources (id, name, kind, url, category_id) VALUES
    (1, '가천대 학사공지', 'rss', 'https://www.gachon.ac.kr/bbs/kor/475/rssList.do?row=50', 10),
    (2, '구글 뉴스', 'google_news', NULL, NULL);