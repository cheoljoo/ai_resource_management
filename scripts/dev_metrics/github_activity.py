"""6.3절: 활동 폭/다양성 확장 (GitHub 연계) — AI Flywheel 8단계(인접 확장) 실행

`gh` CLI(GitHub 공식 CLI, 이미 인증된 세션)로 GraphQL `contributionsCollection`을
조회해, 로컬 git 저장소만으로는 볼 수 없는 **GitHub 공개/비공개 저장소 기여 이력**을
활동 폭/다양성(4.4절)에 더한다. 본인 계정 범위로만 조회한다(spec.md "본인 범위 한정"
원칙 — Expert Finder(6.6절)와 달리 이 스크립트는 예외 대상이 아니다).

사용 예:
    python3 github_activity.py --login cheoljoo
"""
from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter

GRAPHQL_QUERY = """
query($login: String!, $max: Int!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      commitContributionsByRepository(maxRepositories: $max) {
        repository {
          nameWithOwner
          primaryLanguage { name }
          isPrivate
        }
        contributions { totalCount }
      }
    }
  }
}
"""


def fetch_contributions(login: str, max_repos: int = 25) -> dict:
    result = subprocess.run(
        [
            "gh", "api", "graphql",
            "-f", f"query={GRAPHQL_QUERY}",
            "-f", f"login={login}",
            "-F", f"max={max_repos}",
        ],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def compute_github_breadth(login: str, max_repos: int, min_commits: int) -> dict:
    data = fetch_contributions(login, max_repos)
    user = data.get("data", {}).get("user")
    if not user:
        return {"error": "user not found or GraphQL query failed", "raw": data}

    collection = user["contributionsCollection"]
    by_repo = collection["commitContributionsByRepository"]

    per_repo = {}
    languages: Counter[str] = Counter()
    for entry in by_repo:
        repo = entry["repository"]["nameWithOwner"]
        commits = entry["contributions"]["totalCount"]
        lang = (entry["repository"].get("primaryLanguage") or {}).get("name") or "(unknown)"
        per_repo[repo] = {"commits": commits, "language": lang, "is_private": entry["repository"]["isPrivate"]}
        if commits >= min_commits:
            languages[lang] += 1

    qualifying = {r: info for r, info in per_repo.items() if info["commits"] >= min_commits}

    return {
        "login": login,
        "total_commit_contributions": collection["totalCommitContributions"],
        "per_repo": per_repo,
        "min_commits_threshold": min_commits,
        "qualifying_repo_count": len(qualifying),
        "qualifying_repos": sorted(qualifying.keys()),
        "distinct_languages": sorted(languages.keys()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login", required=True, help="조회할 본인 GitHub 로그인 (본인 범위 한정)")
    parser.add_argument("--max-repos", type=int, default=25, help="조회할 최대 저장소 수 (기본 25)")
    parser.add_argument(
        "--min-commits", type=int, default=2,
        help="저장소를 '실질 기여'로 인정할 최소 커밋 수 (기본 2) — 다양성 게이밍 방지용",
    )
    args = parser.parse_args()

    result = compute_github_breadth(args.login, args.max_repos, args.min_commits)
    if "error" in result:
        print(f"⚠️ {result['error']}")
        return

    print(f"# GitHub 활동 폭/다양성 ({result['login']}, 최근 1년 기준 GitHub 기본 집계)\n")
    print(f"총 커밋 기여: {result['total_commit_contributions']}건\n")
    print(f"{'repo':<45} {'commits':>8} {'language':<15} {'qualifies':>10}")
    for repo, info in sorted(result["per_repo"].items(), key=lambda kv: -kv[1]["commits"]):
        qualifies = repo in result["qualifying_repos"]
        print(f"{repo:<45} {info['commits']:>8} {info['language']:<15} {str(qualifies):>10}")

    print(f"\n실질 기여 저장소 수(임계치 {result['min_commits_threshold']}건 이상): {result['qualifying_repo_count']}")
    print(f"확인된 언어 수: {len(result['distinct_languages'])} -> {', '.join(result['distinct_languages'])}")
    print(
        "\n※ 로컬 git 기반 activity_breadth.py와 합산해 4.4절 활동 폭/다양성 지표를 보강하는 용도입니다"
        " (developer_evaluation_metrics.md 6.3절 참고). 사내 GitLab/Gerrit 활동과는 별도 집계입니다."
    )


if __name__ == "__main__":
    main()
