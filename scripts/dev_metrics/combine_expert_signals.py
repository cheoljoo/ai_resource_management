"""전문가 파인더 — 5개 데이터 소스 결합 리포트 (spec.md 완료조건 4번)

git(사내+GitHub) + Gerrit + Jira + Confluence 신호를 한 사람 단위로 모아
"회사 안의 어떤 사람이 전문가인가"에 답하는 최종 리포트를 만든다.

원칙(spec.md "거버넌스 확장" 절 준수):
  * git 모듈 랭킹이 "이 모듈은 누구에게 물어볼까"의 1차 답이다(라우팅 목적).
  * Gerrit/Jira/Confluence는 그 사람의 전반적인 활동 폭을 보여주는 보조 신호일
    뿐, 개인별 성과 비교·순위 매기기에는 쓰지 않는다(수치를 정렬해서 보여주는
    것은 "누가 최근 무엇을 많이 다뤘는지" 라우팅 참고용).

사용 예:
    python3 combine_expert_signals.py \
        --repo ~/code/pvs_crawler --repo ~/code/pvs_trender ... \
        --gerrit-json gerrit_signal_na_lamp_2026-09-11.json \
        --github-json /tmp/github_signal.json \
        --jira-confluence-json jira_confluence_signal_2026-09-11.json \
        --since-days 1500
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict

from expert_finder import collect_module_contributor_ea


def load_json(path: str | None) -> dict:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", action="append", required=True)
    parser.add_argument("--since-days", type=int, default=1500)
    parser.add_argument("--module-depth", type=int, default=2)
    parser.add_argument("--gerrit-json", default=None)
    parser.add_argument("--github-json", default=None)
    parser.add_argument("--jira-confluence-json", default=None)
    parser.add_argument("--top-modules", type=int, default=3)
    parser.add_argument("--top-people", type=int, default=25)
    args = parser.parse_args()

    git_data = collect_module_contributor_ea(args.repo, args.since_days, args.module_depth)
    git_ea_total: Counter[str] = Counter()
    for counter in git_data.values():
        git_ea_total.update(counter)

    gerrit = load_json(args.gerrit_json)
    gerrit_person_total = gerrit.get("person_total", {})

    github = load_json(args.github_json)
    github_commits = github.get("commits", {})

    jc = load_json(args.jira_confluence_json).get("people", {})

    all_people = set(git_ea_total) | set(gerrit_person_total) | set(github_commits) | set(jc)

    print(f"# 전문가 파인더 — 5개 소스 결합 리포트 (git+Gerrit+Jira+Confluence+GitHub)")
    print(f"# 이번 조회에서 확인된 고유 인원: {len(all_people)}명\n")

    print("## 1차 답: 저장소별 모듈 전문가 랭킹 (git EA, 라우팅 목적)")
    for (repo, module), counter in git_data.items():
        repo_name = repo.rstrip("/").rsplit("/", 1)[-1]
        top = counter.most_common(args.top_modules)
        if not top:
            continue
        print(f"  [{repo_name}] {module}: " + ", ".join(f"{p}({n})" for p, n in top))

    print("\n## 2차 답: 인원별 종합 활동 프로파일 (git EA / Gerrit changes / Jira 티켓 / Confluence 문서 / GitHub 커밋)")
    print(f"{'person':40s} {'git_EA':>8s} {'gerrit':>8s} {'jira':>8s} {'confluence':>10s} {'github':>8s}")
    rows = []
    for person in all_people:
        git_v = git_ea_total.get(person, 0)
        gerrit_v = gerrit_person_total.get(person, 0)
        jira_v = jc.get(person, {}).get("jira_total_180d", "-")
        conf_v = jc.get(person, {}).get("confluence_hits", "-")
        github_v = github_commits.get(person, 0)
        rows.append((person, git_v, gerrit_v, jira_v, conf_v, github_v))

    rows.sort(key=lambda r: r[1], reverse=True)
    for person, git_v, gerrit_v, jira_v, conf_v, github_v in rows[: args.top_people]:
        print(f"{person:40s} {git_v:8d} {gerrit_v:8d} {str(jira_v):>8s} {str(conf_v):>10s} {github_v:8d}")

    print(
        "\n# 주의: 이 표는 라우팅(누구에게 물어볼지) 참고용이며, 개인별 성과 비교·평가로 전용하지 않는다"
        "(developer_evaluation_metrics.md 1.3절 Goodhart's Law, spec.md 거버넌스 확장 절 참고)."
    )


if __name__ == "__main__":
    main()
