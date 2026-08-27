"""5.1 번아웃 위험도 (Burnout Signals) - Git 부분만

정규 근무시간 외(기본: 21시~07시) 또는 주말(토/일)에 발생한 커밋 비율을 작성자별로
집계한다. Teams 캘린더 기반 주간 회의 시간 합산은 이번 검토 범위에서 제외되었다
(문서 5.1 참고, Teams 관련 항목은 ⏭️ 범위 제외).

주의: 유연근무제 등 개인 근무 패턴일 수 있으므로 평가가 아닌 웰빙 케어 알림
용도로만 사용해야 한다 (문서 5.1 보완/주의점 참고).

사용 예:
    python3 burnout_signals.py --repo /path/to/repo --after-hour 21 --before-hour 7
"""
from __future__ import annotations

import argparse
from collections import defaultdict

from git_utils import iter_commits

WEEKEND_DAYS = {5, 6}  # datetime.weekday(): 5=Saturday, 6=Sunday


def compute_burnout_signals(repo: str, branch: str, after_hour: int, before_hour: int, author: str | None = None) -> dict[str, dict]:
    commits = iter_commits(repo, branch)
    if author:
        commits = [c for c in commits if author in c.author_email or author in c.author_name]
    stats: dict[str, dict] = defaultdict(lambda: {"total": 0, "after_hours": 0, "weekend": 0})

    for c in commits:
        dt = c.dt
        s = stats[c.author_name]
        s["total"] += 1
        if dt.hour >= after_hour or dt.hour < before_hour:
            s["after_hours"] += 1
        if dt.weekday() in WEEKEND_DAYS:
            s["weekend"] += 1

    for s in stats.values():
        s["after_hours_pct"] = round(100 * s["after_hours"] / s["total"], 1) if s["total"] else 0.0
        s["weekend_pct"] = round(100 * s["weekend"] / s["total"], 1) if s["total"] else 0.0
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="분석할 git 저장소 경로")
    parser.add_argument("--branch", default="HEAD", help="분석 대상 브랜치")
    parser.add_argument("--after-hour", type=int, default=21, help="야간 시작 시각 (24h, 기본 21시)")
    parser.add_argument("--before-hour", type=int, default=7, help="야간 종료 시각 (24h, 기본 7시)")
    parser.add_argument("--author", default=None, help="특정 작성자(이름/이메일 일부)로 범위 제한")
    args = parser.parse_args()

    stats = compute_burnout_signals(args.repo, args.branch, args.after_hour, args.before_hour, args.author)

    print(f"# 번아웃 위험 신호 (야간: {args.after_hour}시~{args.before_hour}시, 주말 포함)\n")
    print(f"{'author':<25} {'total':>6} {'after_hours':>12} {'%':>6} {'weekend':>8} {'%':>6}")
    for author, s in sorted(stats.items(), key=lambda kv: -kv[1]["after_hours_pct"]):
        print(f"{author:<25} {s['total']:>6} {s['after_hours']:>12} {s['after_hours_pct']:>6} "
              f"{s['weekend']:>8} {s['weekend_pct']:>6}")

    print("\n※ 개인 근무 패턴/유연근무제일 수 있으므로 평가가 아닌 웰빙 케어 알림 용도로만 사용하세요.")


if __name__ == "__main__":
    main()
