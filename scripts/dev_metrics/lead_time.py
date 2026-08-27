"""2.1 변경 리드 타임 (Lead Time for Changes)

merge commit 을 "Gerrit Final Submit" 에 대응하는 시점으로 보고, 병합된 브랜치에서
가장 오래된 커밋(=최초 작업 시작 시점, "First Upload"에 대응)까지의 시간차를 리드
타임으로 근사 계산한다.

로컬 git 저장소의 merge commit 이력만으로 계산 가능 (git_utils.iter_commits 참고).
Gerrit의 실제 First-Upload 시각까지 반영하려면 Gerrit REST API 연동이 추가로 필요하다.

사용 예:
    python3 lead_time.py --repo /path/to/repo --branch main
"""
from __future__ import annotations

import argparse
import statistics
from datetime import timedelta

from git_utils import iter_commits, run_git


def compute_lead_times(repo: str, branch: str) -> list[dict]:
    merges = [c for c in iter_commits(repo, branch, extra_args=["--merges"])]
    results = []
    for m in merges:
        if len(m.parents) != 2:
            continue
        base_parent, feature_parent = m.parents
        try:
            branch_commits = iter_commits(repo, f"{base_parent}..{feature_parent}")
        except Exception:
            continue
        if not branch_commits:
            continue
        earliest = min(c.author_ts for c in branch_commits)
        lead_seconds = m.author_ts - earliest
        if lead_seconds < 0:
            continue
        results.append(
            {
                "merge_commit": m.commit_hash[:10],
                "merge_subject": m.subject,
                "merged_at": m.dt.isoformat(),
                "commits_in_change": len(branch_commits),
                "lead_time_hours": round(lead_seconds / 3600, 2),
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="분석할 git 저장소 경로")
    parser.add_argument("--branch", default="HEAD", help="병합 대상 브랜치 (기본: HEAD)")
    parser.add_argument("--top", type=int, default=20, help="출력할 최근 merge 개수")
    args = parser.parse_args()

    rows = compute_lead_times(args.repo, args.branch)
    if not rows:
        print("merge commit을 찾지 못했습니다 (feature-branch + merge 워크플로우가 아닐 수 있습니다).")
        return

    hours = [r["lead_time_hours"] for r in rows]
    print(f"# 변경 리드 타임 분석 (merge commit 기준, 총 {len(rows)}건)\n")
    print(f"평균: {round(statistics.mean(hours), 2)}h  중앙값: {round(statistics.median(hours), 2)}h  "
          f"최대: {round(max(hours), 2)}h  최소: {round(min(hours), 2)}h\n")

    print(f"{'merge':<10} {'merged_at':<26} {'commits':>7} {'lead_time(h)':>13}  subject")
    for r in rows[: args.top]:
        print(f"{r['merge_commit']:<10} {r['merged_at']:<26} {r['commits_in_change']:>7} "
              f"{r['lead_time_hours']:>13}  {r['merge_subject'][:60]}")


if __name__ == "__main__":
    main()
