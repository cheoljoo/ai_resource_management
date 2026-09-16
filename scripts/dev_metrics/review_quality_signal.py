# /// script
# requires-python = ">=3.11"
# dependencies = ["requests>=2.32,<3"]
# ///
"""agent-action-items.md A1: 코드 리뷰 코멘트 품질 (메타데이터 전용 부분)

developer_evaluation_metrics.md 3.1절의 "의미있는 리뷰" 4대 신호 중, **코멘트 본문 없이 메타데이터
만으로 계산 가능한 두 가지**를 구현한다:

  1. 라인 단위 코멘트 비율 — 코멘트가 특정 파일의 특정 라인(`line`/`range`)을 짚었는지, 아니면
     Change 전체에 대한 단발성 코멘트인지.
  2. 후속 스레드(reply) 존재율 — `in_reply_to` 필드로 답글이 오갔는지.

**"구체성"(코드 스니펫 인용, 대안 제시 여부)은 이번 POC에 포함하지 않는다** — `gerrit_signal.py`의
`fetch_comments()`가 애초에 코멘트 본문(`message`)을 가져오지 않도록 설계되어 있다(7장 "소스코드
원본 유출 완전 차단" 원칙). 본문 없이는 구체성을 판별할 수 없으므로, 이 신호를 채우려면 별도로
본문을 가져오는 결정(및 그 결정의 거버넌스 검토)이 선행되어야 한다 — agent-action-items.md A1의
"위임 시 추가로 정의해야 할 것"에 이 발견을 반영해야 한다.

`gerrit_signal.py`의 `GerritClient`/`fetch_recent_changes`/`fetch_comments`를 그대로 재사용해
인증·조회 로직을 중복 구현하지 않는다.

사용 예:
    python3 review_quality_signal.py --server na --since-days 30 --limit-per-server 5
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections import Counter, defaultdict

from gerrit_signal import GerritClient, _load_gerrit_conf, fetch_comments, fetch_recent_changes


def collect_review_quality(servers: list[str], since_days: int, limit_per_server: int) -> dict:
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
                comments = fetch_comments(client, change["_number"])
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

    return {
        "since_days": since_days,
        "limit_per_server": limit_per_server,
        "servers_requested": servers,
        "server_errors": server_errors,
        "total": dict(total),
        "per_reviewer": {k: dict(v) for k, v in per_reviewer.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--server", action="append", dest="servers", help="조회할 Gerrit 서버 이름(복수 가능, 미지정 시 설정 파일의 전체 서버)")
    parser.add_argument("--since-days", type=int, default=30, help="조회 기간(기본 30일 — POC이므로 짧게)")
    parser.add_argument("--limit-per-server", type=int, default=5, help="서버당 조회할 Change 수(기본 5 — POC이므로 작게)")
    args = parser.parse_args()

    servers = args.servers or list(_load_gerrit_conf())
    result = collect_review_quality(servers, args.since_days, args.limit_per_server)

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

    if result["per_reviewer"]:
        print("\n리뷰어별 (코멘트 수 / 라인단위 비율 / 스레드 비율):")
        for reviewer, c in sorted(result["per_reviewer"].items(), key=lambda kv: -kv[1]["comments"]):
            n = c["comments"]
            print(f"  {reviewer:<30} {n:>4}건  라인단위 {c['line_level']/n:.0%}  스레드 {c['replies']/n:.0%}")

    print(
        "\n※ '구체성'(코드 인용/대안 제시 여부)은 이번 POC에 없습니다 — gerrit_signal.py가 코멘트 본문을"
        " 애초에 수집하지 않도록 설계되어 있기 때문입니다(7장 원칙). 본문 기반 분석이 필요하면 이 설계를"
        " 바꿀지부터 별도로 결정해야 합니다."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
