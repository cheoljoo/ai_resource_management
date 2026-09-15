"""신규: 월별 활동 비지도 클러스터링 (Montandon et al. 2019 방법론 적용)

Montandon et al., "Identifying Experts in Software Libraries and Frameworks
among GitHub Users" (2019)의 핵심 기법은 "고정 임계치가 아니라 비지도
클러스터링으로 고활동/저활동 집단을 나누고, 고활동 클러스터를 신뢰 가능한 양성
신호로 쓴다"는 것이다.

이 프로젝트는 spec.md 제약상 **동료(타인) 데이터를 모아 사람 간 클러스터링을 할
수 없다** (본인 범위 한정). 대신 같은 방법을 **한 사람의 활동을 월 단위로 쪼갠
시간축**에 적용한다: 본인의 여러 달을 각각 하나의 관측치로 보고 2-평균(k=2)
클러스터링해 "고활동 달 클러스터" vs "저활동 달 클러스터"를 고정 임계치 없이
나눈다. 이렇게 하면 (a) 원 논문의 클러스터링 기법을 그대로 재현하면서 (b) 지금까지
composite_signals.py가 하드코딩해 온 임계치를 데이터 기반으로 대체하고 (c) "지속적
저활동/고기여" 신호(1.6절)에 필요한 **추세(sustained)** 판단 근거를 제공한다.

외부 패키지 없이 표준 라이브러리만으로 1차원 특징(월별 커밋 수)에 대해 k=2
Lloyd's algorithm을 직접 구현한다.

사용 예:
    python3 monthly_activity_clusters.py --repo /path/to/repo --author "cheoljoo"
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict

from git_utils import iter_commits


def compute_monthly_commit_counts(repo: str, branch: str, author: str | None) -> dict[str, int]:
    commits = iter_commits(repo, branch)
    if author:
        commits = [c for c in commits if author in c.author_email or author in c.author_name]
    counter: Counter[str] = Counter()
    for c in commits:
        counter[c.dt.strftime("%Y-%m")] += 1
    return dict(sorted(counter.items()))


def kmeans_1d_k2(values: list[float], max_iter: int = 100) -> tuple[float, float, list[int]]:
    """1차원 k=2 k-means. 반환: (저활동 클러스터 중심, 고활동 클러스터 중심, 각 값의 클러스터 라벨(0=저/1=고))."""
    if len(values) < 2:
        # 관측치가 1개 이하면 클러스터를 나눌 수 없음 — 호출부에서 이 경우를 별도 처리해야 함.
        c = values[0] if values else 0.0
        return c, c, [0] * len(values)

    lo, hi = min(values), max(values)
    if lo == hi:
        return lo, hi, [0] * len(values)

    center_low, center_high = lo, hi
    labels = [0] * len(values)
    for _ in range(max_iter):
        new_labels = [
            0 if abs(v - center_low) <= abs(v - center_high) else 1
            for v in values
        ]
        if new_labels == labels and _ > 0:
            break
        labels = new_labels

        low_vals = [v for v, lab in zip(values, labels) if lab == 0]
        high_vals = [v for v, lab in zip(values, labels) if lab == 1]
        if low_vals:
            center_low = sum(low_vals) / len(low_vals)
        if high_vals:
            center_high = sum(high_vals) / len(high_vals)

    if center_low > center_high:
        center_low, center_high = center_high, center_low
        labels = [1 - lab for lab in labels]
    return center_low, center_high, labels


def compute_clusters(
    repo: str, branch: str, author: str | None
) -> dict:
    monthly = compute_monthly_commit_counts(repo, branch, author)
    months = list(monthly.keys())
    values = [float(v) for v in monthly.values()]

    if len(values) < 4:
        return {
            "monthly_commit_counts": monthly,
            "clustered": False,
            "reason": f"관측치(월)가 {len(values)}개뿐이라 클러스터링을 신뢰할 수 없음 (최소 4개월 권장)",
        }

    center_low, center_high, labels = kmeans_1d_k2(values)
    month_labels = dict(zip(months, labels))

    # 가장 최근 달부터 몇 달 연속으로 저활동 클러스터인지 계산 (경고 신호의 "지속성" 근거)
    consecutive_low_recent = 0
    for month in reversed(months):
        if month_labels[month] == 0:
            consecutive_low_recent += 1
        else:
            break

    consecutive_high_recent = 0
    for month in reversed(months):
        if month_labels[month] == 1:
            consecutive_high_recent += 1
        else:
            break

    return {
        "monthly_commit_counts": monthly,
        "clustered": True,
        "low_cluster_center": round(center_low, 2),
        "high_cluster_center": round(center_high, 2),
        "month_labels": month_labels,  # 0=저활동 클러스터, 1=고활동 클러스터
        "consecutive_low_months_recent": consecutive_low_recent,
        "consecutive_high_months_recent": consecutive_high_recent,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="분석할 git 저장소 경로")
    parser.add_argument("--branch", default="HEAD", help="분석 대상 브랜치")
    parser.add_argument("--author", default=None, help="특정 작성자(이름/이메일 일부)로 범위 제한")
    args = parser.parse_args()

    result = compute_clusters(args.repo, args.branch, args.author)

    print("# 월별 활동 비지도 클러스터링 (Montandon et al. 2019 방법론 적용, 시간축 버전)\n")
    if not result["clustered"]:
        print(f"⚠️ {result['reason']}")
        print(f"월별 커밋 수: {result['monthly_commit_counts']}")
        return

    print(f"저활동 클러스터 중심: {result['low_cluster_center']} 커밋/월")
    print(f"고활동 클러스터 중심: {result['high_cluster_center']} 커밋/월\n")
    print(f"{'month':<10} {'commits':>8} {'cluster':>10}")
    for month, count in result["monthly_commit_counts"].items():
        label = result["month_labels"][month]
        print(f"{month:<10} {count:>8} {'저활동' if label == 0 else '고활동':>10}")

    print(f"\n최근 연속 저활동 달 수: {result['consecutive_low_months_recent']}")
    print(f"최근 연속 고활동 달 수: {result['consecutive_high_months_recent']}")
    print(
        "\n※ 이 클러스터링은 사람 간 비교가 아니라 본인의 시간축 내 상대적 구분입니다"
        " (spec.md 범위 제약 — 동료 데이터 미사용). '저활동'은 역량 부족의 증거가 아니라"
        " 상대적으로 조용했던 달이라는 뜻일 뿐입니다 (developer_evaluation_metrics.md 1.5절)."
    )


if __name__ == "__main__":
    main()
