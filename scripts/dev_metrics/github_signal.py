"""전문가 파인더 — GitHub 활동 신호 (spec.md B안, 5개 소스 결합의 일부)

이 세션에는 GitHub 전용 MCP가 연결돼 있지 않아, 로컬에 이미 인증된 `gh` CLI
(계정 확인은 `gh auth status`)를 그대로 사용한다. 커밋/PR/이슈 메타데이터만
집계하며 코드 본문은 가져오지 않는다.

사용 예:
    python3 github_signal.py --repo cheoljoo/sage-wiki
"""
from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter


def _gh_json(args: list[str]) -> list[dict]:
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  gh 호출 실패({' '.join(args)}): {result.stderr.strip()[:200]}")
        return []
    try:
        return json.loads(result.stdout) if result.stdout.strip() else []
    except json.JSONDecodeError:
        return []


def collect_signal(repo: str) -> dict:
    commit_authors = Counter()
    for line in subprocess.run(
        ["gh", "api", f"repos/{repo}/commits", "--paginate", "-q", ".[] | .commit.author.email"],
        capture_output=True, text=True,
    ).stdout.splitlines():
        if line.strip():
            commit_authors[line.strip()] += 1

    pr_authors = Counter()
    for pr in _gh_json(["api", f"repos/{repo}/pulls?state=all", "--paginate"]):
        login = pr.get("user", {}).get("login")
        if login:
            pr_authors[login] += 1

    issue_authors = Counter()
    for issue in _gh_json(["api", f"repos/{repo}/issues?state=all", "--paginate"]):
        if "pull_request" in issue:
            continue
        login = issue.get("user", {}).get("login")
        if login:
            issue_authors[login] += 1

    return {"commits": commit_authors, "prs": pr_authors, "issues": issue_authors}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", action="append", required=True, help="owner/repo 형식, 복수 지정 가능")
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args()

    combined = {"commits": Counter(), "prs": Counter(), "issues": Counter()}
    for repo in args.repo:
        print(f"# GitHub 신호 — {repo}")
        sig = collect_signal(repo)
        for key in combined:
            combined[key].update(sig[key])
        for key, label in [("commits", "커밋"), ("prs", "PR"), ("issues", "이슈")]:
            print(f"  {label}: {dict(sig[key].most_common(5))}")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump({k: dict(v) for k, v in combined.items()}, f, ensure_ascii=False, indent=2)
        print(f"# JSON 저장: {args.json_out}")


if __name__ == "__main__":
    main()
