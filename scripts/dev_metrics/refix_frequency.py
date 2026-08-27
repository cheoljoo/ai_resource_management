"""1.2 단기 재수정(Re-fix) 빈도

특정 파일이 커밋으로 수정된 후 N일(기본 30~90일) 이내에 같은 파일이 다시 수정되는
패턴을 탐지한다. 커밋 메시지에 fix/bug/issue 등의 키워드가 있으면 "확정적 재작업
(confirmed_refix)"으로, 없으면 단순 "재수정 후보(candidate)"로 구분한다.

로컬 git 이력(git log --name-only)만으로 계산 가능. Gerrit Change/Patchset 단위
메타데이터까지 반영하려면 Gerrit API가 추가로 필요하다 (문서 1.2 참고).

사용 예:
    python3 refix_frequency.py --repo /path/to/repo --window-days 30
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict

from git_utils import iter_commits

FIX_KEYWORDS = re.compile(r"\b(fix|fixed|fixes|bug|hotfix|issue|defect)\b", re.IGNORECASE)


def compute_refix_events(repo: str, branch: str, window_days: int) -> list[dict]:
    commits = iter_commits(repo, branch, with_files=True)
    commits.sort(key=lambda c: c.author_ts)  # oldest -> newest

    file_history: dict[str, list] = defaultdict(list)
    for c in commits:
        if c.is_merge:
            continue
        for f in c.files:
            file_history[f].append(c)

    window_seconds = window_days * 86400
    events = []
    for path, touches in file_history.items():
        for prev, cur in zip(touches, touches[1:]):
            gap = cur.author_ts - prev.author_ts
            if gap <= window_seconds:
                events.append(
                    {
                        "file": path,
                        "prev_commit": prev.commit_hash[:10],
                        "prev_at": prev.dt.isoformat(),
                        "refix_commit": cur.commit_hash[:10],
                        "refix_at": cur.dt.isoformat(),
                        "gap_days": round(gap / 86400, 1),
                        "confirmed_refix": bool(FIX_KEYWORDS.search(cur.subject)),
                        "refix_subject": cur.subject,
                    }
                )
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="분석할 git 저장소 경로")
    parser.add_argument("--branch", default="HEAD", help="분석 대상 브랜치")
    parser.add_argument("--window-days", type=int, default=30, help="재수정 판단 기간(일)")
    parser.add_argument("--top", type=int, default=30, help="출력할 최대 이벤트 수")
    args = parser.parse_args()

    events = compute_refix_events(args.repo, args.branch, args.window_days)
    if not events:
        print("재수정 이벤트를 찾지 못했습니다.")
        return

    confirmed = sum(1 for e in events if e["confirmed_refix"])
    print(f"# 단기 재수정 빈도 분석 ({args.window_days}일 이내, 총 {len(events)}건, "
          f"확정적 재작업 {confirmed}건)\n")
    print(f"{'gap(d)':>6} {'confirmed':>9}  file -> refix_commit  subject")
    for e in sorted(events, key=lambda x: x["gap_days"])[: args.top]:
        print(f"{e['gap_days']:>6} {str(e['confirmed_refix']):>9}  "
              f"{e['file']} -> {e['refix_commit']}  {e['refix_subject'][:50]}")


if __name__ == "__main__":
    main()
