# 개발자 평가 메트릭 - 자동화 스크립트 매핑 (`scripts/dev_metrics/`)

[developer_evaluation_metrics.md](developer_evaluation_metrics.md)에서 **`✅ 즉시 가능`** (로컬 git 저장소만으로 코드가 바로 값을 산출할 수 있는 항목) 으로 표시된 소항목에 대해 실제 동작하는 Python 스크립트를 작성했다. 사내 Gerrit/Jira/Confluence/Teams API 연동이 필요한 `🔑 API 필요`, `❌ 불가` 항목은 이번에 코드화하지 않았다 (해당 시스템에 연결된 MCP/토큰이 없어 값을 가져올 수 없음).

모든 스크립트는 외부 패키지 없이 Python 표준 라이브러리와 `git` CLI만 사용하며, `--repo` 옵션으로 대상 저장소 경로를 지정해 **어떤 git 저장소에도** 재사용할 수 있다.

## 0. 브랜치별 작업 요약 (병합 후 정리, 2026-09-15)

두 개의 독립된 intent 브랜치가 `main`에 병합됐다(`5a8b675`, `55299f1`). 둘은 **목적이 다르다** — 아래를
먼저 읽고 어느 쪽 스크립트/문서를 봐야 하는지 파악할 것. 자세한 배경은 각 intent 문서(intent/spec/plan)
참고, 리서치 원본은 바로 아래 링크로 접근한다.

| | **AGILEDEV-1118** — 개인 진단 프로필 | **AGILEDEV-1132** — 전문가 파인더 (Expert Finder) |
| :--- | :--- | :--- |
| 브랜치 | `intent/2026-09-09-developer-expertise-grading` | `intent/2026-09-11-expert-finder` (전자에서 분기) |
| intent 문서 | [intent.md](intents/2026-09-09-developer-expertise-grading/intent.md) · [spec.md](intents/2026-09-09-developer-expertise-grading/spec.md) · [plan.md](intents/2026-09-09-developer-expertise-grading/plan.md) | [intent.md](intents/2026-09-11-expert-finder/intent.md) · [spec.md](intents/2026-09-11-expert-finder/spec.md) · [plan.md](intents/2026-09-11-expert-finder/plan.md) |
| 범위 | **본인(cheoljoo.lee) 범위 한정.** "등급"이 아니라 5대 대항목 다차원 프로필 + 양극단만 명시적 신호(지속적 고기여 인정/저활동 경고)로 분리(D안). | **타인 데이터 예외 허용**(라우팅 목적 한정) — "회사 안의 어떤 사람이 전문가인지"를 정성 평가 없이 데이터만으로 식별. |
| 핵심 산출 스크립트 | `composite_signals.py`(종합 프로필), `activity_breadth.py`, `monthly_activity_clusters.py`, `run_history.py`, `github_activity.py`, `experience_atoms.py`(공용) | `expert_finder.py`, `gerrit_signal.py`, `gitlab_signal.py`, `github_signal.py`, `jira_confluence_signal.py`, `combine_expert_signals.py` |
| Make 타겟 | `make profile` / `activity-breadth` / `monthly-clusters` / `run-history` / `github-activity` (위 "(A)" 그룹) | `make expert-finder` / `gerrit` / `gitlab` / `github` / `jira-confluence` / `combine` / `all` (위 "(B)" 그룹) |
| 문서 반영처 | `developer_evaluation_metrics.md` 1.2~1.9절, 대항목 1~5, 4.4절(활동 폭/다양성) | `developer_evaluation_metrics.md` 6.6절(POC 요약), 8장(5개 소스 결합 상세) |
| 리서치 원본 | [research/](intents/2026-09-09-developer-expertise-grading/research/) — 빅테크 4개사 사례([company-practices.md](intents/2026-09-09-developer-expertise-grading/research/company-practices.md)), 논문 11편([papers/README.md](intents/2026-09-09-developer-expertise-grading/research/papers/README.md) 인덱스), AI Flywheel 진단([pwc-genai-flywheel.md](intents/2026-09-09-developer-expertise-grading/research/pwc-genai-flywheel.md)), 유스케이스 우선순위 비교([usecase-portfolio-comparison.md](intents/2026-09-09-developer-expertise-grading/research/usecase-portfolio-comparison.md)) | (별도 리서치 없음 — AGILEDEV-1118의 리서치, 특히 Mockus & Herbsleb 2002·Montandon et al. 2019 두 편을 그대로 이어받음) |

**병합 중 발견·수정한 버그 (2026-09-15)**: 두 브랜치가 `experience_atoms.py`를 각자 수정하면서 AGILEDEV-1132
쪽에서 `summarize_breadth_depth()` 함수를 `breadth_depth()`로 이름·시그니처를 바꿨는데, AGILEDEV-1118의
`composite_signals.py`는 옛 이름/시그니처를 그대로 호출하고 있어 병합 후 `ImportError`로 깨져 있었다
(`make profile` 등 (A) 그룹 전체가 실행 자체가 안 됐음 — 테스트 스위트에는 이 통합 경로에 대한 커버리지가
없어서 `make test-*`로는 못 잡혔다). `compute_experience_atoms()`의 인자 순서(`(repo, branch, author)`
→ `(repo, author, module_depth, branch=...)`)도 함께 바뀐 것까지 반영해 `composite_signals.py`를
새 API에 맞게 고쳤다 — 수정 후 `make profile`/`activity-breadth`/`monthly-clusters`/`run-history` 4개
타겟 모두 실제 저장소로 재검증 완료.

## 실행 방법

**2026-09-15 추가:** 전문가 파인더의 Jira·Confluence 자동 수집은
[jira_confluence_signal.py](scripts/dev_metrics/jira_confluence_signal.py)가 담당한다.
이 수집기는 예외적으로 `requests`/`python-dotenv`를 사용하며 `uv run`이 의존성을 준비한다.
환경설정·집계 의미·Makefile 사용법은 [수집기 안내](scripts/dev_metrics/jira_confluence_signal.md) 참고.

Gerrit은 [gerrit_signal.py](scripts/dev_metrics/gerrit_signal.py)가 owner 외에 리뷰 투표,
메시지·공개 댓글 메타데이터, MERGED 상태와 실제 submitter를 수집한다.
조회 상한과 집계 의미는 [Gerrit 수집기 안내](scripts/dev_metrics/gerrit_signal.md) 참고.

GitLab MR과 GitHub PR의 리뷰·댓글·병합·실제 병합자 메타데이터는
[MR/PR 수집기 안내](scripts/dev_metrics/mr_pr_signal.md) 참고. Make 실행과 테스트는
모두 `uv`를 사용하며 결합 리포트에는 공급자별 MR/PR 표로 표시한다.

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
| 신규: 테스트 충분성 (1.7절, A4) | [test_adequacy.py](scripts/dev_metrics/test_adequacy.py) | ✅ 즉시 가능 | 커밋이 프로덕션 코드를 건드릴 때 테스트 코드도 함께 바뀌었는지 비율로 집계 | 커버리지 도구(coverage.py 등) 실행은 범위 밖 — 파일 동반 여부만 판별 |
| 신규: 리뷰 코멘트 품질 (3.1절, A1) | [review_quality_signal.py](scripts/dev_metrics/review_quality_signal.py) | 🔑 API 필요 (수집) / ✅ 즉시 가능 (메타데이터 분석) | Gerrit 코멘트의 라인단위 여부·후속 스레드(reply) 여부를 메타데이터만으로 집계 | "구체성"(코드 인용 등)은 코멘트 본문이 필요한데 `gerrit_signal.py`가 본문을 애초에 수집하지 않도록 설계돼 있어(7장) 판별 불가 — 별도 결정 필요 |
| 신규: 크로스팀 리뷰 참여 (6.4절, A2) | [cross_team_review_signal.py](scripts/dev_metrics/cross_team_review_signal.py) | 🔑 API 필요 | Gerrit change의 owner/vote 정보로 "본인 오너 프로젝트 vs 리뷰한 프로젝트" 교차 비율 계산 | 작은 표본에서는 교차율이 과대평가될 수 있음(전체 이력 재실행 권장) |
| 신규: Jira 교차 프로젝트 + Confluence 양방향 신호 (6.5절, A2/A3) | [jira_confluence_expansion.py](scripts/dev_metrics/jira_confluence_expansion.py) | 🔑 API 필요 (`.env` PAT — mcp-atlassian 불필요) | Jira 담당 이슈의 프로젝트별 분포로 "주 프로젝트 외 참여 비율" 계산, Confluence는 본인이 만들지 않은 페이지에 남긴 코멘트 수 계산 | Confluence 쪽은 코멘트마다 페이지 이력 조회가 추가로 필요해 `--max-comments-per-person`으로 표본 제한 |

## 코드화하지 않은 항목과 이유

문서에서 `🔑 API 필요`(수집 자체가 사내 API 필요) 또는 `❌ 불가`(정성적 판단 영역)로 표기된 항목은 이번에 스크립트를 만들지 않았다:

* **1.1 패치셋 패턴, 2.3 WIP 관리, 3.2 지식 자산화** — Gerrit/Jira/Confluence REST API 및 인증 토큰이 있어야 값을 가져올 수 있음.
* **3.1 코드 리뷰 기여도** — 리뷰 코멘트 원문 자체를 Gerrit API로 가져와야 함 (원문만 확보되면 이후 LLM 시맨틱 분류는 가능).
* **3.3 블로커 해결/멘토링, 4.2 요구사항 분석, 4.3 오버엔지니어링 지양** — 정성적 판단 영역이라 애초에 코드/API로 산출 불가.
* **5.2 주도적 개선(Post-mortem)** — Collab/Jira API 필요.

## 3차 작업: Gerrit 리뷰/코드 품질 심화 항목 (2026-09-07 반영, 스크립트 미작성)

사용자 피드백("Gerrit 하나를 보더라도 리뷰 내용·Patchset 간격·REQ/SDD 매핑·Bulk 여부·코드 내 설명까지
봐야 진짜 일을 제대로 하는지 알 수 있다")을 반영해 [developer_evaluation_metrics.md](developer_evaluation_metrics.md)에
1.5(개정)·1.8·1.9·1.10, 3.1(개정)을 추가/보강했다. 이번에는 **문서만 갱신**했고 스크립트는 아직 작성하지
않았다 — 항목별 착수 우선순위와 이유는 아래와 같다:

| 문서 항목 | Claude 직접 수집 가능 여부(문서 표기) | 스크립트화 난이도 | 비고 |
| :--- | :--- | :--- | :--- |
| 1.9 변경 방식(세밀 vs Bulk) | ✅ 즉시 가능 | **낮음** — 로컬 git diff의 hunk 개수/블록 크기 분포만 있으면 됨. 기존 `refix_frequency.py`와 유사하게 `git diff`/`git show` 파싱으로 바로 구현 가능 | **가장 먼저 스크립트화할 후보** |
| 1.10 소스 내 설명/추적성 주석 | ✅ 즉시 가능 | **낮음** — diff에서 추가된 라인 중 주석 비율, 정규식(`AGILEDEV-\d+` 등) 매칭은 표준 라이브러리만으로 구현 가능 | 1.9와 함께 스크립트화 용이 |
| 1.5 REQ/SDD↔코드 매핑 | 🔑 수집(Jira/Confluence API) / ✅ 매칭분석(LLM) | **중간** — 문서 원문 수집은 API 필요하지만, 일단 REQ/SDD 텍스트와 diff를 파일로 준비해주면 매칭 자체는 스크립트가 아니라 Claude가 그 자리에서 직접 분석 가능(별도 파이썬 스크립트 불필요) | 자동화 대상이 "스크립트"가 아니라 "LLM 프롬프트"에 가까움 |
| 1.8 리뷰 피드백 반영률 | 🔑 수집(Gerrit API) / ✅ 반영분석 | **중간** — Gerrit 코멘트+Patchset diff를 JSON으로 확보하면(`gerrit_fetch.py` 확장), 코멘트 위치와 다음 Patchset diff를 대조하는 로직은 스크립트화 가능. "취지가 반영됐는지"의 최종 판단은 LLM 보조 필요 | `gerrit_fetch.py`에 코멘트 조회 기능 추가가 선행 조건 |
| 3.1 코드 리뷰 기여도(개정) | 🔑 수집 / ✅ 분석 | 위 1.8과 동일 선행 조건 | 라인단위 코멘트 비율·구체성 판별은 코멘트 원문 확보 후 LLM으로 |

## 4차 작업: SMILE 플랫폼 발견 — 1.5/1.7/3.1의 스크립트화 계획 보류 (2026-09-07)

Collab SAAD 스페이스의 [SMILE User Guide](http://collab.lge.com/main/spaces/SAAD/pages/3800498513/)와
[Release Notes](http://collab.lge.com/main/spaces/SAAD/pages/3815244051/)(v1.0.0-preview, 2026-09-04)를
원문으로 확인한 결과, 사내에 이미 **SMILE**(커밋/MR 단위 AI 코드 변경 영향 분석 플랫폼)이 존재하며
Requirement 추적(PRD/SRS/FBS/UI 자동 매칭), Code Review(Critical/Warning/Info 등급), Unit/System Test
자동 생성·검증(Pass/Fail/Unverified/Out of Scope/Existing Coverage)을 이미 제공하고 있음을 확인했다.

이에 따라 바로 위 "3차 작업"에서 **1.5(REQ/SDD 매핑)·1.7(테스트 충분성)·3.1(코드 리뷰 기여도)를 커스텀
스크립트/LLM 프롬프트로 직접 구현하려던 계획은 보류**한다 — SMILE이 이미 같은 결과를 구조화된 형태로
산출하고 있다면, 직접 만드는 대신 SMILE의 API(`POST /api/analyses` 등, API Key + curl 연동)를 통해 그
결과를 가져오는 것이 우선순위가 높다. 자세한 배경은 [developer_evaluation_metrics.md 5장](developer_evaluation_metrics.md#5-smile-플랫폼-활용-방안-2026-09-신규-반영) 참고.

**다음 단계로 확인이 필요한 것** (아직 스크립트/연동 작업 착수 전):

1. ✅ **[절차 확인, 2026-09-07]** SMILE API Key 발급 절차 확인 완료 — [API 기반 분석 연동](http://collab.lge.com/main/spaces/SAAD/pages/3789454123/)
   원문을 조회함. 절차: SMILE 웹 UI 로그인 → 설정 → `API Keys` → 이름/만료 지정 → 발급 → 평문 키(`smile_...`)를
   **그 순간에만** 복사 가능. 추가로 계정에 **SAVE Key**가 선등록돼 있어야 하며(`설정 → 연동 API Keys`),
   없으면 모든 요청이 `400 save_key_required`로 거부됨. 자세한 내용은
   [developer_evaluation_metrics.md 5.4](developer_evaluation_metrics.md#54-api-key-발급-절차-2026-09-07-확인--api-기반-분석-연동-원문) 참고.
   * **🚧 [시도, 2026-09-07 16:xx KST] 실제 발급 시도 — SMILE 점검 중으로 중단.** `../headless-browser-with-ai`의
     `scripts/steel_browser.sh`(self-host Steel Docker, CDP로 AI가 DOM 조작)로 `https://smile.aise.lge.com`을
     열고, `.env`의 `LGEP_ID`/`LGEP_PASSWORD`로 SEL SSO(Keycloak, `sso.sel.lge.com`) 로그인 폼(`#username`,
     `#password`, `#kc-login`)을 채워 제출 → **로그인 자체는 성공**(SMILE 홈으로 리다이렉트, 우측 상단에
     로그인 사용자 아바타 표시됨). 다만 SMILE이 **서비스 점검 중**(점검 시작 2026-09-08 01:30 ~ 종료
     2026-09-08 08:59, 한국시)이라 설정 화면에 진입할 수 없어 API Key 발급까지는 못 감. 컨테이너는 정리
     (`stop`)했음 — **점검 종료(2026-09-08 09시 이후) 후 같은 절차로 재시도 필요**.
   * **확인된 것**: 이 SSO는 표준 Keycloak 로그인 폼이라 자격증명만 있으면 브라우저 자동화(CDP)로 로그인
     자체는 문제없이 통과된다. 즉 "Claude가 로그인은 절대 못 한다"는 이전 판단은 **틀렸음** — 로그인은
     자동화 가능했고, 이번에 막힌 것은 순전히 SMILE 서비스 자체의 점검 스케줄 때문.
   * **비밀번호 노출 방지**: 스크립트(`sso_login.py`)는 `.env`에서 읽은 비밀번호를 CDP `Runtime.evaluate`
     파라미터로만 전달했고, 어떤 로그·스크린샷·파일에도 평문으로 남기지 않았다(스크린샷은 로그인 완료
     후의 화면만 캡처).
2. SMILE API로 **과거 이력(본인이 이미 작업한 커밋/MR)까지 소급 조회**가 가능한지, 아니면 신규 분석
   요청만 가능한지 — 확인된 `POST /api/analyses`는 두 리비전(base/change) 간 diff를 **그때그때 새로
   생성**하는 방식이라, 이미 분석된 적 없는 과거 커밋은 소급 분석 시 비용/시간이 다시 든다. 목록 조회
   (listing analyses) 엔드포인트가 있다는 언급은 있으나 상세 스펙은 이번 페이지에 없어 **여전히 미확인**
   — 실제 키를 받으면 1건 시험 호출로 확인.
3. 🔴 **[확인 완료, 2026-09-08 — 결과: 미등록]** 이 저장소(`ai_resource_management`)를 포함해 실제 분석
   대상 저장소들이 SMILE `Project Settings`에 PRD/SRS/FBS/UI/Test Case 문서 링크와 함께 등록되어 있는지
   확인한 결과, **"VS" 프로젝트용으로 SMILE에 아무것도 설정된 것이 없다**(사용자 확인). 즉 지금 시점에는
   SMILE을 통한 1.5/1.7/3.1 대체·보강이 **적용 불가** — 등록(저장소 연결 + 문서 링크 등록)이 선행돼야
   하며, 그 전까지는 기존 커스텀 방식(1.5/1.7/3.1의 로컬 git/LLM 기반 접근)을 그대로 써야 한다. 이 항목이
   이번 SMILE 조사에서 **가장 중요한 결론**이다 — API Key를 발급받는다 해도 프로젝트 미등록 상태면 의미
   있는 분석 결과를 가져올 수 없다.
4. 위 3번의 등록 작업이 끝나면 `scripts/dev_metrics/smile_fetch.py`(가칭)를 `gerrit_fetch.py`와 같은
   패턴으로 추가해, SMILE 분석 결과 JSON을 1.5/1.7/3.1 지표로 변환하는 스크립트를 작성한다.

**1.9(변경 방식 세밀 vs Bulk), 1.10(소스 내 추적성 주석)은 SMILE과 무관하게 여전히 로컬 git만으로 즉시
스크립트화 가능**하므로 이 계획에 영향받지 않는다 — 우선순위 그대로 유지.

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

## 추가 (5차 작업, AGILEDEV-1118): 활동 폭/다양성 신규 지표 + 종합 로직 (데이터 우선 원칙)

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

## 추가 (6차 작업, AGILEDEV-1118): 두 논문의 방법론 직접 적용 (결론 인용에서 방법 채택으로)

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

## 추가 (7차 작업, AGILEDEV-1118): 전문가 파인더(Expert Finder) POC — AI Flywheel 8단계(인접 확장)

PwC GenAI Flywheel 진단(plan.md 참고)에서 식별한 "가장 유력한 다음 단계"를 PoC로 구현했다. **이
항목만 spec.md "범위 밖" 절의 명시적 예외**로, 저장소의 모든 기여자(본인 외 타인 포함) 데이터를
사용한다 — 공유 저장소의 이미 공개된 git log를 라우팅 목적으로만 쓰는 것으로 한정.

* [scripts/dev_metrics/expert_finder.py](scripts/dev_metrics/expert_finder.py) — `experience_atoms.py`의
  EA 방법을 저장소 전체 기여자에게 적용해 "이 모듈은 누구에게 물어볼까"를 순위로 보여준다. **PoC
  범위 제약(2026-09-11 사용자 결정): 최근 14일(2주)치 커밋만 사용** — 전체 이력 확장은 이 PoC 결과를
  보고 별도 판단. 다중 기여자 실 저장소 `pvs_crawler`(4명, 86 커밋/14일)로 실행 검증 — 모듈별 1순위
  기여자와 특정 모듈(`SWPMUtil/sage`) 조회 모두 정상 동작 확인.

## 추가 (8차 작업, AGILEDEV-1118): AI Flywheel 4·7·8단계 실행 (2026-09-11)

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

## 9차 작업: 전문가 파인더 (Expert Finder) — AGILEDEV-1132, 5개 소스 결합 (2026-09-11)

"개발시 누가 전문가일까요? AI로 전문가만을 찾자"(AGILEDEV-1132, AGILEDEV-1118의 clone) 티켓에 따라
git+Gerrit+Jira+Confluence+GitHub 5개 데이터 소스를 결합한 전문가 파인더를 새로 작성했다. 상세 설계·거버넌스
배경은 [developer_evaluation_metrics.md 8장](developer_evaluation_metrics.md#8-전문가-파인더-expert-finder--agiledev-1132-2026-09-11) 참고.

| 스크립트 | 데이터 소스 | 무엇을 계산하는가 | 비고 |
| :--- | :--- | :--- | :--- |
| [scripts/dev_metrics/experience_atoms.py](scripts/dev_metrics/experience_atoms.py) | git(로컬) | Mockus & Herbsleb(2002) 경험 원자(EA) — (모듈, 기술, 변경목적)별 집계, breadth/depth 산출 | 단일 저장소·단일 작성자 자기 진단용 |
| [scripts/dev_metrics/expert_finder.py](scripts/dev_metrics/expert_finder.py) | git(로컬, 여러 저장소) | (저장소, 모듈)별 전체 기여자 EA 랭킹 — "이 모듈은 누구에게 물어볼까" | `--since-days` 옵션화(기본 14일), 여러 `--repo` 동시 지정 가능 |
| [scripts/dev_metrics/gerrit_signal.py](scripts/dev_metrics/gerrit_signal.py) | Gerrit REST | (서버, 프로젝트)별 owner 활동 카운트 | `gerrit_fetch.py`의 "본인 owner 한정" 안전장치를 라우팅 목적으로 완화(거버넌스 확장, 사용자 승인) |
| [scripts/dev_metrics/github_signal.py](scripts/dev_metrics/github_signal.py) | GitHub(`gh` CLI) | 저장소별 커밋/PR/이슈 작성자 카운트 | 이 세션에 GitHub 전용 MCP는 없어 로컬 인증된 `gh` CLI로 대체 |
| Jira/Confluence 신호 | `mcp-atlassian` MCP (`jira_search`/`confluence_search`) | 사람별 최근 티켓 총건수(Jira `total`), 문서 활동 건수(Confluence, 상한 50) | 별도 스크립트 없음 — MCP는 담당 agent만 호출 가능하므로 조회 결과를 `jira_confluence_signal_2026-09-11.json`으로 저장 |
| [scripts/dev_metrics/combine_expert_signals.py](scripts/dev_metrics/combine_expert_signals.py) | 위 4개 산출물 결합 | 저장소/모듈별 1차 랭킹(git) + 사람별 5개 소스 종합 프로파일 표 | 개인별 성과 비교·평가로 전용 금지(라우팅 참고용) |

**검증 규모**: `AutoTest_Cmd`/`LogAnalyzer`/`pvs_crawler`/`pvs_crawler_new`/
`new_commit_review_violation_checker`/`pvs_trender`/`ldap`/`swit`/`sage-wiki` 9개 저장소를 합쳐
고유 기여자 410명(전체 이력 기준) 규모로 실행 확인 — 목표였던 "~20명"을 크게 상회.

**2026-09-11 후속 반영** (사용자 피드백): (1) `@lge.com`/`@lgepartner.com` 등 도메인이 달라도 `@` 앞부분만
같으면 동일인으로 합산하도록 `combine_expert_signals.py`에 `normalize_person()` 추가. (2) 회사의 실제
GitHub/GitLab은 github.com이 아니라 `mod.lge.com/hub`(자체 호스팅 GitLab)임을 반영해
[scripts/dev_metrics/gitlab_signal.py](scripts/dev_metrics/gitlab_signal.py) 신규 작성(`~/code/mouse`의
기존 연동 코드와 동일한 `.env`의 `LGEP_ID`/`LGEP_PASSWORD` 계정 사용) — `AutoTest_Cmd`에서 실제 Merge
Request 활동을 확인해 github.com에서는 못 봤던 신호를 얻음. (3) 모든 소스를 180일로 통일 → 고유 인원
391명(180일 이내 활동 기준) 확인.
