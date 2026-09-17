# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.32,<3", "python-dotenv>=1,<2"]
# ///
"""agent-action-items.md A2(Jira 쪽)·A3: Jira 교차 프로젝트 참여 + Confluence 양방향 협업 신호

`jira_confluence_signal.py`의 `AtlassianClient`/`load_settings`/`query_literal`/`load_roster`를
재사용해 인증 로직을 중복하지 않는다(공유 스크립트 자체는 테스트가 있어 건드리지 않고 별도 스크립트로
분리). 두 가지를 추가로 계산한다:

  1. Jira 교차 프로젝트 참여 (A2 Jira 쪽): 사람별 담당/보고 이슈를 프로젝트별로 집계해, 가장 활동이
     많은 "주 프로젝트" 대비 그 외 프로젝트 비율을 계산 — Gerrit 쪽(cross_team_review_signal.py)과
     같은 개념을 Jira에 적용.
  2. Confluence 양방향 협업 신호 (A3): 본인이 작성한 코멘트 수와, 그 중 **본인이 만들지 않은 페이지**에
     남긴 코멘트 수를 구분한다(작성자 대조는 페이지 이력 조회 1건 추가 필요 — 사람당 코멘트 수를
     `--max-comments-per-person`으로 제한해 API 호출량을 통제한다).

Confluence "정확한 건수"에 대한 참고: `jira_confluence_signal.py`의 `confluence_count()`는 이미
`_links.next`를 끝까지 따라가는 완전 페이지네이션을 구현하고 있다 — developer_evaluation_metrics.md
8.6절의 "페이지당 상한 50이라 근사치" 한계는 (이 스크립트가 쓰는) REST 직접 수집 경로에는 해당하지
않는다. 그 한계는 별도 세션에서 `mcp-atlassian`의 `confluence_search` 도구를 직접 호출했을 때의
얘기였다 — 도구별로 페이지네이션 처리가 다르다는 걸 이번에 확인했다.

사용 예:
    python3 jira_confluence_expansion.py --since-days 180 --max-jira-issues 100 --max-comments-per-person 20
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from jira_confluence_signal import (
    DEFAULT_ENV,
    DEFAULT_ROSTER,
    AtlassianClient,
    CollectionError,
    load_roster,
    load_settings,
    query_literal,
)


def jira_project_breakdown(client: AtlassianClient, jira_user: str, days: int, max_issues: int) -> dict:
    jql = f"(assignee = {query_literal(jira_user)} OR reporter = {query_literal(jira_user)}) AND updated >= -{days}d"
    projects: Counter[str] = Counter()
    start = 0
    fetched = 0
    while fetched < max_issues:
        page_size = min(100, max_issues - fetched)
        data = client.get("/rest/api/2/search", {
            "jql": jql, "startAt": start, "maxResults": page_size, "fields": "project",
        })
        issues = data.get("issues")
        if not isinstance(issues, list):
            raise CollectionError("JIRA: 응답에 유효한 issues가 없습니다.")
        if not issues:
            break
        for issue in issues:
            key = ((issue.get("fields") or {}).get("project") or {}).get("key") or "(unknown)"
            projects[key] += 1
        fetched += len(issues)
        start += len(issues)
        total = data.get("total", 0)
        if start >= total:
            break
    if not projects:
        return {"total_fetched": 0, "primary_project": None, "cross_project_ratio": None, "projects": {}}
    primary, primary_count = projects.most_common(1)[0]
    total = sum(projects.values())
    return {
        "total_fetched": total,
        "primary_project": primary,
        "cross_project_ratio": (total - primary_count) / total,
        "projects": dict(projects),
    }


def confluence_comment_signal(client: AtlassianClient, conf_user: str, days: int, max_comments: int) -> dict:
    cql = f'type=comment and creator = {query_literal(conf_user)} and created >= now("-{days}d")'
    data = client.get("/rest/api/content/search", {
        "cql": cql, "start": 0, "limit": max_comments, "expand": "ancestors",
    })
    results = data.get("results")
    if not isinstance(results, list):
        raise CollectionError("CONFLUENCE: 응답에 유효한 results가 없습니다.")
    total_comments = len(results)
    on_others_page = 0
    checked = 0
    for comment in results:
        ancestors = comment.get("ancestors") or []
        if not ancestors:
            continue
        page_id = ancestors[-1].get("id")
        if not page_id:
            continue
        checked += 1
        page_data = client.get(f"/rest/api/content/{page_id}", {"expand": "history"})
        page_creator = ((page_data.get("history") or {}).get("createdBy") or {}).get("username")
        if page_creator and page_creator != conf_user:
            on_others_page += 1
    return {
        "comments_sampled": total_comments,
        "ancestor_checked": checked,
        "comments_on_others_pages": on_others_page,
        "on_others_ratio": (on_others_page / checked) if checked else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV, help="PAT 등 설정을 읽을 .env 경로")
    parser.add_argument("--roster", type=Path, default=DEFAULT_ROSTER, help="명단 JSON 경로")
    parser.add_argument("--person", action="append", help="명단 대신 특정 인물만 조회(복수 가능)")
    parser.add_argument("--since-days", type=int, default=180, help="조회 기간(기본 180일)")
    parser.add_argument("--max-jira-issues", type=int, default=100, help="사람당 조회할 최대 Jira 이슈 수")
    parser.add_argument("--max-comments-per-person", type=int, default=20, help="사람당 조회할 최대 Confluence 코멘트 수")
    args = parser.parse_args()

    settings = load_settings(args.env_file)
    roster = load_roster(args.roster, args.person)

    jira = AtlassianClient("JIRA", settings)
    confluence = AtlassianClient("CONFLUENCE", settings)

    print(f"# Jira 교차 프로젝트 + Confluence 양방향 협업 신호 POC (최근 {args.since_days}일)\n")
    print(f"{'person':<28} {'jira_issues':>11} {'primary_proj':>14} {'cross_ratio':>11}   {'conf_on_others':>14} {'conf_ratio':>10}")

    for person, identities in roster.items():
        try:
            jr = jira_project_breakdown(jira, identities["jira_user"], args.since_days, args.max_jira_issues)
        except CollectionError as exc:
            print(f"{person:<28} JIRA ERROR: {exc}")
            continue
        try:
            cr = confluence_comment_signal(confluence, identities["confluence_user"], args.since_days, args.max_comments_per_person)
        except CollectionError as exc:
            print(f"{person:<28} CONFLUENCE ERROR: {exc}")
            continue

        jratio = f"{jr['cross_project_ratio']:.0%}" if jr["cross_project_ratio"] is not None else "N/A"
        cratio = f"{cr['on_others_ratio']:.0%}" if cr["on_others_ratio"] is not None else "N/A"
        print(
            f"{person:<28} {jr['total_fetched']:>11} {str(jr['primary_project']):>14} {jratio:>11}   "
            f"{cr['comments_on_others_pages']:>14} {cratio:>10}"
        )

    print(
        "\n※ Jira cross_ratio: 조회된 이슈 중 '주 프로젝트'가 아닌 프로젝트 비율(표본은 --max-jira-issues로 제한)."
        "\n※ Confluence conf_ratio: 표본 코멘트 중 본인이 만들지 않은 페이지에 남긴 비율(표본은 --max-comments-per-person으로 제한, 페이지당 API 호출 1건 추가)."
        "\n※ 두 수치 모두 '여러 분야에서 활동'하는지 보는 라우팅/협업 참고 신호이며, 낮다고 역량 부족을 뜻하지 않습니다"
        " (developer_evaluation_metrics.md 1.3절 Goodhart's Law)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
