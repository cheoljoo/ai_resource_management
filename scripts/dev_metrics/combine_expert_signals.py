"""전문가 파인더 — 데이터 소스 결합 리포트 (spec.md 완료조건 4번)

git(사내+GitHub) + Gerrit + Jira + Confluence + GitLab + 선택적 GitHub 신호를
한 사람 단위로 모아 "회사 안의 어떤 사람이 전문가인가"에 답하는 최종 리포트를
만든다.

**식별자 정규화(2026-09-11 사용자 지시)**: 같은 사람이 시스템마다 다른 도메인
(`@lge.com` vs `@lgepartner.com` 등)이나 아이디만(도메인 없이) 나타날 수 있다.
`@` 앞부분(local-part)만을 정규화된 사람 식별자로 사용해 모든 소스를 합친다.

**기간(2026-09-11 사용자 지시)**: 기본 조회 기간은 최근 180일이다. Gerrit은
updated 기준으로 선택한 changes의 owner/현재 투표/현재 MERGED 상태와,
개별 timestamp 기간으로 제한한 comments/messages/submits를 구분한다.

원칙(spec.md "거버넌스 확장" 절 준수):
  * git 모듈 랭킹이 "이 모듈은 누구에게 물어볼까"의 1차 답이다(라우팅 목적).
    * Gerrit/Jira/Confluence/GitLab/GitHub은 그 사람의 전반적인 활동 폭을 보여주는
    보조 신호일 뿐, 개인별 성과 비교·순위 매기기에는 쓰지 않는다.

사용 예:
    uv run combine_expert_signals.py \
        --repo ~/code/pvs_crawler --repo ~/code/pvs_trender ... \
        --since-days 180 \
        --gerrit-json gerrit_signal_na_lamp_2026-09-11.json \
        --gitlab-json gitlab_signal_2026-09-11.json \
        --github-json github_signal_2026-09-11.json \
        --jira-confluence-json jira_confluence_signal_2026-09-11.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import Counter

from expert_finder import collect_module_contributor_ea


def normalize_person(identifier: str) -> str:
    """'@' 앞부분만 소문자로 정규화 — 도메인이 달라도(@lge.com vs @lgepartner.com,
    또는 도메인 없는 GitLab username) 같은 사람으로 취급한다."""
    return identifier.split("@", 1)[0].lower()


def load_json(path: str | None) -> dict:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_counter(raw: dict) -> Counter[str]:
    counter: Counter[str] = Counter()
    for key, value in raw.items():
        counter[normalize_person(key)] += value
    return counter


MR_PR_FIELDS = {
    "selected_author": "request_author_total",
    "reviewed": "reviewer_total",
    "comments": "comment_total",
    "reviews": "review_total",
    "merged_owner": "merged_author_total",
    "merger": "merger_total",
}


def request_counters(data: dict, created_field: str) -> dict[str, Counter[str] | None]:
    """Absent/null maps are unknown; a present empty map is a collected zero."""
    fields = {"created": created_field, **MR_PR_FIELDS, "commits_legacy": "commits",
              "issues": "issues"}
    return {
        column: normalize_counter(data[field]) if isinstance(data.get(field), dict) else None
        for column, field in fields.items()
    }


def counter_value(counter: Counter[str] | None, person: str) -> str:
    return "N/A" if counter is None else str(counter.get(person, 0))


def collection_endpoint(data: dict) -> dt.datetime | None:
    """Compare equivalent ISO timestamps without mistaking Z for a different window."""
    value = data.get("collected_at")
    if not isinstance(value, str):
        return None
    try:
        timestamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return timestamp if timestamp.tzinfo is not None else None


def print_request_metadata(providers: dict[str, dict],
                           counters: dict[str, dict[str, Counter[str] | None]],
                           since_days: int) -> None:
    if "GitHub" not in providers:
        print("\n# GitHub PR metadata not collected: --github-json 미지정 (0 활동을 뜻하지 않음)")
    if not providers:
        return
    print("\n## MR/PR metadata (별도 보조 표; provider별 person 이름순, 점수 합산 없음)")
    windows = set()
    for provider, data in providers.items():
        days = data.get("window_days")
        endpoint = collection_endpoint(data)
        scope = data.get("projects" if provider == "GitLab" else "repos")
        scope_text = ", ".join(scope) if scope is not None else "N/A (legacy input)"
        print(f"# {provider} collected scope: {scope_text}; 범위 밖 활동은 미수집")
        print(f"# {provider}: schema_version={data.get('schema_version', 'legacy')}, "
              f"collected_at={data.get('collected_at', 'N/A')}, window_days={days if days is not None else 'N/A'}")
        if days is None or endpoint is None:
            print(f"# WARNING: {provider} metadata window unknown — window_days/collected_at 누락 또는 유효하지 않음")
        else:
            windows.add((days, endpoint))
        if days is not None and days != since_days:
            print(f"# WARNING: {provider} metadata window_days={days} differs from --since-days={since_days}; 재필터링하지 않음")
        missing = [column for column, counter in counters[provider].items()
                   if counter is None and column != "issues"]
        if missing:
            print(f"# WARNING: {provider} unavailable maps (N/A, 실제 0이 아님): {', '.join(missing)}")
        truncated = data.get("truncated_projects" if provider == "GitLab" else "truncated_repos", [])
        if truncated:
            print(f"# WARNING: {provider} cap reached — MR/PR metadata counts partial; "
                  f"legacy created/commits counters independent: {', '.join(truncated)}")
        if provider == "GitLab" and (
            any(item.get("feature") == "approvals" for item in data.get("unavailable", []))
            or any("approvals" in record and record["approvals"] is None
                   for record in data.get("requests", []))
        ):
            print("# WARNING: GitLab approvals unavailable — reviewer_total/review_total "
                  "(reviewed/reviews) are partial lower bounds, not complete zeros; "
                  "unsupported or not visible approval snapshots")
    if len(windows) > 1:
        print("# WARNING: GitLab/GitHub metadata windows differ (window_days and/or collected_at); "
              "각 입력의 수집 창을 유지하며 직접 비교·합산하지 않음")

    columns = ["created", *MR_PR_FIELDS, "commits_legacy"]
    print(f"{'provider':8s} {'person':25s} " + " ".join(f"{column:>15s}" for column in columns))
    for provider in providers:
        provider_counters = counters[provider]
        people = set().union(*(counter for counter in provider_counters.values() if counter is not None))
        for person in sorted(people):
            values = " ".join(f"{counter_value(provider_counters[column], person):>15s}" for column in columns)
            print(f"{provider:8s} {person:25s} {values}")

    print("\n# MR/PR 범례 (입력 JSON의 window_days 및 collected_at 기준; 원시 요청 내용은 출력하지 않음):")
    print("# created = GitLab mrs / GitHub prs legacy: created_at 창 안에 생성된 요청 수; selected_author와 별개")
    print("# selected_author = request_author_total: updated_at 창에 선택된 MR/PR의 author별 요청 수")
    print("# reviewed = reviewer_total: nonowner commenter/reviewer의 distinct MR/PR 수; owner 자신의 feedback 제외")
    print("# comments = comment_total: created_at 창 안의 GitLab nonsystem discussion notes / GitHub issue+review comments")
    print("# reviews = review_total: GitLab current approved_by approval snapshot (historical review events 아님); "
          "GitHub submitted_at 창 안의 non-PENDING review events")
    print("# GitHub review state는 과거 제출 이벤트의 현재 API 표현; DISMISSED는 원래 승인/반대 결정을 보존하지 않음")
    print("# merged_owner = merged_author_total: updated-selected 요청 중 현재 merged인 author의 수; merge 시각 창이 아님")
    print("# merger = merger_total: merged_at 창 안의 actual merged_by/merge_user; author와 별개이며 unknown merger를 author로 대체하지 않음")
    print("# commits_legacy = 기존 commits map (commit-date 창); git_EA와 합산하지 않음")
    print("# requested_reviewers는 참여 아님; users/bots 모두 포함 가능, human-only 보장 없음; N/A는 미수집, 0은 존재하는 map에서 집계 없음")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", action="append", required=True)
    parser.add_argument("--since-days", type=int, default=180)
    parser.add_argument("--module-depth", type=int, default=2)
    parser.add_argument("--gerrit-json", default=None)
    parser.add_argument("--gitlab-json", default=None)
    parser.add_argument("--github-json", default=None, help="Optional GitHub schema-2 PR metadata JSON")
    parser.add_argument("--jira-confluence-json", default=None)
    parser.add_argument("--top-modules", type=int, default=3)
    parser.add_argument("--top-people", type=int, default=25)
    args = parser.parse_args()

    git_data = collect_module_contributor_ea(args.repo, args.since_days, args.module_depth)
    git_ea_total: Counter[str] = Counter()
    git_data_norm: dict[tuple[str, str], Counter[str]] = {}
    for key, counter in git_data.items():
        norm_counter = normalize_counter(counter)
        git_data_norm[key] = norm_counter
        git_ea_total.update(norm_counter)

    gerrit = load_json(args.gerrit_json)
    gerrit_person_total = normalize_counter(gerrit.get("person_total", {}))
    gerrit_fields = {
        "g_review": "reviewer_total",
        "g_comment": "comment_total",
        "g_message": "message_total",
        "g_merged": "merged_owner_total",
        "g_submit": "submitter_total",
    }
    gerrit_counters = {
        column: normalize_counter(gerrit.get(field, {}))
        for column, field in gerrit_fields.items()
    }
    unavailable = [column for column, field in gerrit_fields.items() if field not in gerrit]

    gitlab = load_json(args.gitlab_json)
    github = load_json(args.github_json)
    mr_pr_counters = {
        "GitLab": request_counters(gitlab, "mrs"),
        "GitHub": request_counters(github, "prs"),
    }
    gitlab_commits = mr_pr_counters["GitLab"]["commits_legacy"]
    gitlab_mrs = mr_pr_counters["GitLab"]["created"]
    providers = {}
    if args.gitlab_json:
        providers["GitLab"] = gitlab
    if args.github_json:
        providers["GitHub"] = github

    jc_raw = load_json(args.jira_confluence_json).get("people", {})
    jira_total: Counter[str] = Counter()
    confluence_total: Counter[str] = Counter()
    for key, data in jc_raw.items():
        person = normalize_person(key)
        jira_total[person] += data.get("jira_total_180d", 0)
        confluence_total[person] += data.get("confluence_hits", 0)

    all_people = (
        set(git_ea_total) | set(gerrit_person_total) | set(jira_total) | set(confluence_total)
    )
    for counter in gerrit_counters.values():
        all_people.update(counter)
    for provider_counters in mr_pr_counters.values():
        for counter in provider_counters.values():
            if counter is not None:
                all_people.update(counter)

    sources = "git+Gerrit+Jira+Confluence+GitLab" + ("+GitHub" if args.github_json else "")
    print(f"# 전문가 파인더 — {6 if args.github_json else 5}개 소스 결합 리포트 ({sources}, 최근 {args.since_days}일)")
    print(f"# 식별자는 '@' 앞부분(local-part)으로 정규화하여 도메인 차이(@lge.com vs @lgepartner.com 등)를 통합")
    print(f"# 이번 조회에서 확인된 고유 인원: {len(all_people)}명\n")
    if unavailable:
        print(f"# WARNING: Gerrit 데이터 unavailable (N/A, 실제 0이 아님): {', '.join(unavailable)} — JSON에 해당 map 없음")
    if gerrit.get("truncated_servers"):
        print(f"# WARNING: Gerrit cap reached — 일부 change 누락 가능: {', '.join(gerrit['truncated_servers'])}")

    print("## 1차 답: 저장소별 모듈 전문가 랭킹 (git EA, 라우팅 목적)")
    for (repo, module), counter in git_data_norm.items():
        repo_name = repo.rstrip("/").rsplit("/", 1)[-1]
        top = counter.most_common(args.top_modules)
        if not top:
            continue
        print(f"  [{repo_name}] {module}: " + ", ".join(f"{p}({n})" for p, n in top))

    print(f"\n## 2차 답: 인원별 종합 활동 프로파일 (최근 {args.since_days}일, git EA / Gerrit / GitLab 커밋 / GitLab MR / Jira / Confluence)")
    gerrit_header = " ".join(f"{column:>9s}" for column in gerrit_fields)
    print(f"{'person':25s} {'git_EA':>8s} {'g_owner':>8s} {gerrit_header} {'gitlab_c':>9s} {'gitlab_mr':>10s} {'jira':>8s} {'confluence':>10s}")
    rows = []
    for person in all_people:
        rows.append((
            person,
            git_ea_total.get(person, 0),
            gerrit_person_total.get(person, 0),
            counter_value(gitlab_commits, person),
            counter_value(gitlab_mrs, person),
            jira_total.get(person, 0),
            confluence_total.get(person, 0),
        ))

    rows.sort(key=lambda r: (-r[1], r[0]))
    for person, git_v, gerrit_v, gc_v, gmr_v, jira_v, conf_v in rows[: args.top_people]:
        gerrit_values = " ".join(
            f"{('N/A' if column in unavailable else str(counter.get(person, 0))):>9s}"
            for column, counter in gerrit_counters.items()
        )
        print(f"{person:25s} {git_v:8d} {gerrit_v:8d} {gerrit_values} {gc_v:>9s} {gmr_v:>10s} {jira_v:8d} {conf_v:10d}")

    print_request_metadata(providers, mr_pr_counters, args.since_days)

    print("\n# Gerrit 범례 (입력 JSON의 수집 기간 기준):")
    print("# g_owner = 기존 gerrit/person_total: updated 조회 창에 선택된 owned changes 수 (리뷰 수가 아님)")
    print("# g_review = nonzero current votes 또는 최근 published comments/review messages가 있는 distinct reviewed changes; owner 자신의 feedback 제외")
    print("# 일반 투표·댓글·리뷰 메시지에도 자동화 계정이 포함될 수 있으며 사람 여부를 검증한 지표가 아님")
    print("# 투표는 current vote snapshot이며 historic vote event count가 아님; 과거 투표 이력/횟수를 뜻하지 않음")
    print("# g_comment = 최근 published comments 수 (inline/patch-set-level); g_message = 최근 change messages 수 (auto/system 포함), comments와 별개")
    print("# comments/messages/submits는 각각 timestamp가 since-days 창 안인 항목만 집계")
    print("# g_merged = updated 조회 창에 선택된 changes 중 현재 상태가 MERGED인 owner의 change 수; merge 시각 창이 아님")
    print("# g_submit = since-days 창 안에 submitted된 changes의 actual submitter별 수; owner와 별개")

    print(
        "\n# 주의: 이 표는 라우팅(누구에게 물어볼지) 참고용이며, 개인별 성과 비교·평가로 전용하지 않는다"
        "(developer_evaluation_metrics.md 1.3절 Goodhart's Law, spec.md 거버넌스 확장 절 참고)."
    )


if __name__ == "__main__":
    main()
