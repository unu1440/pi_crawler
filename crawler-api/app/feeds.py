"""RSS 다운로드와 해석.

담당자 개인 이름인 author 값은 읽지도 저장하지도 않음.
"""

import html
import re
import ssl
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import struct_time
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

import certifi
import feedparser
import httpx

USER_AGENT = "pi_crawler/0.1 (+https://github.com/unu1440/pi_crawler)"
REQUEST_TIMEOUT_SECONDS = 15
MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 응답 크기 제한 5MB
MAX_GOOGLE_NEWS_ITEMS = 20            # 키워드당 최대 건수
MAX_EXCERPT_LENGTH = 300
MAX_URL_LENGTH = 2048

KOREA_TIMEZONE = timezone(timedelta(hours=9))
GACHON_DATE_FORMAT = "%Y.%m.%d %H:%M:%S"  # 가천대 RSS 시각 형식, 한국 시간

# 공지 본문의 연락처 저장 방지
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_PATTERN = re.compile(r"(?<!\d)(?:0\d{1,2}|\d{3,4})[-.)\s]\s?\d{3,4}[-.\s]\d{4}(?!\d)")
CONTACT_MASK = "[연락처 생략]"

# 학교 서버의 구형 암호 방식 지원, 인증서 검증은 유지
TLS_CONTEXT = ssl.create_default_context(cafile=certifi.where())
TLS_CONTEXT.set_ciphers("DEFAULT")


@dataclass(frozen=True)
class FeedEntry:
    """저장할 글 한 건."""

    title: str
    url: str
    publisher: str | None
    excerpt: str | None
    published_at: datetime | None


def google_news_url(keyword: str) -> str:
    """키워드 검색 주소 생성. URL 인코딩으로 주소 구조 변경 방지."""
    return f"https://news.google.com/rss/search?q={quote(keyword)}&hl=ko&gl=KR&ceid=KR:ko"


def fetch_feed(url: str) -> bytes:
    """RSS 다운로드. 크기 제한 초과 시 중단."""
    received = bytearray()

    with httpx.stream(
        "GET",
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT_SECONDS,
        follow_redirects=True,
        verify=TLS_CONTEXT,
    ) as response:
        response.raise_for_status()

        for chunk in response.iter_bytes():
            received.extend(chunk)
            if len(received) > MAX_RESPONSE_BYTES:
                raise ValueError("응답이 허용 크기를 넘었습니다.")

    return bytes(received)


def is_http_url(url: str) -> bool:
    """http, https 주소만 허용."""
    if len(url) > MAX_URL_LENGTH:
        return False

    try:
        parts = urlsplit(url)
    except ValueError:
        return False

    return parts.scheme in ("http", "https") and bool(parts.netloc)


def remove_layout_query(url: str) -> str:
    """주소의 layout 값 제거. 같은 글의 중복 저장 방지."""
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query) if key != "layout"]
    return urlunsplit(parts._replace(query=urlencode(query)))


def clean_text(value: str | None, max_length: int) -> str | None:
    """태그, HTML 엔티티, 겹친 공백 제거."""
    if not value:
        return None

    without_tags = re.sub(r"<[^>]+>", " ", value)
    text = re.sub(r"\s+", " ", html.unescape(without_tags)).strip()
    return text[:max_length] or None


def mask_contacts(text: str | None) -> str | None:
    """이메일과 전화번호 가림."""
    if not text:
        return text

    return PHONE_PATTERN.sub(CONTACT_MASK, EMAIL_PATTERN.sub(CONTACT_MASK, text))


def parse_feed_items(content: bytes) -> list:
    """응답을 RSS로 해석. RSS가 아니면 실패 처리."""
    parsed = feedparser.parse(content)

    if not parsed.version:
        raise ValueError("RSS 형식이 아닌 응답입니다.")

    return parsed.entries


def remove_publisher_suffix(title: str, publisher: str | None) -> str:
    """구글 뉴스 제목 끝의 ' - 언론사' 제거."""
    suffix = f" - {publisher}" if publisher else ""
    return title[: -len(suffix)].rstrip() if suffix and title.endswith(suffix) else title


def parse_gachon_date(value: str | None) -> datetime | None:
    """가천대 RSS의 한국 시간을 UTC로 변환."""
    if not value:
        return None

    try:
        local_time = datetime.strptime(value.strip(), GACHON_DATE_FORMAT)
    except ValueError:
        return None

    return local_time.replace(tzinfo=KOREA_TIMEZONE).astimezone(timezone.utc).replace(tzinfo=None)


def parsed_time_to_utc(value: struct_time | None) -> datetime | None:
    """feedparser 시각을 datetime으로 변환."""
    return datetime(*value[:6]) if value else None


def parse_rss_entries(content: bytes, source_name: str) -> list[FeedEntry]:
    """고정 주소 RSS 해석."""
    entries = []

    for item in parse_feed_items(content):
        link = item.get("link", "").strip()
        title = clean_text(item.get("title"), 500)

        if not title or not is_http_url(link):
            continue

        entries.append(
            FeedEntry(
                title=title,
                url=remove_layout_query(link),
                publisher=source_name,
                excerpt=mask_contacts(clean_text(item.get("description"), MAX_EXCERPT_LENGTH)),
                published_at=parse_gachon_date(item.get("published"))
                or parsed_time_to_utc(item.get("published_parsed")),
            )
        )

    return entries


def parse_google_news_entries(content: bytes) -> list[FeedEntry]:
    """구글 뉴스 검색 결과 해석. 요약 칸은 링크 목록이라 제외."""
    entries = []

    for item in parse_feed_items(content)[:MAX_GOOGLE_NEWS_ITEMS]:
        url = item.get("link", "").strip()
        publisher = clean_text(item.get("source", {}).get("title"), 120)
        title = clean_text(item.get("title"), 500)

        if not title or not is_http_url(url):
            continue

        entries.append(
            FeedEntry(
                title=remove_publisher_suffix(title, publisher),
                url=url,
                publisher=publisher,
                excerpt=None,
                published_at=parsed_time_to_utc(item.get("published_parsed")),
            )
        )

    return entries