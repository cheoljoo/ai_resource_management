# /// script
# requires-python = ">=3.11"
# dependencies = ["requests>=2.32,<3"]
# ///
"""agent-action-items.md A2: 크로스팀 리뷰 참여 지표 (Gerrit)

developer_evaluation_metrics.md 6.4절("본인이 주로 커밋하는 프로젝트가 아닌 Change에 리뷰어로
참여한 비율")을 실제로 계산한다. 원 티켓(AGILEDEV-1118)의 "얼마나 많은 분야에서 활동하는가"를
협업(리뷰) 관점에서 보강.

`gerrit_signal.py`의 `fetch_recent_changes()`가 이미 반환하는 change별 `project`/`owner`/`votes`
필드만으로 계산 가능 — 별도 API 호출이 추가로 필요 없다(코멘트 본문도 다루지 않는다).

정의:
  - "본인이 오너인 프로젝트 집합" = 이 사람이 owner로 등록된 change가 있는 프로젝트들.
  - "리뷰한 프로젝트 집합" = 이 사람이 0이 아닌 투표(vote)를 남긴 change가 있는 프로젝트들
    (본인이 owner인 change는 제외 — 자기 자신에 대한 투표는 리뷰가 아니므로).
  - 교차 참여 비율 = (리뷰한 프로젝트 중 본인 오너 프로젝트에 없는 것의 수) / (리뷰한 전체 프로젝트 수).

사용 예:
    python3 cross_team_review_signal.py --server na --since-days 60 --limit-per-server 50
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections import defaultdict

from gerrit_signal import GerritClient, _load_gerrit_conf, fetch_recent_changes, person_key


def collect_cross_team_review(servers: list[str], since_days: int, limit_per_server: int) -> dict:
    conf = _load_gerrit_conf()
    owned_projects: dict[str, set[str]] = defaultdict(set)
    reviewed_projects: dict[str, set[str]] = defaultdict(set)
    server_errors: dict[str, str] = {}

    for name in servers:
        entry = conf.get(name)
        if not entry:
            server_errors[name] = "설정 없음(~/code/ccr/global_variables.py)"
            continue
        try:
            client = GerritClient(name, entry)
            changes, _truncated = fetch_recent_changes(client, since_days, limit_per_server)
        except Exception as exc:  # noqa: BLE001 - POC: 서버별 실패를 한 줄로 보고
            server_errors[name] = str(exc)
            continue

        for change in changes:
            project_key = f"{name}::{change.get('project', '(unknown)')}"
            owner = person_key(change.get("owner"), name)
            if owner:
                owned_projects[owner].add(project_key)
            for vote in change.get("votes", []):
                if vote.get("value") == 0:
                    continue
                reviewer = person_key(vote.get("reviewer"), name)
                if reviewer and reviewer != owner:
                    reviewed_projects[reviewer].add(project_key)

    people = sorted(set(owned_projects) | set(reviewed_projects))
    per_person = {}
    for p in people:
        owned = owned_projects.get(p, set())
        reviewed = reviewed_projects.get(p, set())
        cross = reviewed - owned
        per_person[p] = {
            "owned_project_count": len(owned),
            "reviewed_project_count": len(reviewed),
            "cross_team_reviewed_count": len(cross),
            "cross_team_ratio": (len(cross) / len(reviewed)) if reviewed else None,
            "cross_team_projects": sorted(cross),
        }

    return {
        "since_days": since_days,
        "limit_per_server": limit_per_server,
        "servers_requested": servers,
        "server_errors": server_errors,
        "per_person": per_person,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--server", action="append", dest="servers", help="조회할 Gerrit 서버 이름(복수 가능, 미지정 시 설정 파일의 전체 서버)")
    parser.add_argument("--since-days", type=int, default=60, help="조회 기간(기본 60일)")
    parser.add_argument("--limit-per-server", type=int, default=50, help="서버당 조회할 Change 수(기본 50)")
    parser.add_argument("--min-reviewed", type=int, default=1, help="결과에 표시할 최소 리뷰 프로젝트 수(기본 1)")
    args = parser.parse_args()

    servers = args.servers or list(_load_gerrit_conf())
    result = collect_cross_team_review(servers, args.since_days, args.limit_per_server)

    print(f"# 크로스팀 리뷰 참여 지표 POC — 최근 {result['since_days']}일, 서버당 최대 {result['limit_per_server']}건 Change")
    print(f"조회 대상 서버: {', '.join(result['servers_requested'])}\n")

    if result["server_errors"]:
        print("⚠️ 일부 조회 실패:")
        for k, v in result["server_errors"].items():
            print(f"  - {k}: {v}")
        print()

    rows = [
        (p, info) for p, info in result["per_person"].items()
        if info["reviewed_project_count"] >= args.min_reviewed
    ]
    if not rows:
        print("리뷰 활동이 있는 사람이 없습니다(조회 기간/Change 수를 늘려보세요).")
        return 0

    rows.sort(key=lambda kv: -(kv[1]["cross_team_ratio"] or 0))
    print(f"{'person':<32} {'owned_proj':>10} {'reviewed_proj':>13} {'cross_team':>10} {'ratio':>7}")
    for p, info in rows:
        ratio = f"{info['cross_team_ratio']:.0%}" if info["cross_team_ratio"] is not None else "N/A"
        print(f"{p:<32} {info['owned_project_count']:>10} {info['reviewed_project_count']:>13} {info['cross_team_reviewed_count']:>10} {ratio:>7}")

    top = rows[0]
    if top[1]["cross_team_projects"]:
        print(f"\n예시 — {top[0]}가 크로스팀으로 리뷰한 프로젝트: {', '.join(top[1]['cross_team_projects'][:5])}")

    print(
        "\n※ 이 지표는 '여러 분야에서 활동'하는 사람을 찾는 참고 신호이며, 교차 리뷰가 적다고 해서"
        " 역량이 낮은 것은 아닙니다(전담 영역이 명확한 역할일 수 있음) — 단독 평가 기준으로 쓰지 마세요"
        " (developer_evaluation_metrics.md 1.3절 Goodhart's Law)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
