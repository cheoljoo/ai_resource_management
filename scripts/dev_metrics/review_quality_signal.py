# /// script
# requires-python = ">=3.11"
# dependencies = ["requests>=2.32,<3"]
# ///
"""agent-action-items.md A1: 코드 리뷰 코멘트 품질

developer_evaluation_metrics.md 3.1절의 "의미있는 리뷰" 4대 신호 중 세 가지를 구현한다:

  1. 라인 단위 코멘트 비율 — 코멘트가 특정 파일의 특정 라인(`line`/`range`)을 짚었는지, 아니면
     Change 전체에 대한 단발성 코멘트인지. (메타데이터만으로 계산, 기본 동작)
  2. 후속 스레드(reply) 존재율 — `in_reply_to` 필드로 답글이 오갔는지. (메타데이터만으로 계산, 기본 동작)
  3. **구체성(코드 인용/파일 경로·함수명 언급 여부)** — `--include-body` 플래그를 켰을 때만 계산된다.

**구체성은 기본적으로 계산하지 않는다.** `gerrit_signal.py`의 `fetch_comments()`는 2026-09-15
사용자 승인으로 코멘트 본문(`message`)을 기본적으로 가져오지 않도록 설계되어 있다(7장 "소스코드
원본 유출 완전 차단" 원칙). 2026-09-21 사용자 승인으로, A1 구체성 판별 목적에 한해
`gerrit_signal.py --include-comment-body`(opt-in)를 함께 켜는 경우에만 본문을 받아와 규칙 기반
휴리스틱(코드 인용 백틱, 파일 경로 패턴, 함수/변수명 패턴 포함 여부)으로 "구체적" 여부를 근사한다.
판정 결과(bool)만 집계하고, 원문 코멘트는 어떤 옵션으로도 출력하지 않는다(7장 원칙 — 판정 결과만 집계).

`gerrit_signal.py`의 `GerritClient`/`fetch_recent_changes`/`fetch_comments`를 그대로 재사용해
인증·조회 로직을 중복 구현하지 않는다.

사용 예:
    python3 review_quality_signal.py --server na --since-days 30 --limit-per-server 5
    python3 review_quality_signal.py --server na --since-days 30 --limit-per-server 5 --include-body
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from collections import Counter, defaultdict

from gerrit_signal import GerritClient, _load_gerrit_conf, fetch_comments, fetch_recent_changes

# "구체성" 휴리스틱: 코드 인용(백틱/들여쓰기 블록), 파일 경로, 함수/변수명 스타일 언급 중 하나라도
# 있으면 "구체적"으로 본다. 이 판별이 필요로 하는 것은 판정 결과(bool)뿐이고, 원문은 어디에도 출력하지 않는다.
_SPECIFICITY_PATTERNS = [
    re.compile(r"`[^`]+`"),  # 코드 인용 (백틱)
    re.compile(r"\b[\w./-]+\.[a-zA-Z]{1,10}\b"),  # 파일 경로/파일명 (예: foo/bar.py)
    re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\([^)]*\)"),  # 함수 호출 패턴 (예: fetch_comments(...))
    re.compile(r"\b[a-z][a-zA-Z0-9]*_[a-zA-Z0-9_]+\b"),  # snake_case 식별자
]


def is_specific_comment(message: str | None) -> bool:
    if not message:
        return False
    return any(p.search(message) for p in _SPECIFICITY_PATTERNS)


def collect_review_quality(servers: list[str], since_days: int, limit_per_server: int, include_body: bool = False) -> dict:
    conf = _load_gerrit_conf()
    per_reviewer: dict[str, Counter] = defaultdict(Counter)
    total = Counter()
    server_errors: dict[str, str] = {}

    for name in servers:
        entry = conf.get(name)
        if not entry:
            server_errors[name] = "설정 없음(~/code/ccr/global_variables.py)"
            continue
        try:
            client = GerritClient(name, entry)
            changes, _truncated = fetch_recent_changes(client, since_days, limit_per_server)
        except Exception as exc:  # noqa: BLE001 - POC: 서버별 실패를 한 줄로 보고하고 계속 진행
            server_errors[name] = str(exc)
            continue

        for change in changes:
            try:
                comments = fetch_comments(client, change["_number"], include_body=include_body)
            except Exception as exc:  # noqa: BLE001
                server_errors[f"{name}#{change.get('_number')}"] = str(exc)
                continue
            if not comments:
                continue
            for c in comments:
                reviewer = c.get("author", {}).get("email") or c.get("author", {}).get("name") or "(unknown)"
                is_line_level = bool(c.get("line") or c.get("range"))
                is_reply = bool(c.get("in_reply_to"))
                total["comments"] += 1
                total["line_level"] += int(is_line_level)
                total["replies"] += int(is_reply)
                per_reviewer[reviewer]["comments"] += 1
                per_reviewer[reviewer]["line_level"] += int(is_line_level)
                per_reviewer[reviewer]["replies"] += int(is_reply)
                if include_body:
                    is_specific = is_specific_comment(c.get("message"))
                    total["specific"] += int(is_specific)
                    per_reviewer[reviewer]["specific"] += int(is_specific)

    return {
        "since_days": since_days,
        "limit_per_server": limit_per_server,
        "servers_requested": servers,
        "include_body": include_body,
        "server_errors": server_errors,
        "total": dict(total),
        "per_reviewer": {k: dict(v) for k, v in per_reviewer.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--server", action="append", dest="servers", help="조회할 Gerrit 서버 이름(복수 가능, 미지정 시 설정 파일의 전체 서버)")
    parser.add_argument("--since-days", type=int, default=30, help="조회 기간(기본 30일 — POC이므로 짧게)")
    parser.add_argument("--limit-per-server", type=int, default=5, help="서버당 조회할 Change 수(기본 5 — POC이므로 작게)")
    parser.add_argument("--include-body", action="store_true",
                         help="구체성(코드 인용/파일경로/함수명 언급) 판별을 위해 댓글 본문을 받아온다 "
                              "(2026-09-21 사용자 승인, 기본 꺼짐 — 판정 결과만 집계하고 원문은 출력 안 함)")
    args = parser.parse_args()

    servers = args.servers or list(_load_gerrit_conf())
    result = collect_review_quality(servers, args.since_days, args.limit_per_server, args.include_body)

    print(f"# 리뷰 코멘트 품질(메타데이터 전용) POC — 최근 {result['since_days']}일, 서버당 최대 {result['limit_per_server']}건 Change")
    print(f"조회 대상 서버: {', '.join(result['servers_requested'])}\n")

    if result["server_errors"]:
        print("⚠️ 일부 조회 실패:")
        for k, v in result["server_errors"].items():
            print(f"  - {k}: {v}")
        print()

    t = result["total"]
    if not t.get("comments"):
        print("수집된 공개 코멘트가 없습니다(조회 기간/서버/Change 수를 늘려보세요).")
        return 0

    print(f"전체 코멘트: {t['comments']}")
    print(f"  라인 단위(특정 파일/라인을 짚은) 코멘트: {t['line_level']} ({t['line_level']/t['comments']:.1%})")
    print(f"  후속 스레드(답글)로 이어진 코멘트: {t['replies']} ({t['replies']/t['comments']:.1%})")
    if result["include_body"]:
        print(f"  구체적(코드 인용/파일경로/함수명 언급) 코멘트: {t.get('specific', 0)} ({t.get('specific', 0)/t['comments']:.1%})")

    if result["per_reviewer"]:
        header = "코멘트 수 / 라인단위 비율 / 스레드 비율" + (" / 구체성 비율" if result["include_body"] else "")
        print(f"\n리뷰어별 ({header}):")
        for reviewer, c in sorted(result["per_reviewer"].items(), key=lambda kv: -kv[1]["comments"]):
            n = c["comments"]
            line = f"  {reviewer:<30} {n:>4}건  라인단위 {c['line_level']/n:.0%}  스레드 {c['replies']/n:.0%}"
            if result["include_body"]:
                line += f"  구체성 {c.get('specific', 0)/n:.0%}"
            print(line)

    if not result["include_body"]:
        print(
            "\n※ '구체성'(코드 인용/파일경로/함수명 언급 여부)은 --include-body 없이는 계산하지 않습니다"
            " — gerrit_signal.py가 기본적으로 코멘트 본문을 수집하지 않도록 설계되어 있기 때문입니다"
            "(7장 원칙, 2026-09-15 결정). --include-body를 켜면 2026-09-21 승인 범위 내에서 판정 결과만"
            " 집계합니다(원문은 노출하지 않음)."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
