"""전문가 파인더 — 5개 데이터 소스 결합 리포트 (spec.md 완료조건 4번)

git(사내+GitHub) + Gerrit + Jira + Confluence + GitLab(mod.lge.com/hub) 신호를
한 사람 단위로 모아 "회사 안의 어떤 사람이 전문가인가"에 답하는 최종 리포트를
만든다.

**식별자 정규화(2026-09-11 사용자 지시)**: 같은 사람이 시스템마다 다른 도메인
(`@lge.com` vs `@lgepartner.com` 등)이나 아이디만(도메인 없이) 나타날 수 있다.
`@` 앞부분(local-part)만을 정규화된 사람 식별자로 사용해 모든 소스를 합친다.

**기간(2026-09-11 사용자 지시)**: 모든 소스를 180일 이내로 통일한다. git EA,
Gerrit changes, GitLab 커밋/MR/이슈, Jira 티켓 총건수, Confluence 문서 활동
모두 최근 180일 창을 기준으로 카운트한다.

원칙(spec.md "거버넌스 확장" 절 준수):
  * git 모듈 랭킹이 "이 모듈은 누구에게 물어볼까"의 1차 답이다(라우팅 목적).
  * Gerrit/Jira/Confluence/GitLab은 그 사람의 전반적인 활동 폭을 보여주는
    보조 신호일 뿐, 개인별 성과 비교·순위 매기기에는 쓰지 않는다.

사용 예:
    python3 combine_expert_signals.py \
        --repo ~/code/pvs_crawler --repo ~/code/pvs_trender ... \
        --since-days 180 \
        --gerrit-json gerrit_signal_na_lamp_2026-09-11.json \
        --gitlab-json gitlab_signal_2026-09-11.json \
        --jira-confluence-json jira_confluence_signal_2026-09-11.json
"""
from __future__ import annotations

import argparse
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", action="append", required=True)
    parser.add_argument("--since-days", type=int, default=180)
    parser.add_argument("--module-depth", type=int, default=2)
    parser.add_argument("--gerrit-json", default=None)
    parser.add_argument("--gitlab-json", default=None)
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

    gitlab = load_json(args.gitlab_json)
    gitlab_commits = normalize_counter(gitlab.get("commits", {}))
    gitlab_mrs = normalize_counter(gitlab.get("mrs", {}))

    jc_raw = load_json(args.jira_confluence_json).get("people", {})
    jira_total: Counter[str] = Counter()
    confluence_total: Counter[str] = Counter()
    for key, data in jc_raw.items():
        person = normalize_person(key)
        jira_total[person] += data.get("jira_total_180d", 0)
        confluence_total[person] += data.get("confluence_hits", 0)

    all_people = (
        set(git_ea_total) | set(gerrit_person_total) | set(gitlab_commits)
        | set(gitlab_mrs) | set(jira_total) | set(confluence_total)
    )

    print(f"# 전문가 파인더 — 5개 소스 결합 리포트 (git+Gerrit+Jira+Confluence+GitLab, 최근 {args.since_days}일)")
    print(f"# 식별자는 '@' 앞부분(local-part)으로 정규화하여 도메인 차이(@lge.com vs @lgepartner.com 등)를 통합")
    print(f"# 이번 조회에서 확인된 고유 인원: {len(all_people)}명\n")

    print("## 1차 답: 저장소별 모듈 전문가 랭킹 (git EA, 라우팅 목적)")
    for (repo, module), counter in git_data_norm.items():
        repo_name = repo.rstrip("/").rsplit("/", 1)[-1]
        top = counter.most_common(args.top_modules)
        if not top:
            continue
        print(f"  [{repo_name}] {module}: " + ", ".join(f"{p}({n})" for p, n in top))

    print(f"\n## 2차 답: 인원별 종합 활동 프로파일 (최근 {args.since_days}일, git EA / Gerrit / GitLab 커밋 / GitLab MR / Jira / Confluence)")
    print(f"{'person':25s} {'git_EA':>8s} {'gerrit':>8s} {'gitlab_c':>9s} {'gitlab_mr':>10s} {'jira':>8s} {'confluence':>10s}")
    rows = []
    for person in all_people:
        rows.append((
            person,
            git_ea_total.get(person, 0),
            gerrit_person_total.get(person, 0),
            gitlab_commits.get(person, 0),
            gitlab_mrs.get(person, 0),
            jira_total.get(person, 0),
            confluence_total.get(person, 0),
        ))

    rows.sort(key=lambda r: r[1], reverse=True)
    for person, git_v, gerrit_v, gc_v, gmr_v, jira_v, conf_v in rows[: args.top_people]:
        print(f"{person:25s} {git_v:8d} {gerrit_v:8d} {gc_v:9d} {gmr_v:10d} {jira_v:8d} {conf_v:10d}")

    print(
        "\n# 주의: 이 표는 라우팅(누구에게 물어볼지) 참고용이며, 개인별 성과 비교·평가로 전용하지 않는다"
        "(developer_evaluation_metrics.md 1.3절 Goodhart's Law, spec.md 거버넌스 확장 절 참고)."
    )


if __name__ == "__main__":
    main()
