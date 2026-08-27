"""1.3 변경 실패율 (Change Failure Rate) 신호 탐지 - 부분 자동화

로컬 git 이력만으로 감지 가능한 신호를 모은다:
  * `git revert`로 생성된 revert 커밋 (커밋 메시지가 "Revert ..."로 시작)
  * 커밋 메시지에 hotfix/rollback 계열 키워드가 포함된 커밋
  * `hotfix/`, `revert-` 접두사를 쓰는 브랜치

주의: 이 신호들만으로는 "장애로 인한 롤백"과 "기획 변경에 의한 되돌리기"를 구분할
수 없다 (문서 1.3 참고). Jira 장애 티켓과 교차 검증하려면 Jira API 연동이 필요하다.

사용 예:
    python3 change_failure_signals.py --repo /path/to/repo --branch main
"""
from __future__ import annotations

import argparse
import re

from git_utils import iter_commits, list_branches

HOTFIX_KEYWORDS = re.compile(r"\b(hotfix|rollback|roll back|revert)\b", re.IGNORECASE)
HOTFIX_BRANCH = re.compile(r"^(?:[^/]+/)?(hotfix/|revert-)", re.IGNORECASE)


def find_revert_commits(repo: str, branch: str) -> list[dict]:
    commits = iter_commits(repo, branch)
    return [
        {"hash": c.commit_hash[:10], "at": c.dt.isoformat(), "subject": c.subject}
        for c in commits
        if c.subject.strip().lower().startswith("revert")
    ]


def find_keyword_commits(repo: str, branch: str) -> list[dict]:
    commits = iter_commits(repo, branch)
    return [
        {"hash": c.commit_hash[:10], "at": c.dt.isoformat(), "subject": c.subject}
        for c in commits
        if HOTFIX_KEYWORDS.search(c.subject) and not c.subject.strip().lower().startswith("revert")
    ]


def find_hotfix_branches(repo: str) -> list[str]:
    return [b for b in list_branches(repo) if HOTFIX_BRANCH.match(b)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="분석할 git 저장소 경로")
    parser.add_argument("--branch", default="HEAD", help="분석 대상 브랜치")
    args = parser.parse_args()

    reverts = find_revert_commits(args.repo, args.branch)
    keyword_hits = find_keyword_commits(args.repo, args.branch)
    hotfix_branches = find_hotfix_branches(args.repo)

    print("# 변경 실패율(Change Failure) 신호 요약\n")
    print(f"## Revert 커밋 ({len(reverts)}건)")
    for r in reverts:
        print(f"  {r['hash']}  {r['at']}  {r['subject'][:70]}")

    print(f"\n## hotfix/rollback 키워드 커밋 ({len(keyword_hits)}건)")
    for r in keyword_hits:
        print(f"  {r['hash']}  {r['at']}  {r['subject'][:70]}")

    print(f"\n## hotfix/revert- 브랜치 ({len(hotfix_branches)}건)")
    for b in hotfix_branches:
        print(f"  {b}")

    print("\n※ 실제 '변경 실패'(장애) 여부는 Jira 장애 티켓과의 교차 검증이 필요합니다.")


if __name__ == "__main__":
    main()
