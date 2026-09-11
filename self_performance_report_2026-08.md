# 개인 워크퍼포먼스 리포트 (Self, 2026-08 기준) — 실제 데이터 검증 결과

> **범위**: 본인(cheoljoo.lee)의 작업 데이터만 수집·분석. 동료 데이터는 포함하지 않음.
> **목적**: [developer_evaluation_metrics.md](developer_evaluation_metrics.md)의 지표 정의가 실제 사내 시스템에서 값을 제대로 가져오는지 검증하고, 그 실측값으로 본인 워크퍼포먼스를 스스로 점검하기 위한 자료.
> **용도 제한**: 본 리포트는 자기 진단/회고용이며, 동료 평가나 인사 평가에 사용되지 않음 (문서 5장 "인사 평가 직접 연동 금지" 원칙 준수).

---

## 0. 데이터 수집 검증 결과 (실행 확인)

| 데이터 소스 | 접속 방식 | 조회 조건 | 실제 수집 건수 | 상태 |
| :--- | :--- | :--- | :--- | :---: |
| Jira (`jira.lge.com`) | REST API, `vspvs` 서비스 계정 인증(QCD_ENV DB에서 로드) | `(reporter = "cheoljoo.lee" OR assignee = "cheoljoo.lee") AND updated >= -180d` | **155건** | ✅ 실측 확인 |
| Gerrit (`vgit.lge.com/na`, `/as` 등 10개 서버) | REST API, 서버별 서비스 계정(HTTP Basic) | `owner:cheoljoo.lee@lge.com` (전체 서버, 페이지네이션) | **103건** (na 102 + as 1) | ✅ 실측 확인 |
| Local git (`~/code/ccr`) | 로컬 `git log` | author `cheoljoo.lee@lge.com` 계열 (charles.lee/Charles.Lee/cheoljoo.lee 별칭 포함) | **122 commits** / 21 merge | ✅ 실측 확인 |
| Local 소스 복잡도 (`~/code/ccr`, Python) | `ast` 정적 분석 | 전체 `.py` 파일 | 660개 함수 분석 | ✅ 실측 확인 |

> Gerrit `gpro`, `prosys` 서버는 인증 실패(401)로 건너뜀 — 해당 서버 접근 권한 별도 확인 필요.
> 사용한 스크립트: [scripts/dev_metrics](scripts/dev_metrics) 의 `gerrit_fetch.py`, `gerrit_metrics.py`, `jira_metrics.py`, `lead_time.py`, `focus_time.py`, `burnout_signals.py`, `complexity.py`.

### 0.1 재검증: "최근" 활동 여부 (사용자 지적 반영)

초안에서 Gerrit/`ccr` 데이터를 "실측 확인"이라고만 표시해 마치 최근 활동처럼 보일 수 있었다. 실제 타임스탬프를 다시 확인한 결과:

* **Gerrit**: owner:cheoljoo.lee@lge.com 로 잡히는 전체 103건 중 가장 최근 `updated` 시각은 **2025-04-16** (ABANDONED 처리된 tiger/build #1485527). 즉 **현재(2026-08-27) 기준 약 16개월간 Gerrit(vgit.lge.com 등 10개 서버)에는 신규/갱신 활동이 없음** — 사용자 지적이 맞다.
* **Local git `~/code/ccr`**: 모든 브랜치(`--all`) 통틀어 가장 최근 커밋은 **2026-06-26** — 현재 기준 약 2개월 전. 최근 몇 주 기준으로는 코드 커밋이 없는 것도 맞다 (단, `data/` 아래 미추적 산출물 CSV 다수 존재 — 도구는 계속 실행되고 있으나 코드 변경/커밋은 없었던 것으로 보임).
* **재확인**: `~/code` 하위 전체 로컬 저장소를 스캔해 실제로 최근 활동이 있는 곳을 찾음 — `llm_wiki`(158 commits, 2026-07-06~**2026-08-27 당일**), `sage-wiki`(122 commits, ~2026-08-27), `cheoljoo.github.io`(당일), `pvs_crawler`(2025-06~2026-08-14) 등. **즉 최근 실제 개발 활동은 Gerrit이 아닌 이런 개인 툴링/위키 저장소에서 이뤄지고 있음.**

→ 아래 2·3장의 "Local git" 지표는 `ccr`(과거 이력, tiger/Gerrit 연계 프로젝트) 대신 **`llm_wiki`(현재 실제로 활발한 저장소)** 데이터로 교체했다. Gerrit 기반 1·2장 지표는 여전히 유효한 실측값이지만 **모두 2025-04 이전 활동**이라는 점을 반드시 함께 읽어야 한다.

---

## 1. 품질 & 완성도 (Gerrit 기반, 실측 — ⚠️ 최근 활동 아님, 2020~2025-04 데이터)

* **Change 상태 분포**: MERGED 73건 / ABANDONED 29건 / NEW(진행중) 1건 (총 103건)
* **1.1 재작업률 근사치 (Patchset 수)**: 평균 **2.36개**, 중앙값 1개, 최대 14개
  * Patchset 5개 이상인 Change 12건 확인 (예: `tiger/build` #1465294 — 14 patchset, `#1427607` — 11 patchset). 문서 1.1의 "평균 7회 이상이면 초기 완성도 부족 신호"라는 기준선 대비 전반적으로 양호한 편.
* **변경 규모**: 총 insertion 94,805줄 / deletion 52,527줄, Change당 평균 insertion 920줄 (일부 대형 변경 포함 — 평균값 해석 시 주의)
* **작업 프로젝트 분포(상위)**: `tiger/utils/tidl` 19건, `tiger/build` 18건, `gm/con/linux/utils/libgmpal` 12건 등 31개 프로젝트에 분산

## 2. 개발 속도와 흐름

### 2-a. Gerrit 기반 (⚠️ 2020~2025-04 데이터, 최근 아님)

* **2.1 변경 리드 타임 (Gerrit, MERGED 기준)**: 평균 **94.5시간**, 중앙값 **19.1시간** — 대부분 단기간에 처리되나 소수 장기 지연 건이 평균을 끌어올림 (중앙값 참고 권장).
* **월별 Gerrit Change 생성 추이**: 2024-07 26건으로 최다. 2025-04 이후로는 활동 없음 (0.1절 참고).

### 2-b. Local git 기반 — `llm_wiki` (실제 최근 활동 저장소, 2026-07-06~2026-08-27)

* **2.1 변경 리드 타임 (merge commit 기준, 15건)**: 평균 **20.4시간**, 중앙값 **1.9시간**, 최대 91.4시간 — Gerrit 이력 대비 훨씬 빠른 회전(주로 개인 위키/툴링 저장소라 리뷰 대기 없이 즉시 병합되는 구조라서 직접 비교는 부적절).
* **1.2 단기 재수정(Re-fix) 빈도 (14일 창)**: `tooling/commands/wiki-log.md`, `Makefile` 등 자주 다루는 파일에서 짧은 주기의 재수정 다수 확인 (`fix:` 키워드 포함 커밋 존재) — 반복 개선형 워크플로우(문서/스킬 다듬기)로 해석됨.

## 3. 지속 가능성 및 웰빙 — `llm_wiki` 기준 (실제 최근 활동 저장소)

* **번아웃 신호 (야간 21시~07시 또는 주말 커밋 비율)**:

  | 계정 별칭 | 총 커밋 | 야간 비율 | 주말 비율 |
  | :--- | ---: | ---: | ---: |
  | cheoljoo.lee | 72 | 12.5% | 2.8% |
  | charles.lee | 85 | 5.9% | 8.2% |
  | cheojoo (오타 별칭) | 3 | 33.3% | 100.0% |

  → `ccr`(과거) 대비해서도 야간/주말 비율이 낮은 편. 다만 "cheojoo" 오타 별칭 3건은 표본이 작아 100% 주말이라는 수치를 과대 해석하지 않아야 함.
* **몰입 시간(Focus Time) 추정 (Inter-Event Gap, 120분 기준)**: 계정 별칭 합산 약 63개 세션, 총 추정 몰입시간 약 41시간(약 7주 기간) — 최근 활동이 실제로 존재함을 뒷받침.

> 참고용으로 `ccr` 저장소(과거 이력, 2020~2026-06)의 원래 수치는 부록에 남겨둔다: 커밋 122건, 번아웃 야간 5.9~37.5%/주말 0~12.5% (계정 별칭별), 몰입시간 합산 약 35.6시간.

## 4. 문제 정의 및 설계 역량 관련 참고 지표

* **Jira 이슈 유형 분포**: Story 117건, Sub-task 25건, Epic 4건, Task 3건 등. Story 비중이 커서 신규 기능 개발 위주 업무로 해석 가능 (단, Jira 자체는 "설계 명확성"을 판별하지 못함 — 문서 4.2 참고, 정성적 판단 필요).
* **Jira 상태 분포**: Resolved 119 / Open 12 / In Progress 9 / Closed 8 / Holding 7 — 정체(Holding/Open) 비중이 적어 흐름이 원활한 편.

---

## 5. 방법론적 한계 (반드시 함께 읽을 것)

1. **표본 범위 제한**: Local git 분석은 `llm_wiki`(최근)와 `ccr`(과거) 저장소 2개만 사용. 실제로는 여러 저장소에 걸쳐 작업하므로 이 리포트는 전체 활동의 일부만 반영한다.
2. **시스템별 최근성 편차**: 0.1절에서 확인된 대로 Gerrit/`ccr`은 최근(2025-04 이후/2026-06 이후) 활동이 없고, 실제 최근 작업은 `llm_wiki`등 개인 저장소에 있다. 즉 **이 리포트의 "품질/속도" 지표는 두 개의 서로 다른 시기·시스템을 섮은 것**이라서 단일 추세선으로 해석해서는 안 된다.
3. **Jira는 180일 창(window)만 조회**: 최근 6개월 데이터만 반영되어 장기 추세는 알 수 없음.
4. **Gerrit lead time의 `submitted` 필드 부재**: 이 조직의 Gerrit 응답에는 `submitted` 값이 비어 있어 `updated` 타임스탬프로 대체 계산함 — Gerrit 자체의 "최종 제출 시각"과 정확히 일치하지 않을 수 있음.
5. **Goodhart's Law 경고 (문서 1장)**: 위 수치(특히 Patchset 수, 리드 타임, 커밋 시각)를 단독 절대 지표로 사용해 스스로를 재단하지 말 것. 대규모 아키텍처 변경은 자연스럽게 Patchset이 많아지고, 야간 커밋은 유연근무의 결과일 수 있다.
6. **인사 평가 미사용**: 본 리포트는 자기 회고·병목 파악 용도로만 작성되었으며, 별도 동의·거버넌스 절차 없이 동료 평가나 인사자료로 전용해서는 안 된다.

---

## 6. AGILEDEV-1118 데이터 전용 종합 신호 실행 결과 (2026-09-10 추가)

`scripts/dev_metrics/composite_signals.py`(spec.md 완료조건 3·8, developer_evaluation_metrics.md
1.6절)를 본인 계정으로 실행한 결과다. **설문/자기보고 없이 시스템 메타데이터만 사용했다**(1.4절
데이터 우선 원칙). 아래 결과는 인사 평가 자료가 아니며, 자기 회고/병목 진단 용도로만 읽을 것.

```bash
cd scripts/dev_metrics
python3 composite_signals.py --repo ~/code/llm_wiki \
  --repos ~/code/llm_wiki ~/code/sage-wiki ~/code/cheoljoo.github.io ~/code/pvs_crawler ~/code/ccr \
  --author "cheoljoo" --raw
```

| 대항목 | 밴드 | 근거(원시 수치, `--raw`) |
| :--- | :--- | :--- |
| 1. 코드 품질 및 완성도 | 우수 | 커밋 206건, 확정적 재수정 5건, revert/hotfix 0건 |
| 2. 개발 속도와 흐름 | 우수 | merge 20건, 리드 타임 중앙값 0.94시간 |
| 3. 협업 및 팀 기여도 | 데이터 없음 | Gerrit/Jira API 미연결(이번 실행 범위 밖) |
| 4. 문제 정의/설계 역량 + 활동 폭·다양성 | 우수 | PoC 브랜치 0건, 실질 기여 저장소 5/5, 확장자(기술스택) 22종 |
| 5. 지속 가능성 및 웰빙 | 양호 | 커밋 204건, 야간 비율 7.4%, 주말 비율 5.9% |

* **지속적 고기여 인정 신호: 🟢 발생** — 3개 대항목이 "우수" 구간이며 품질 지표(재작업/변경실패율)도
  양호해서 발생 조건을 만족했다.
* **지속적 저활동 경고 신호: ⚪ 미발생** — "관찰 필요" 구간이 0개라 발생 조건(4개 이상)에 크게 못 미침.

**해석 시 주의(1.5절 비대칭 원칙 재확인)**: 위 "인정 신호"는 여러 독립 축(품질+속도+다양성)이 동시에
높다는 신뢰할 만한 양성 지표이지만, 그렇다고 "경고 신호가 없다"는 것이 "이 사람이 항상 문제 없다"는
뜻은 아니다 — 3.협업(코드 리뷰) 축은 이번 실행에서 아예 데이터가 없었으므로(Gerrit API 미연결) 전체
그림의 일부만 본 것이다. 반대로 만약 경고 신호가 떴더라도 그 자체를 역량 부족의 증거로 쓰면 안 되고
사람의 확인이 먼저다(Montandon et al. 2019, 근거는 `intents/2026-09-09-developer-expertise-grading/research/papers/montandon-identifying-experts-github.md` 참고).

### 6.1 방법론 보강 재실행 — 경험 원자(EA) + 월별 클러스터링 반영 (2026-09-10)

위 6장 실행은 Mockus & Herbsleb(2002)·Montandon et al.(2019)의 **결론만 원칙으로 인용**했을 뿐 실제
방법론은 구현에 없었다는 지적을 받아, `developer_evaluation_metrics.md` 1.7절에 따라 두 방법을 직접
구현(`experience_atoms.py`, `monthly_activity_clusters.py`)하고 `composite_signals.py`에 통합해
재실행했다.

```bash
python3 experience_atoms.py --repo ~/code/llm_wiki --author "cheoljoo"
python3 monthly_activity_clusters.py --repo ~/code/ccr --author "cheoljoo"
python3 composite_signals.py --repo ~/code/llm_wiki \
  --repos ~/code/llm_wiki ~/code/sage-wiki ~/code/cheoljoo.github.io ~/code/pvs_crawler ~/code/ccr \
  --author "cheoljoo" --raw
```

* **경험 원자(EA, Mockus & Herbsleb 2002 방법 그대로)** — `llm_wiki` 기준 총 EA 701개, 실질 경험
  임계치(EA≥5) 기준 breadth(폭) 13개 모듈, depth(깊이) 390 EA(최심 모듈 `log`). 대항목 4의 밴드
  산출 근거에 `ea_breadth_module_count`/`ea_depth_max`로 편입됨(대항목 4는 여전히 "우수" 유지).
* **월별 활동 클러스터링(Montandon et al. 2019 방법을 시간축에 적용)** — `llm_wiki`는 관측 월이
  3개뿐이라 클러스터링 미신뢰(4개월 미만) 처리됨. 이력이 긴 `ccr`로 별도 확인한 결과 저활동 클러스터
  중심 8.75건/월, 고활동 클러스터 중심 29.0건/월, **최근 2개월 연속 저활동 클러스터**로 판정 — 이
  클러스터링 결과가 실제로 존재한다면 "지속적 저활동 경고 신호"의 지속성(sustained) 조건 판단에
  쓰인다(현재 `llm_wiki` 기준 실행에서는 대항목 밴드 자체가 "관찰 필요" 0개라 경고 신호는 여전히
  미발생).
* **재확인**: 인정 신호(🟢 발생)·경고 신호(⚪ 미발생) 결론 자체는 기존과 동일 — 이번 보강은 "왜/어떻게"
  그 결론에 도달했는지의 근거를 논문 방법론에 맞게 더 촘촘하게 만든 것이다.

---

## 7. 재현 방법 (Reproducibility)

```bash
# 재검증: 어느 저장소가 실제로 최근 활동이 있는지 스캔
# (author에 자신의 git 이메일/이름 별칭을 모두 넣을 것)
for d in $(find ~/code -maxdepth 2 -name .git -type d); do
  repo=$(dirname "$d")
  last=$(git -C "$repo" log --all -i --author='cheoljoo.lee\|charles.lee' --format='%ad' --date=short -1)
  [ -n "$last" ] && echo "$last  $repo"
done | sort -r

# Jira (최근 180일, 본인 이슈만)
cd ~/code/_worklog
uv run python fetch_worklog.py \
  --jql='(reporter = "cheoljoo.lee" OR assignee = "cheoljoo.lee") AND updated >= -180d' \
  --dirname=/tmp/cheoljoo_jira_check --fileprefix=cj
uv run python process_worklog.py --dirname=/tmp/cheoljoo_jira_check --fileprefix=cj \
  --raw_csv=/tmp/cj_raw.csv --worklog_csv=/tmp/cj_worklog.csv

# Gerrit (본인 owner, 전체 서버)
cd ~/code/ai_resource_management/scripts/dev_metrics
python3 gerrit_fetch.py --owner cheoljoo.lee@lge.com --out /tmp/gerrit_self.json
python3 gerrit_metrics.py --in /tmp/gerrit_self.json

# Jira 지표 계산
python3 jira_metrics.py --raw-csv /tmp/cj_raw.csv --owner "cheoljoo.lee"

# Local git (llm_wiki 저장소 — 실제 최근 활동이 있는 저장소)
python3 lead_time.py --repo ~/code/llm_wiki
python3 focus_time.py --repo ~/code/llm_wiki
python3 burnout_signals.py --repo ~/code/llm_wiki
python3 refix_frequency.py --repo ~/code/llm_wiki --window-days 14

# Local git (ccr 저장소, 참고용 과거 이력)
python3 lead_time.py --repo ~/code/ccr
python3 focus_time.py --repo ~/code/ccr --author cheoljoo.lee
python3 burnout_signals.py --repo ~/code/ccr --author cheoljoo.lee
python3 complexity.py --path ~/code/ccr --threshold 15

# AGILEDEV-1118: 활동 폭/다양성 + 데이터 전용 종합 신호 (6장 결과 재현)
python3 activity_breadth.py --repos ~/code/llm_wiki ~/code/sage-wiki \
  ~/code/cheoljoo.github.io ~/code/pvs_crawler ~/code/ccr --author "cheoljoo"
python3 composite_signals.py --repo ~/code/llm_wiki \
  --repos ~/code/llm_wiki ~/code/sage-wiki ~/code/cheoljoo.github.io ~/code/pvs_crawler ~/code/ccr \
  --author "cheoljoo" --raw
```

> 원본 JSON/CSV는 개인 작업 상세 내용(티켓 제목, 커밋 메시지 등)을 포함하므로 `/tmp`에만 저장했고 이 저장소에는 커밋하지 않았다.
