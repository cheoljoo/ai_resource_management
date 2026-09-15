"""spec.md 완료조건 3·8: 기존 지표 스크립트를 종합해 다차원 프로필과 두 개의
데이터 전용 신호(지속적 고기여 인정 신호 / 지속적 저활동 경고 신호)를 산출한다.

이 스크립트는 시스템 메타데이터(로컬 git, 그리고 선택적으로 gerrit_metrics.py /
jira_metrics.py의 JSON 출력)만 입력으로 받는다 — 설문/자기보고는 사용하지 않는다
(developer_evaluation_metrics.md 1.4절 데이터 우선 원칙).

가드레일 (모두 developer_evaluation_metrics.md 1.5~1.6절과 spec.md 완료조건 8번에서
그대로 가져온 것 — 여기서 완화하지 않는다):
  * 5대 대항목 중 최소 3개 이상에 데이터가 있어야 프로필을 발행한다.
  * 두 신호 모두 단일 지표가 아니라 여러 독립 축의 조합으로만 계산한다.
  * 두 신호는 최종 결론이 아니라 사람의 확인이 필요하다는 트리거일 뿐이다 — 항상
    그 취지의 경고 문구를 함께 출력한다.
  * 원시 수치는 --raw 옵션 없이는 출력하지 않는다("등급/평가/점수" 대신 "진단/
    프로필/신호"라는 표현을 쓴다).

사용 예:
    python3 composite_signals.py --repo ~/code/llm_wiki \
        --repos ~/code/llm_wiki ~/code/sage-wiki ~/code/ccr \
        --author "cheoljoo" --raw
"""
from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone

from activity_breadth import compute_activity_breadth
from burnout_signals import compute_burnout_signals
from change_failure_signals import find_hotfix_branches, find_keyword_commits, find_revert_commits
from experience_atoms import breadth_depth, compute_experience_atoms
from git_utils import iter_commits
from lead_time import compute_lead_times
from monthly_activity_clusters import compute_clusters
from poc_branch_history import analyze_branch, default_branch as detect_default_branch, list_branches
from refix_frequency import compute_refix_events
from run_history import append_run

BAND_WATCH = "관찰 필요"
BAND_OK = "양호"
BAND_GOOD = "우수"
BAND_NA = "데이터 없음"

DISCLAIMER = """\
※ 이 리포트는 인사 평가 자료가 아닙니다 (developer_evaluation_metrics.md 1.3절 Goodhart's Law,
  7장 "인사 평가 직접 연동 금지" 원칙). 병목 진단·자기 회고·지원 대화의 출발점으로만 사용하세요.
※ "지속적 고기여 인정 신호"와 "지속적 저활동 경고 신호"는 최종 판단이 아니라 사람의 확인이
  필요하다는 트리거입니다. 특히 경고 신호는 역량 부족의 증거가 아니라 판별 불능을 의미할 뿐입니다
  (Montandon et al. 2019 — 고신호는 실제 전문가와 65~75% 일치하지만 저신호로는 초보자와 숨은
  전문가를 구분하는 정확도가 F=0.56에 그침. developer_evaluation_metrics.md 1.5절 참고).\
"""


def _quality_band(repo: str, branch: str, author: str | None) -> tuple[str, dict]:
    """대항목 1: 재작업률(1.2) + 변경 실패율(1.3) 신호 조합."""
    refix_events = compute_refix_events(repo, branch, window_days=30)
    if author:
        refix_events = [e for e in refix_events if True]  # refix_events는 파일 단위라 author 필터 불가(문서 1.2 한계)
    reverts = find_revert_commits(repo, branch)
    keyword_hits = find_keyword_commits(repo, branch)
    hotfix_branches = find_hotfix_branches(repo)

    total_commits = len(iter_commits(repo, branch))
    confirmed_refix = sum(1 for e in refix_events if e["confirmed_refix"])
    failure_signal_count = len(reverts) + len(keyword_hits) + len(hotfix_branches)

    evidence = {
        "total_commits": total_commits,
        "confirmed_refix_events": confirmed_refix,
        "revert_commits": len(reverts),
        "hotfix_keyword_commits": len(keyword_hits),
        "hotfix_branches": len(hotfix_branches),
    }
    if total_commits == 0:
        return BAND_NA, evidence

    refix_rate = confirmed_refix / total_commits
    failure_rate = failure_signal_count / total_commits

    if refix_rate > 0.15 or failure_rate > 0.05:
        return BAND_WATCH, evidence
    if refix_rate < 0.05 and failure_rate < 0.01:
        return BAND_GOOD, evidence
    return BAND_OK, evidence


def _velocity_band(repo: str, branch: str) -> tuple[str, dict]:
    """대항목 2: 변경 리드 타임(2.1)."""
    rows = compute_lead_times(repo, branch)
    if not rows:
        return BAND_NA, {"merge_count": 0}
    hours = [r["lead_time_hours"] for r in rows]
    median_hours = statistics.median(hours)
    evidence = {"merge_count": len(rows), "lead_time_median_hours": round(median_hours, 2)}
    if median_hours > 120:  # 5일 초과
        return BAND_WATCH, evidence
    if median_hours < 24:
        return BAND_GOOD, evidence
    return BAND_OK, evidence


def _problem_solving_band(repo: str, branch: str, author: str | None, activity: dict) -> tuple[str, dict]:
    """대항목 4: 선행 검증/PoC(4.1) + 활동 폭/다양성 + 경험 원자(EA, 4.4절, Mockus & Herbsleb 2002)."""
    base = detect_default_branch(repo)
    branches = [b for b in list_branches(repo) if b != base and not b.endswith(f"/{base}")]
    poc_rows = [r for r in (analyze_branch(repo, b, base) for b in branches) if r]
    poc_count = sum(1 for r in poc_rows if r["is_poc"])

    ea = compute_experience_atoms(repo, author, module_depth=2, branch=branch)
    ea_breadth, ea_depth, ea_deepest_module = breadth_depth(ea["module_ea"], min_ea=5)
    ea_summary = {
        "breadth_module_count": ea_breadth,
        "depth_max_ea": ea_depth,
        "deepest_module": ea_deepest_module,
    }

    evidence = {
        "poc_branch_count": poc_count,
        "qualifying_repo_count": activity["qualifying_repo_count"],
        "distinct_extension_count": activity["distinct_extension_count"],
        "ea_breadth_module_count": ea_summary["breadth_module_count"],
        "ea_depth_max": ea_summary["depth_max_ea"],
        "ea_deepest_module": ea_summary["deepest_module"],
    }
    # 1.5절 비대칭 원칙: PoC/다양성/EA가 "낮다"고 관찰 필요로 깎지 않는다 — 활동이 없다는 것이
    # 곧 역량 부족은 아니기 때문(Montandon et al. 2019). 높을 때만 우수로 가점한다.
    if poc_count >= 1 or activity["qualifying_repo_count"] >= 3 or ea_summary["breadth_module_count"] >= 5:
        return BAND_GOOD, evidence
    return BAND_OK, evidence


def _wellbeing_band(repo: str, branch: str, author: str | None) -> tuple[str, dict]:
    """대항목 5: 번아웃 위험도(5.1) — 밴드가 낮을수록(위험 낮을수록) 좋다는 점에 유의."""
    stats = compute_burnout_signals(repo, branch, after_hour=21, before_hour=7, author=author)
    if not stats:
        return BAND_NA, {}
    # author 필터가 없으면 여러 명이 섞이므로 총합으로 근사
    total = sum(s["total"] for s in stats.values())
    after_hours = sum(s["after_hours"] for s in stats.values())
    weekend = sum(s["weekend"] for s in stats.values())
    if total == 0:
        return BAND_NA, {}
    after_hours_pct = round(100 * after_hours / total, 1)
    weekend_pct = round(100 * weekend / total, 1)
    evidence = {"total_commits": total, "after_hours_pct": after_hours_pct, "weekend_pct": weekend_pct}
    if after_hours_pct > 30 or weekend_pct > 20:
        return BAND_WATCH, evidence
    return BAND_OK, evidence


def compute_profile(
    repo: str,
    repos_for_breadth: list[str],
    author: str | None,
    branch: str,
) -> dict:
    activity = compute_activity_breadth(repos_for_breadth, author, branch)
    trend = compute_clusters(repo, branch, author)  # Montandon et al. 2019 방법론(시간축 버전)

    categories = {
        "1. 코드 품질 및 완성도": _quality_band(repo, branch, author),
        "2. 개발 속도와 흐름": _velocity_band(repo, branch),
        "3. 협업 및 팀 기여도": (BAND_NA, {"reason": "Gerrit/Jira API 미연결 — 이번 실행 범위 밖"}),
        "4. 문제 정의 및 설계 역량 (+활동 폭/다양성/EA)": _problem_solving_band(repo, branch, author, activity),
        "5. 지속 가능성 및 웰빙": _wellbeing_band(repo, branch, author),
    }

    filled = {name: (band, ev) for name, (band, ev) in categories.items() if band != BAND_NA}
    return {
        "categories": categories,
        "filled_count": len(filled),
        "activity_breadth": activity,
        "trend": trend,
    }


def compute_recognition_signal(profile: dict) -> tuple[bool, str]:
    good_count = sum(1 for band, _ in profile["categories"].values() if band == BAND_GOOD)
    watch_in_quality = profile["categories"]["1. 코드 품질 및 완성도"][0] == BAND_WATCH
    if good_count < 3 or watch_in_quality:
        return False, f"'우수' 구간 {good_count}개 (기준 3개 미달 또는 품질 지표 '관찰 필요')"

    trend = profile["trend"]
    if trend["clustered"] and trend["consecutive_low_months_recent"] >= 2:
        # 스냅샷은 좋아 보여도, 클러스터링 결과 최근 몇 달이 '저활동 클러스터'라면 지속성 조건을
        # 만족하지 못하는 것 — 단일 시점 값만으로 "지속적" 인정 신호를 내지 않는다.
        return False, (
            f"대항목 밴드는 기준을 만족하지만 최근 {trend['consecutive_low_months_recent']}개월이 "
            "월별 활동 클러스터링상 '저활동 클러스터'라 '지속적' 조건 미달"
        )

    trend_note = ""
    if trend["clustered"]:
        trend_note = f", 최근 {trend['consecutive_high_months_recent']}개월 연속 고활동 클러스터"
    return True, f"{good_count}개 대항목이 '우수' 구간이며 품질 지표도 양호함{trend_note}"


def compute_warning_sign(profile: dict) -> tuple[bool, str]:
    watch_count = sum(1 for band, _ in profile["categories"].values() if band == BAND_WATCH)
    na_count = sum(1 for band, _ in profile["categories"].values() if band == BAND_NA)
    # 안전장치: 데이터가 있는 축이 너무 적으면 판단하지 않는다.
    if profile["filled_count"] < 3:
        return False, "데이터가 채워진 대항목이 3개 미만이라 판단 보류"
    if watch_count < 4:
        return False, f"'관찰 필요' 구간 {watch_count}개, 데이터 없음 {na_count}개 (경고 신호 기준 4개 미달)"

    trend = profile["trend"]
    if not trend["clustered"]:
        return True, (
            f"5대 대항목 중 {watch_count}개가 '관찰 필요' 구간 — 다만 월별 데이터가 부족해 "
            f"'지속성(sustained)'은 확인하지 못한 단일 시점 스냅샷임({trend['reason']})"
        )
    if trend["consecutive_low_months_recent"] < 2:
        return False, (
            f"'관찰 필요' 구간 {watch_count}개이지만, 월별 활동 클러스터링상 최근 저활동 클러스터가"
            f" {trend['consecutive_low_months_recent']}개월뿐이라 '지속적' 조건(2개월 이상) 미달"
        )
    return True, (
        f"5대 대항목 중 {watch_count}개가 '관찰 필요' 구간 + 월별 클러스터링상 최근 "
        f"{trend['consecutive_low_months_recent']}개월 연속 저활동 클러스터 (경고 신호 — 확정적 결론 아님)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="품질/속도/문제정의/웰빙 지표를 계산할 주 저장소")
    parser.add_argument(
        "--repos", nargs="*", default=None,
        help="활동 폭/다양성 계산에 포함할 저장소 목록 (생략 시 --repo 하나만 사용)",
    )
    parser.add_argument("--author", default=None, help="특정 작성자(이름/이메일 일부)로 범위 제한")
    parser.add_argument("--branch", default="HEAD", help="분석 대상 브랜치")
    parser.add_argument(
        "--raw", action="store_true",
        help="대항목별 원시 근거 수치를 함께 출력 (기본은 밴드만 출력)",
    )
    parser.add_argument(
        "--log-history", action="store_true",
        help="이번 실행 결과를 run_history.py의 실행 이력에 누적 기록 (AI Flywheel 7단계 —"
        " 임계치 재보정을 위한 실측 데이터 축적, 기본은 기록하지 않음)",
    )
    args = parser.parse_args()

    repos_for_breadth = args.repos or [args.repo]
    profile = compute_profile(args.repo, repos_for_breadth, args.author, args.branch)

    print(f"# 개발자 진단 프로필 (생성 시각: {datetime.now(timezone.utc).isoformat()})\n")

    if profile["filled_count"] < 3:
        print(
            f"⚠️ 5대 대항목 중 데이터가 채워진 항목이 {profile['filled_count']}개뿐입니다 "
            "(최소 3개 필요 — spec.md 완료조건 3번 가드레일). 프로필을 발행하지 않습니다."
        )
        return

    if args.log_history:
        append_run(profile, args.repo, args.author)
        print("📝 이번 실행 결과를 run_history.py 이력에 기록했습니다 (`python3 run_history.py --show`로 확인).\n")

    print("## 대항목별 밴드 (관찰 필요 / 양호 / 우수 / 데이터 없음)\n")
    for name, (band, evidence) in profile["categories"].items():
        print(f"- {name}: **{band}**")
        if args.raw and evidence:
            print(f"    근거: {json.dumps(evidence, ensure_ascii=False)}")

    if args.raw:
        print("\n⚠️ --raw 옵션으로 원시 수치를 출력했습니다. 이 수치를 인사평가나 개인 간 비교에 쓰지 마십시오.")

    recognized, recognition_reason = compute_recognition_signal(profile)
    warned, warning_reason = compute_warning_sign(profile)

    print("\n## 데이터 전용 종합 신호\n")
    print(f"- 지속적 고기여 인정 신호: {'🟢 발생' if recognized else '⚪ 미발생'} — {recognition_reason}")
    print(f"- 지속적 저활동 경고 신호: {'🟡 발생' if warned else '⚪ 미발생'} — {warning_reason}")
    if warned:
        print(
            "  → 이 신호는 자동 조치를 의미하지 않습니다. 매니저/본인과의 1:1 확인 대화를 여는"
            " 트리거로만 사용하세요."
        )

    print(f"\n{DISCLAIMER}")


if __name__ == "__main__":
    main()
