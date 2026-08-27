"""4.1 선행 검증 및 PoC 수행 능력 - 브랜치 이력 기반 (부분 자동화)

로컬 저장소의 브랜치 생성/커밋 이력으로 "정식 서브밋 이전 선행 검증" 활동을
근사 추정한다: 브랜치별 최초/최근 커밋 시각, 커밋 수, main 대비 merge 여부를
집계하고 poc/, spike/, experiment/, prototype/ 접두사 브랜치를 PoC 후보로 표시한다.

Collab에 작성된 POC 보고서 존재 여부까지 반영하려면 Confluence API 연동이
추가로 필요하다 (문서 4.1 참고).

사용 예:
    python3 poc_branch_history.py --repo /path/to/repo
"""
from __future__ import annotations

import argparse
import re
import subprocess

from git_utils import default_branch, iter_commits, list_branches, run_git

POC_PREFIX = re.compile(r"^(?:[^/]+/)?(poc|spike|experiment|prototype)[-/]", re.IGNORECASE)


def analyze_branch(repo: str, branch: str, base: str) -> dict | None:
    try:
        commits = iter_commits(repo, branch, extra_args=[f"{base}..{branch}"] if base else None)
    except subprocess.CalledProcessError:
        return None
    if not commits:
        return None

    commits.sort(key=lambda c: c.author_ts)
    try:
        run_git(repo, ["merge-base", "--is-ancestor", branch, base])
        merged = True
    except subprocess.CalledProcessError:
        merged = False

    return {
        "branch": branch,
        "is_poc": bool(POC_PREFIX.match(branch)),
        "commits": len(commits),
        "first_commit_at": commits[0].dt.isoformat(),
        "last_commit_at": commits[-1].dt.isoformat(),
        "author": commits[0].author_name,
        "merged_into_base": merged,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="분석할 git 저장소 경로")
    parser.add_argument("--base", default=None, help="비교 기준 브랜치 (기본: 자동 감지된 main/master)")
    parser.add_argument("--poc-only", action="store_true", help="poc/spike/experiment 접두사 브랜치만 출력")
    args = parser.parse_args()

    base = args.base or default_branch(args.repo)
    branches = [b for b in list_branches(args.repo) if b != base and not b.endswith(f"/{base}")]

    rows = []
    for b in branches:
        row = analyze_branch(args.repo, b, base)
        if row and (not args.poc_only or row["is_poc"]):
            rows.append(row)

    print(f"# 브랜치 기반 선행 검증(PoC) 이력 (base={base}, 총 {len(rows)}개 브랜치)\n")
    print(f"{'branch':<30} {'poc?':>5} {'commits':>7} {'author':<20} {'first':<26} {'merged':>7}")
    for r in sorted(rows, key=lambda x: x["first_commit_at"]):
        print(f"{r['branch']:<30} {str(r['is_poc']):>5} {r['commits']:>7} {r['author']:<20} "
              f"{r['first_commit_at']:<26} {str(r['merged_into_base']):>7}")


if __name__ == "__main__":
    main()
