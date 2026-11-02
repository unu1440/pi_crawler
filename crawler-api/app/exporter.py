"""수집 결과 CSV 생성."""

import csv
import io
from datetime import datetime, timedelta, timezone

KOREA_TIMEZONE = timezone(timedelta(hours=9))
CSV_HEADER = ["대주제", "소주제", "제목", "출처", "발행일", "링크", "요약", "수집일"]

# 엑셀 수식 실행 방지 대상 문자
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def protect_cell(value: str | None) -> str:
    """수식으로 해석될 수 있는 셀 앞에 작은따옴표 추가."""
    text = value or ""
    return f"'{text}" if text.startswith(FORMULA_PREFIXES) else text


def format_korea_time(value: datetime | None) -> str:
    """UTC 시각을 한국 시간 문자열로 변환."""
    if value is None:
        return ""
    return value.replace(tzinfo=timezone.utc).astimezone(KOREA_TIMEZONE).strftime("%Y-%m-%d %H:%M")


def build_csv(rows: list[dict]) -> str:
    """글 목록을 CSV로 변환. 엑셀 한글 깨짐 방지용 BOM 포함."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_HEADER)

    for row in rows:
        top_name = row["parent_name"] or row["category_name"]
        sub_name = row["category_name"] if row["parent_name"] else ""
        writer.writerow(
            [
                protect_cell(top_name),
                protect_cell(sub_name),
                protect_cell(row["title"]),
                protect_cell(row["publisher"]),
                format_korea_time(row["published_at"]),
                protect_cell(row["url"]),
                protect_cell(row["summary"] or row["excerpt"]),
                format_korea_time(row["collected_at"]),
            ]
        )

    return "\ufeff" + buffer.getvalue()