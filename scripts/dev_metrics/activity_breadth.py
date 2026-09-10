"""신규 지표: 활동 폭/다양성 (Activity Breadth / Diversity)

원 티켓("얼마나 많은 분야에서 활동하는가")에 대응하는 지표. 여러 로컬 git 저장소에
걸친 커밋 분포와 건드린 파일 확장자(기술 스택) 다양성을 집계한다.

안티패턴 방지 (developer_evaluation_metrics.md 1.3절 5번째 행 참고): 다양성 점수를
높이려고 여러 저장소에 실질 기여 없는 사소한 커밋을 흩뿌리는 행동을 막기 위해,
저장소당 변경 라인 수(추가+삭제)가 --min-lines-changed 임계치 이상인 경우만
"실질 기여 저장소"로 인정한다.

사용 예:
    python3 activity_breadth.py --repos /path/to/repo1 /path/to/repo2 --author "cheoljoo"
"""
from __future__ import annotations

import argparse
import os
import subprocess
from collections import defaultdict

from git_utils import iter_commits


def _lines_changed_by_author(repo: str, author: str | None, branch: str) -> int:
    args = ["git", "-C", repo, "log", "--pretty=format:", "--numstat", branch]
    if author:
        args = ["git", "-C", repo, "log", f"--author={author}", "--pretty=format:", "--numstat", branch]
    result = subprocess.run(args, capture_output=True, text=True, check=True)
    total = 0
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, _path = parts
        if added == "-" or deleted == "-":
            continue  # binary file
        total += int(added) + int(deleted)
    return total


def compute_activity_breadth(
    repos: list[str],
    author: str | None = None,
    branch: str = "HEAD",
    min_lines_changed: int = 20,
) -> dict:
    per_repo: dict[str, dict] = {}
    for repo in repos:
        commits = iter_commits(repo, branch, with_files=True)
        if author:
            commits = [c for c in commits if author in c.author_email or author in c.author_name]
        if not commits:
            per_repo[repo] = {"commits": 0, "lines_changed": 0, "extensions": []}
            continue
        extensions = set()
        for c in commits:
            for f in c.files:
                _, ext = os.path.splitext(f)
                if ext:
                    extensions.add(ext.lstrip("."))
        try:
            lines_changed = _lines_changed_by_author(repo, author, branch)
        except subprocess.CalledProcessError:
            lines_changed = 0
        per_repo[repo] = {
            "commits": len(commits),
            "lines_changed": lines_changed,
            "extensions": sorted(extensions),
        }

    qualifying = {
        repo: info for repo, info in per_repo.items() if info["lines_changed"] >= min_lines_changed
    }
    distinct_extensions: set[str] = set()
    for info in qualifying.values():
        distinct_extensions.update(info["extensions"])

    return {
        "per_repo": per_repo,
        "min_lines_changed_threshold": min_lines_changed,
        "qualifying_repo_count": len(qualifying),
        "qualifying_repos": sorted(qualifying.keys()),
        "distinct_extension_count": len(distinct_extensions),
        "distinct_extensions": sorted(distinct_extensions),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repos", nargs="+", required=True, help="분석할 git 저장소 경로 목록")
    parser.add_argument("--author", default=None, help="특정 작성자(이름/이메일 일부)로 범위 제한")
    parser.add_argument("--branch", default="HEAD", help="분석 대상 브랜치")
    parser.add_argument(
        "--min-lines-changed",
        type=int,
        default=20,
        help="저장소를 '실질 기여'로 인정할 최소 변경 라인 수(추가+삭제, 기본 20) — 다양성 게이밍 방지용",
    )
    args = parser.parse_args()

    result = compute_activity_breadth(args.repos, args.author, args.branch, args.min_lines_changed)

    print(f"# 활동 폭/다양성 분석 (임계치: 저장소당 {result['min_lines_changed_threshold']}줄 이상 변경)\n")
    print(f"{'repo':<40} {'commits':>8} {'lines_changed':>14} {'qualifies':>10}")
    for repo, info in sorted(result["per_repo"].items(), key=lambda kv: -kv[1]["lines_changed"]):
        qualifies = repo in result["qualifying_repos"]
        print(f"{repo:<40} {info['commits']:>8} {info['lines_changed']:>14} {str(qualifies):>10}")

    print(f"\n실질 기여 저장소 수: {result['qualifying_repo_count']} / {len(result['per_repo'])}")
    print(f"확인된 기술 스택(파일 확장자) 수: {result['distinct_extension_count']}")
    print(f"  -> {', '.join(result['distinct_extensions']) or '(없음)'}")
    print(
        "\n※ 임계치 미달 저장소는 '사소한 커밋 흩뿌리기' 게이밍을 배제하기 위해 카운트에서 제외됨"
        " (developer_evaluation_metrics.md 1.3절 참고)."
    )


if __name__ == "__main__":
    main()
