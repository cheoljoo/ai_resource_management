"""2.2 몰입 시간 확보율 (Focus Time) - Inter-Event Gap 휴리스틱 (Git 부분만)

동일 작성자의 커밋 타임스탬프 간 간격이 `--gap-minutes` 이내로 이어지면 하나의
"Focus 세션"으로 묶어 몰입 구간을 근사 추정한다. Teams 캘린더 기반 Inverse
Calendar Block 분석은 이번 검토 범위에서 제외되었다 (문서 2.2 참고, Teams 관련
항목은 ⏭️ 범위 제외).

사용 예:
    python3 focus_time.py --repo /path/to/repo --gap-minutes 120
"""
from __future__ import annotations

import argparse
from collections import defaultdict

from git_utils import iter_commits

MIN_SESSION_SECONDS = 15 * 60  # 커밋 1건만 있는 세션도 최소 15분 몰입으로 인정


def compute_focus_sessions(repo: str, branch: str, gap_minutes: int, author: str | None = None) -> dict[str, list[dict]]:
    commits = iter_commits(repo, branch)
    if author:
        commits = [c for c in commits if author in c.author_email or author in c.author_name]
    commits.sort(key=lambda c: c.author_ts)

    by_author: dict[str, list] = defaultdict(list)
    for c in commits:
        by_author[c.author_name].append(c)

    gap_seconds = gap_minutes * 60
    sessions_by_author: dict[str, list[dict]] = {}
    for author, author_commits in by_author.items():
        sessions = []
        session_start = session_end = author_commits[0].author_ts
        commit_count = 1
        for c in author_commits[1:]:
            if c.author_ts - session_end <= gap_seconds:
                session_end = c.author_ts
                commit_count += 1
            else:
                sessions.append(_session_dict(session_start, session_end, commit_count))
                session_start = session_end = c.author_ts
                commit_count = 1
        sessions.append(_session_dict(session_start, session_end, commit_count))
        sessions_by_author[author] = sessions
    return sessions_by_author


def _session_dict(start_ts: int, end_ts: int, commit_count: int) -> dict:
    duration = max(end_ts - start_ts, MIN_SESSION_SECONDS)
    return {
        "start_ts": start_ts,
        "end_ts": end_ts,
        "commit_count": commit_count,
        "duration_hours": round(duration / 3600, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="분석할 git 저장소 경로")
    parser.add_argument("--branch", default="HEAD", help="분석 대상 브랜치")
    parser.add_argument("--gap-minutes", type=int, default=120, help="세션을 묶는 최대 공백(분)")
    parser.add_argument("--author", default=None, help="특정 작성자(이름/이메일 일부)로 범위 제한")
    args = parser.parse_args()

    sessions_by_author = compute_focus_sessions(args.repo, args.branch, args.gap_minutes, args.author)

    print(f"# Focus Time 추정 (Inter-Event Gap <= {args.gap_minutes}분, Git 커밋 기준)\n")
    for author, sessions in sessions_by_author.items():
        total_hours = sum(s["duration_hours"] for s in sessions)
        avg_hours = total_hours / len(sessions) if sessions else 0
        print(f"## {author}: 세션 {len(sessions)}개, 총 추정 몰입시간 {round(total_hours, 2)}h, "
              f"세션당 평균 {round(avg_hours, 2)}h")


if __name__ == "__main__":
    main()
