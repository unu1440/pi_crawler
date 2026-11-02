"""소스별 글 수집과 DB 저장.

소스 하나가 실패해도 나머지는 계속 실행.
실행 결과는 collect_runs에 기록.
"""

import hashlib
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.db import open_connection
from app.feeds import (
    FeedEntry,
    fetch_feed,
    google_news_url,
    parse_google_news_entries,
    parse_rss_entries,
)

REQUEST_DELAY_SECONDS = 1  # 대상 사이트 부담 방지


@dataclass
class CollectResult:
    """수집 결과 요약."""

    fetched: int = 0
    inserted: int = 0
    runs: int = 0
    failed_sources: list[str] = field(default_factory=list)


def utc_now() -> datetime:
    """현재 UTC 시각."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def load_top_category_ids(cursor) -> dict[int, int]:
    """분류 번호를 대주제 번호로 바꾸는 표."""
    cursor.execute("SELECT id, parent_id FROM categories")
    return {row["id"]: row["parent_id"] or row["id"] for row in cursor.fetchall()}


def load_keywords(cursor, user_id: int | None) -> list[dict]:
    """수집 대상 키워드 조회. user_id가 없으면 전체 사용자."""
    if user_id is None:
        cursor.execute("SELECT id, keyword, category_id FROM keywords")
    else:
        cursor.execute(
            "SELECT id, keyword, category_id FROM keywords WHERE user_id = %s",
            (user_id,),
        )
    return cursor.fetchall()


def save_entry(cursor, source_id: int, category_id: int | None, entry: FeedEntry) -> tuple[int, bool]:
    """글 저장 후 (글 번호, 새 글 여부) 반환.

    같은 주소는 새로 넣지 않음.
    중복 처리된 글이면 원본 번호 반환.
    """
    cursor.execute(
        """
        INSERT INTO articles
            (source_id, category_id, url, url_hash, title, publisher, excerpt, published_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)
        """,
        (
            source_id,
            category_id,
            entry.url,
            hashlib.sha256(entry.url.encode("utf-8")).hexdigest(),
            entry.title,
            entry.publisher,
            entry.excerpt,
            entry.published_at,
        ),
    )
    article_id = cursor.lastrowid
    is_new = cursor.rowcount == 1

    if not is_new:
        cursor.execute("SELECT COALESCE(duplicate_of, id) AS target_id FROM articles WHERE id = %s", (article_id,))
        article_id = cursor.fetchone()["target_id"]

    return article_id, is_new


def link_keywords(cursor, article_id: int, keyword_ids: list[int]) -> None:
    """글과 키워드 연결. 이미 있으면 무시."""
    if keyword_ids:
        cursor.executemany(
            "INSERT IGNORE INTO article_keywords (article_id, keyword_id) VALUES (%s, %s)",
            [(article_id, keyword_id) for keyword_id in keyword_ids],
        )


def record_run(cursor, source_id, keyword_id, trigger_type, started_at, fetched, inserted, error) -> None:
    """수집 실행 결과 기록."""
    cursor.execute(
        """
        INSERT INTO collect_runs
            (source_id, keyword_id, trigger_type, status, fetched_count, inserted_count,
             error_message, started_at, finished_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            source_id,
            keyword_id,
            trigger_type,
            "failed" if error else "success",
            fetched,
            inserted,
            error[:500] if error else None,
            started_at,
            utc_now(),
        ),
    )


def matching_keyword_ids(entry: FeedEntry, keywords: list[dict]) -> list[int]:
    """제목이나 소개에 포함된 키워드 찾기. 대소문자 무시."""
    text = f"{entry.title} {entry.excerpt or ''}".casefold()
    return [item["id"] for item in keywords if item["keyword"].casefold() in text]


def collect_rss_source(cursor, source: dict, keywords: list[dict], top_ids: dict[int, int]) -> tuple[int, int]:
    """고정 주소 RSS 수집. 같은 대주제 키워드와 비교해 연결."""
    entries = parse_rss_entries(fetch_feed(source["url"]), source["name"])
    source_top_id = top_ids[source["category_id"]]
    same_tree_keywords = [item for item in keywords if top_ids[item["category_id"]] == source_top_id]
    inserted = 0

    for entry in entries:
        article_id, is_new = save_entry(cursor, source["id"], source["category_id"], entry)
        inserted += int(is_new)
        link_keywords(cursor, article_id, matching_keyword_ids(entry, same_tree_keywords))

    return len(entries), inserted


def collect_google_news(cursor, source: dict, keyword: str, category_id: int, keyword_ids: list[int]) -> tuple[int, int]:
    """키워드 하나로 구글 뉴스 검색 후 저장."""
    entries = parse_google_news_entries(fetch_feed(google_news_url(keyword)))
    inserted = 0

    for entry in entries:
        article_id, is_new = save_entry(cursor, source["id"], category_id, entry)
        inserted += int(is_new)
        link_keywords(cursor, article_id, keyword_ids)

    return len(entries), inserted


def run_collection(user_id: int | None, trigger_type: str) -> CollectResult:
    """수집 실행. 단계마다 커밋해 앞선 결과 보존."""
    result = CollectResult()

    with open_connection() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id, name, kind, url, category_id FROM sources WHERE enabled = 1")
        sources = cursor.fetchall()
        keywords = load_keywords(cursor, user_id)
        top_ids = load_top_category_ids(cursor)

        # 전용 소스가 있는 대주제는 뉴스 검색 제외. 다른 학교 기사 혼입 방지
        dedicated_top_ids = {
            top_ids[source["category_id"]]
            for source in sources
            if source["kind"] == "rss" and source["category_id"] is not None
        }

        # 같은 키워드는 외부 요청 1회로 통합
        keyword_groups = defaultdict(list)
        for item in keywords:
            if top_ids[item["category_id"]] not in dedicated_top_ids:
                keyword_groups[(item["keyword"], item["category_id"])].append(item["id"])

        def run_step(source, keyword_id, collect):
            """수집 한 단계 실행과 기록."""
            started_at = utc_now()
            fetched = inserted = 0
            error_message = None

            try:
                fetched, inserted = collect()
            except Exception as error:
                connection.rollback()
                error_message = f"{type(error).__name__}: {error}"
                if source["name"] not in result.failed_sources:
                    result.failed_sources.append(source["name"])

            record_run(cursor, source["id"], keyword_id, trigger_type, started_at, fetched, inserted, error_message)
            connection.commit()

            result.fetched += fetched
            result.inserted += inserted
            result.runs += 1
            time.sleep(REQUEST_DELAY_SECONDS)

        for source in sources:
            if source["kind"] == "rss":
                run_step(source, None, lambda: collect_rss_source(cursor, source, keywords, top_ids))
                continue

            for (keyword, category_id), keyword_ids in keyword_groups.items():
                run_step(
                    source,
                    keyword_ids[0],
                    lambda: collect_google_news(cursor, source, keyword, category_id, keyword_ids),
                )

    return result