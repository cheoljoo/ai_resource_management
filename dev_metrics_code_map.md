# 개발자 평가 메트릭 - 자동화 스크립트 매핑 (`scripts/dev_metrics/`)

[developer_evaluation_metrics.md](developer_evaluation_metrics.md)에서 **`✅ 즉시 가능`** (로컬 git 저장소만으로 코드가 바로 값을 산출할 수 있는 항목) 으로 표시된 소항목에 대해 실제 동작하는 Python 스크립트를 작성했다. 사내 Gerrit/Jira/Confluence/Teams API 연동이 필요한 `🔑 API 필요`, `❌ 불가` 항목은 이번에 코드화하지 않았다 (해당 시스템에 연결된 MCP/토큰이 없어 값을 가져올 수 없음).

모든 스크립트는 외부 패키지 없이 Python 표준 라이브러리와 `git` CLI만 사용하며, `--repo` 옵션으로 대상 저장소 경로를 지정해 **어떤 git 저장소에도** 재사용할 수 있다.

## 실행 방법

```bash
cd scripts/dev_metrics
python3 <script>.py --repo /path/to/target/repo [옵션들]
```

각 스크립트는 `python3 <script>.py --help`로 옵션을 확인할 수 있다.

## 코드 ↔ 문서 항목 매핑

| 문서 항목 | 스크립트 | Claude 직접 수집 가능 여부(문서 표기) | 무엇을 계산하는가 | 문서에 명시된 한계 |
| :--- | :--- | :--- | :--- | :--- |
| 1.2 단기 재수정(Re-fix) 빈도 | [refix_frequency.py](scripts/dev_metrics/refix_frequency.py) | ✅ 즉시 가능 (부분) | 파일별 커밋 이력을 시간순으로 정렬해, N일(기본 30일) 이내 재수정된 파일/커밋 쌍을 탐지. 커밋 메시지에 fix/bug/hotfix/issue 키워드가 있으면 "확정적 재작업"으로 구분 | Gerrit Change/Patchset 단위 메타데이터는 반영 못 함 (Gerrit API 필요) |
| 1.3 변경 실패율 (Hotfix/Revert) | [change_failure_signals.py](scripts/dev_metrics/change_failure_signals.py) | 🔑 API 필요 (부분 ✅) | `git revert` 커밋, hotfix/rollback 키워드 커밋, `hotfix/`·`revert-` 브랜치를 탐지 | 장애로 인한 롤백인지 기획 변경인지는 구분 불가 (Jira 장애 티켓 교차검증 필요) |
| 1.4 복잡도 대비 결함 밀도 | [complexity.py](scripts/dev_metrics/complexity.py) | 🔑 API 필요 (복잡도 산출만 ✅) | Python `ast` 모듈로 함수별 순환 복잡도(Cyclomatic Complexity)를 자체 계산 (SonarQube 등 외부 툴 불필요) | 실제 결함 수·도메인 난이도와 연결하려면 Jira 버그 데이터 필요. Python 파일만 지원 |
| 2.1 변경 리드 타임 | [lead_time.py](scripts/dev_metrics/lead_time.py) | ✅ 즉시 가능 (부분) | merge commit 기준으로, 병합된 브랜치의 가장 오래된 커밋 ~ merge 시각까지의 시간차를 계산 | Gerrit First-Upload 실제 시각 등은 Gerrit API 필요 |
| 2.2 몰입 시간 확보율 (Focus Time) | [focus_time.py](scripts/dev_metrics/focus_time.py) | ✅ Git 부분만 / ⏭️ Teams 제외 | 작성자별 커밋 타임스탬프 간격이 임계값(기본 120분) 이내면 하나의 Focus 세션으로 묶어 추정 몰입 시간 산출 (Inter-Event Gap 휴리스틱) | Teams 캘린더 기반 Inverse Calendar Block 분석은 범위 제외 |
| 4.1 선행 검증/PoC 수행 능력 | [poc_branch_history.py](scripts/dev_metrics/poc_branch_history.py) | ✅ 즉시 가능 (부분) | 브랜치별 최초/최근 커밋 시각, 커밋 수, base 브랜치 병합 여부 집계. `poc/`, `spike/`, `experiment/`, `prototype/` 접두사 브랜치를 PoC 후보로 표시 | Collab POC 보고서 존재 여부는 Confluence API 필요 |
| 5.1 번아웃 위험도 | [burnout_signals.py](scripts/dev_metrics/burnout_signals.py) | ✅ Git / 🔑 Jira / 🚫 Teams 정책상 영구 제외 | 작성자별 야간(기본 21시~07시)·주말 커밋 비율 집계 | 회의 시간 데이터는 회사 정책상 영구 조회 불가(developer_evaluation_metrics.md 1.2절). 평가가 아닌 웰빙 케어 알림 용도로만 사용 |
| 신규: 활동 폭/다양성 (6.3절) | [activity_breadth.py](scripts/dev_metrics/activity_breadth.py) | ✅ 즉시 가능 (로컬 다중 저장소) | 여러 저장소에 걸친 커밋·변경 라인 수·파일 확장자(기술 스택) 다양성 집계. 저장소당 최소 변경 라인 수 임계치로 "사소한 커밋 흩뿌리기" 게이밍 방지(1.3절) | GitHub/Gerrit/Jira까지 포함한 전사 범위 다양성은 API 필요(6.3절) |
| 신규: 경험 원자(EA) (4.4/1.7절) | [experience_atoms.py](scripts/dev_metrics/experience_atoms.py) | ✅ 즉시 가능 | Mockus & Herbsleb(2002) 방법론 그대로 — 커밋이 건드린 파일을 (모듈, 기술스택, 변경목적) 3축으로 분해해 EA로 누적 집계, 전문성의 폭(breadth)·깊이(depth) 산출 | EA는 "불완전하지만 합리적인" 척도(원 논문 표현) — 변경량이 곧 전문성의 질을 보장하지 않음 |
| 신규: 월별 활동 클러스터링 (1.6/1.7절) | [monthly_activity_clusters.py](scripts/dev_metrics/monthly_activity_clusters.py) | ✅ 즉시 가능 | Montandon et al.(2019)의 비지도 클러스터링 방법을 시간축에 적용 — 본인의 월별 커밋 수를 표준 라이브러리 k=2 k-means로 고활동/저활동 클러스터로 분리, 두 신호의 "지속성(sustained)" 판단 근거 제공 | 사람 간 비교는 spec.md 범위 밖이라 시간축으로만 적용. 관측치(월) 4개 미만이면 클러스터링 미신뢰 처리 |
| 신규: 종합 로직 (spec.md 완료조건 3·8) | [composite_signals.py](scripts/dev_metrics/composite_signals.py) | ✅ 즉시 가능 (위 스크립트들을 조합) | 5대 대항목별 밴드(관찰 필요/양호/우수/데이터 없음)를 산출하고, EA·월별 클러스터링 결과를 반영해 **지속적 고기여 인정 신호**·**지속적 저활동 경고 신호**(1.6절) 두 가지를 계산. 최소 3개 대항목 데이터 가드레일, 단일 지표 금지, 트리거일 뿐이라는 경고 문구, 클러스터링 기반 지속성 검증 포함 | 3.협업(코드 리뷰) 대항목은 Gerrit API 없이는 항상 "데이터 없음" — 밴드 임계치(리드타임 등)는 1차 하드코딩(실측 데이터로 추후 보정 필요, 클러스터링으로 대체 가능한 부분은 이미 대체함) |
| (공통 유틸) | [git_utils.py](scripts/dev_metrics/git_utils.py) | - | 위 스크립트들이 공유하는 `git log`/`git branch` 파싱 헬퍼 (`Commit` dataclass, `iter_commits`, `list_branches`, `default_branch`) | - |

## 코드화하지 않은 항목과 이유

문서에서 `🔑 API 필요`(수집 자체가 사내 API 필요) 또는 `❌ 불가`(정성적 판단 영역)로 표기된 항목은 이번에 스크립트를 만들지 않았다:

* **1.1 재작업률(Patchset 수), 2.3 WIP 관리, 3.2 지식 자산화** — Gerrit/Jira/Confluence REST API 및 인증 토큰이 있어야 값을 가져올 수 있음.
* **3.1 코드 리뷰 기여도** — 리뷰 코멘트 원문 자체를 Gerrit API로 가져와야 함 (원문만 확보되면 이후 LLM 시맨틱 분류는 가능).
* **3.3 블로커 해결/멘토링, 4.2 요구사항 분석, 4.3 오버엔지니어링 지양** — 정성적 판단 영역이라 애초에 코드/API로 산출 불가.
* **5.2 주도적 개선(Post-mortem)** — Collab/Jira API 필요.

## 검증 방법

각 스크립트는 이 저장소([ai_resource_management](.))와 히스토리가 풍부한 외부 저장소(`yt-dlp`)를 대상으로 실행해 정상 동작을 확인했다. 예:

```bash
python3 scripts/dev_metrics/lead_time.py --repo /path/to/yt-dlp --top 5
python3 scripts/dev_metrics/complexity.py --path /path/to/yt-dlp/yt_dlp/utils
```

## 추가 (2차 작업): Gerrit/Jira API 연동 스크립트 — 실제 사내 시스템 데이터로 검증 완료

위 "코드화하지 않은 항목"의 일부(1.1 재작업률, 2.1 리드 타임의 Gerrit 시각, Jira 이슈 분포 등)를 실제 사내 Gerrit/Jira REST API로 조회하는 스크립트를 추가로 작성하고, 본인(cheoljoo.lee) 계정 범위로 실행해 실제 값이 정상적으로 반환되는지 확인했다. 결과와 재현 방법은 [self_performance_report_2026-08.md](self_performance_report_2026-08.md) 참고.

* [scripts/dev_metrics/gerrit_fetch.py](scripts/dev_metrics/gerrit_fetch.py) — 여러 Gerrit 서버(`~/code/ccr/global_variables.py`의 자격증명, 저장소에는 포함되지 않음)에서 `owner:` 기준으로 Change 목록을 페이지네이션 조회. 자격증명은 리포지토리 밖 파일에서 동적으로 로드하며 하드코딩하지 않음.
* [scripts/dev_metrics/gerrit_metrics.py](scripts/dev_metrics/gerrit_metrics.py) — `gerrit_fetch.py` 결과 JSON을 입력받아 1.1 재작업률(Patchset 수 분포), 상태 분포, 2.1 리드 타임(Gerrit `created`~`updated`), 변경 규모, 프로젝트별 분포를 계산.
* [scripts/dev_metrics/jira_metrics.py](scripts/dev_metrics/jira_metrics.py) — 기존 `~/code/_worklog` 도구로 수집한 Jira CSV를 입력받아 상태/이슈타입/우선순위 분포와 월별 추이를 계산.
* `focus_time.py`, `burnout_signals.py`에 `--author` 옵션을 추가해 특정 작성자로 범위를 좁혀 자기 진단 목적으로 사용할 수 있게 함.

## 추가 (3차 작업, AGILEDEV-1118): 활동 폭/다양성 신규 지표 + 종합 로직 (데이터 우선 원칙)

2026-09 사용자 결정(회사 모니터링 정책, 데이터 우선 원칙, 데이터 기반 극단값 해석의 비대칭 원칙 —
[developer_evaluation_metrics.md](developer_evaluation_metrics.md) 1.2~1.6절, [intents/2026-09-09-developer-expertise-grading/spec.md](intents/2026-09-09-developer-expertise-grading/spec.md) 참고)에
따라 아래 두 스크립트를 추가했다. 설문/자기보고는 사용하지 않으며, 시스템 메타데이터만 입력으로 받는다.

* [scripts/dev_metrics/activity_breadth.py](scripts/dev_metrics/activity_breadth.py) — 여러 로컬 git 저장소에
  걸친 커밋/변경 라인 수/파일 확장자 다양성을 집계해 원 티켓의 "얼마나 많은 분야에서 활동하는가" 요구에
  대응한다. 본인(cheoljoo.lee) 계정으로 5개 실 저장소(`llm_wiki`, `sage-wiki`, `cheoljoo.github.io`,
  `pvs_crawler`, `ccr`)를 대상으로 실행해 정상 동작 확인 — 5개 저장소 모두 임계치(20줄) 이상 실질
  기여로 인정되었고, 22개 서로 다른 파일 확장자(기술 스택)가 확인됨.
* [scripts/dev_metrics/composite_signals.py](scripts/dev_metrics/composite_signals.py) — 위 스크립트들을
  오케스트레이션해 5대 대항목 밴드 + 지속적 고기여 인정 신호/지속적 저활동 경고 신호를 산출. 같은 5개
  저장소·본인 계정으로 실행한 결과, "고기여 인정 신호" 발생(3개 대항목 우수 + 품질 지표 양호), "경고
  신호"는 미발생(관찰 필요 0개)을 확인 — 실행 결과 예시는
  [self_performance_report_2026-08.md](self_performance_report_2026-08.md)의 "AGILEDEV-1118 데이터
  전용 종합 신호 실행 결과" 절 참고.

## 추가 (4차 작업, AGILEDEV-1118): 두 논문의 방법론 직접 적용 (결론 인용에서 방법 채택으로)

3차 작업까지는 Mockus & Herbsleb(2002)·Montandon et al.(2019)의 **결론**만 원칙 근거로 인용하고
실제 방법론은 구현하지 않았다는 지적을 받아, 아래 두 스크립트로 방법론 자체를 재현했다
(developer_evaluation_metrics.md 1.7절 참고).

* [scripts/dev_metrics/experience_atoms.py](scripts/dev_metrics/experience_atoms.py) — Mockus &
  Herbsleb의 "경험 원자(Experience Atom)" 개념을 그대로 구현. 커밋이 건드린 파일을 (모듈, 기술스택,
  변경목적) 3축으로 분해해 누적 집계하고, 전문성의 폭(breadth)·깊이(depth)를 구분해 산출. `llm_wiki`
  기준 실행 검증: EA 701개, breadth 13개 모듈, depth 390(최심 모듈 `log`).
* [scripts/dev_metrics/monthly_activity_clusters.py](scripts/dev_metrics/monthly_activity_clusters.py) —
  Montandon et al.의 비지도 클러스터링 방법을, 사람 간 비교가 금지된 이 프로젝트 제약에 맞춰 **본인의
  월별 활동을 시간축으로 클러스터링**하는 방식으로 재구성. 표준 라이브러리만으로 1차원 k=2 k-means를
  직접 구현. `ccr` 기준 실행 검증: 저활동 클러스터 중심 8.75건/월, 고활동 클러스터 중심 29.0건/월,
  최근 2개월 연속 저활동 클러스터로 판정.
* `composite_signals.py`를 위 두 스크립트와 통합: 대항목 4 밴드 산출에 EA breadth/depth를 반영하고,
  두 종합 신호(인정/경고)의 "지속성(sustained)" 조건을 월별 클러스터링 결과(최근 연속 고활동/저활동
  개월 수)로 실제 검증하도록 변경 — 이전에는 단일 시점 스냅샷만으로 판단했던 부분을 보완.

## 추가 (5차 작업, AGILEDEV-1118): 전문가 파인더(Expert Finder) POC — AI Flywheel 8단계(인접 확장)

PwC GenAI Flywheel 진단(plan.md 참고)에서 식별한 "가장 유력한 다음 단계"를 PoC로 구현했다. **이
항목만 spec.md "범위 밖" 절의 명시적 예외**로, 저장소의 모든 기여자(본인 외 타인 포함) 데이터를
사용한다 — 공유 저장소의 이미 공개된 git log를 라우팅 목적으로만 쓰는 것으로 한정.

* [scripts/dev_metrics/expert_finder.py](scripts/dev_metrics/expert_finder.py) — `experience_atoms.py`의
  EA 방법을 저장소 전체 기여자에게 적용해 "이 모듈은 누구에게 물어볼까"를 순위로 보여준다. **PoC
  범위 제약(2026-09-11 사용자 결정): 최근 14일(2주)치 커밋만 사용** — 전체 이력 확장은 이 PoC 결과를
  보고 별도 판단. 다중 기여자 실 저장소 `pvs_crawler`(4명, 86 커밋/14일)로 실행 검증 — 모듈별 1순위
  기여자와 특정 모듈(`SWPMUtil/sage`) 조회 모두 정상 동작 확인.

## 추가 (6차 작업, AGILEDEV-1118): AI Flywheel 4·7·8단계 실행 (2026-09-11)

* [scripts/dev_metrics/github_activity.py](scripts/dev_metrics/github_activity.py) — **8단계(인접
  확장)**. `gh` CLI(이미 인증된 세션)로 GraphQL `contributionsCollection`을 조회해 6.3절의 GitHub
  활동 폭/다양성 확장을 실제로 구현. 본인(cheoljoo) 계정으로 실행 검증: 총 커밋 기여 184건, 실질
  기여 저장소 15개, 언어 3종.
* [scripts/dev_metrics/run_history.py](scripts/dev_metrics/run_history.py) — **7단계(배포·테스트·
  학습 루프)**. `composite_signals.py --log-history` 실행마다 원시 근거치를 로컬 JSON Lines로
  누적하고, 샘플이 충분하면(기본 5회) 75번째 백분위 기반 임계치 재보정안을 제안. 5개 저장소로 실행
  검증 완료 — 예: 1.2(재수정 비율) 현재 임계치 0.15 vs 실측 75백분위 0.31.
* **4단계(파운데이션 모델/아키텍처)는 코드 변경 없이 결정 문서화만 진행** —
  `developer_evaluation_metrics.md` 1.8절 참고. 현재 아키텍처(Claude Code + 결정론적 Python
  스크립트, LLM 추론 없음)를 PoC 단계 공식 아키텍처로 채택, 정식 스케줄/다인원 확장 시 재검토.
