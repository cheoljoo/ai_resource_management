# Intent — AGILEDEV-1132: AI로 전문가만을 찾자 (범위를 좁힌 AGILEDEV-1118)

- Jira: http://jira.lge.com/issue/browse/AGILEDEV-1132
- **관계**: 이 티켓은 [AGILEDEV-1118](http://jira.lge.com/issue/browse/AGILEDEV-1118)을 **clone**한
  것(Jira Link "This issue clones AGILEDEV-1118"). 담당/보고자 cheoljoo.lee, 상태 In Progress, 생성일
  2026-09-11 14:27.

## 티켓 원문 (그대로 인용)

> **제목**: 개발시 누가 전문가일까요?  AI로 전문가만을 찾자.
>
> **본문**:
> 범위를 좁혀보자.  >> 개발시 누가 전문가일까요?  AI로 전문가만을 찾자.
>
> 정성적인 평가는 배제한다.
>
> DATA 기준으로만 찾는다. 필요한 데이터들을 최대한 모아서 이를 근간으로 ....
>
> 딱 이것만 하자.   회사 안의 어떤 사람들이 전문가인지를 찾기 위한 작업을 하자.
>
> | Expertise Browser: A Quantitative Approach to Identifying Expertise | 2002 (ICSE) | 설문/자기기술
> 없이 형상관리 변경 이력만으로 "경험 원자(EA)"를 정의해 전문성을 자동 산출하는 원조 데이터 전용 접근
> | [mockus-herbsleb-expertise-browser.md](./mockus-herbsleb-expertise-browser.md) |
> | Identifying Experts in Software Libraries and Frameworks among GitHub Users | 2019 (arXiv/SANER) |
> GitHub 메타데이터만으로 전문가 식별 시 고활동 클러스터는 실제 전문가와 65~75% 겹치지만(신뢰
> 가능), 저활동값은 초보자·숨은전문가 구분 불가(F=0.56, 신뢰 불가) — **비대칭적 신뢰도**를 실증
> | [montandon-identifying-experts-github.md](./montandon-identifying-experts-github.md) |

## ⚠️ 지금까지 한 일 — AGILEDEV-1118 worktree에 이미 방대한 관련 구현이 존재함

이 티켓이 인용한 두 논문(Mockus & Herbsleb 2002, Montandon et al. 2019)의 요약 파일이 이미 저장소에
존재한다:
`intents/2026-09-09-developer-expertise-grading/worktree/intents/2026-09-09-developer-expertise-grading/research/papers/`
— 즉 이 티켓은 완전히 새로운 조사가 아니라, **AGILEDEV-1118 작업 중 이미 만든 것 중 "전문가 찾기"
부분만 떼어내 좁힌 것**으로 보인다.

`intent/2026-09-09-developer-expertise-grading` 브랜치(별도 worktree, `main`에는 병합되지 않음)에서
이미 완료된 것:

- **`scripts/dev_metrics/experience_atoms.py`** — Mockus & Herbsleb(2002)의 "경험 원자(EA)" 방법을
  구현. 커밋이 건드린 파일을 (모듈, 기술스택, 변경목적) 3축으로 분해해 누적 집계, 전문성의 폭(breadth)과
  깊이(depth)를 구분 산출.
- **`scripts/dev_metrics/monthly_activity_clusters.py`** — Montandon et al.(2019) 방법을 (원 논문은
  사람 간 클러스터링이지만) 월별 활동 시간축 클러스터링으로 재구성 구현.
- **`scripts/dev_metrics/expert_finder.py`** — 위 EA 방법을 **저장소의 전체 기여자**(본인 외 타인
  포함)에게 적용해, (모듈, 기여자)별 EA를 집계하고 "이 모듈은 최근 누가 제일 많이 만졌는가"를 랭킹으로
  보여줌. `developer_evaluation_metrics.md` 6.6절에 문서화됨. **다중 기여자 실 저장소 `pvs_crawler`
  (4명, 86 커밋)로 검증 완료** — 모듈별 1순위 기여자 랭킹, 특정 모듈 조회 모두 정상 동작 확인.
- **알려진 한계 (6.6절에 이미 명시됨)**:
  1. **PoC이므로 최근 14일(2주)치 데이터로만 범위 제한**(2026-09-11 사용자 결정) — 전체 이력 확장은
     보류 상태.
  2. 검증이 `pvs_crawler` 저장소 1개(4명)에만 국한됨.
  3. 데이터 소스가 로컬 git 메타데이터로만 한정됨 — Gerrit/Jira 데이터(`gerrit_metrics.py`,
     `jira_metrics.py`가 이미 존재)는 아직 결합되지 않음.
  4. spec.md "범위 밖" 절에 "공유 저장소의 이미 공개된 git log는 예외로 허용"이라는 조항을 신설해서
     타인 데이터 사용을 정당화해뒀음 — 이 예외 조항의 근거(라우팅 목적 한정, 성과평가 금지)를 이번
     작업에서도 그대로 계승해야 함.

## 이 intent에서 풀어야 할 것 (원문과 현재 구현 사이의 간극)

1. **"필요한 데이터들을 최대한 모아서"** — 현재는 로컬 git만 쓰고 있다. Gerrit(`gerrit_metrics.py`)·
   Jira(`jira_metrics.py`)를 전문가 판정에 결합할지, 결합한다면 어떤 신호로 쓸지 설계가 비어 있다.
2. **14일 제한 해제 여부** — "필요한 데이터들을 최대한 모아서"라는 문구는 기간 확장도 암시할 수 있다.
   전체 이력으로 늘릴지, 설정 가능한 기간으로 옵션화할지 결정되지 않았다.
3. **검증 범위 확대** — 현재 1개 저장소(4명)만 검증됨. "회사 안의 어떤 사람들이 전문가인지"라는 원문은
   조직 전체 규모를 시사하므로, 최소 1개 이상의 추가 저장소로 검증이 필요하다.
4. **AGILEDEV-1118과의 관계 정리** — 원 티켓(AGILEDEV-1118)은 이미 "등급 매기지 않기(D안: 다차원
   프로필+양극단 신호)"로 방향을 잡았고 Recognition/Warning Signal까지 구현했다. 이번 clone 티켓은
   "정성적 평가 배제, 전문가 찾기만"이라고 범위를 더 좁혔는데, 이게 (a) 기존 Expert Finder 부분만
   떼어내 독립 산출물로 다듬으라는 뜻인지, (b) Recognition Signal 등 나머지 부분은 신경 쓰지 말라는
   뜻인지 애매하다 — **담당 agent가 사용자와 먼저 정렬해야 하는 핵심 판단 지점.**

## 제약/고려사항

- **회사 정책(AGILEDEV-1118에서 이미 확정, 그대로 계승)**: 이메일·MS Teams·기타 모든 MS 제품 모니터링
  절대 금지. Jira/Codebeamer/ALM/Confluence 등 Atlassian 제품군, Gerrit, 모든 git 활동, GitHub은 허용.
- **정성적 평가 완전 배제**가 이 티켓의 핵심 전제 — 설문/Peer Feedback/자기 선언형 입력은 절대 쓰지
  않는다(AGILEDEV-1118에서 이미 같은 원칙으로 진행 중이었음).
- **타인 데이터를 다루는 작업이므로 개인정보/거버넌스 민감도가 높다** — "공유 저장소에 이미 공개된
  git log를 라우팅 목적으로만 쓴다"는 기존 예외 조항의 정신을 반드시 유지해야 한다(성과 비교·평가로
  전용 금지).

## 2026-09-11 세션에서 사용자와 정렬 완료된 결정 사항

이 문서 최초 작성 시점에는 "풀어야 할 것" 4가지가 미정이었으나, 담당 agent가 착수 전 `AskUserQuestion`으로
확인한 결과 다음과 같이 확정됐다:

1. **베이스 브랜치 → `main`으로 재확정**. 원래 `intent/2026-09-09-developer-expertise-grading`(커밋
   `231c41f`) 기반으로 worktree가 만들어져 있었으나(herdr-intent가 사용자 확인 없이 내린 판단), 사용자가
   "main 기준으로 새로 시작"을 명시적으로 선택했다. 이에 따라 담당 agent가 기존 worktree를 제거하고
   `main`(커밋 `a66db81`) 기준으로 새 worktree/브랜치(`intent/2026-09-11-expert-finder`)를 재생성했다.
   **`expert_finder.py`/`experience_atoms.py`/`monthly_activity_clusters.py`는 main에 없으므로(1118
   브랜치에만 존재) 가져오지 않고 완전히 새로 작성한다** — 사용자가 "main에서 완전히 새로 작성"을
   명시적으로 선택함. 단, `gerrit_metrics.py`/`jira_metrics.py`/`git_utils.py` 등 다른 dev_metrics
   스크립트는 main에 이미 존재한다.
2. **접근 방식 → A+B+C 전부, 그리고 원래 spec.md B안보다 더 넓은 범위로 확장**. 사용자가 A(git 확장)·
   B(Gerrit+Jira 결합)·C(독립 문서/스크립트) 세 후보 모두를 선택했고, 이어서 "jira, gerrit, collab(=
   Confluence), 사내 git, github 등을 POC 기준(2주, ~20명)으로 모두 찾는가"라고 되물어, 담당 agent가
   재확인한 결과 **5개 데이터 소스(사내 git + GitHub + Gerrit + Jira + Confluence)를 모두 결합**하는
   것으로 확정됐다.
   - **접근 경로**: git은 로컬 clone 직접 분석(기존 방식 확장), **Jira/Confluence는 이 세션에 연결된
     `mcp-atlassian` MCP 도구**(`jira_search`, `confluence_search` 등)를 그대로 사용(별도 API 토큰
     발급 불필요), **GitHub는 이미 인증된 로컬 `gh` CLI**(계정 `cheoljoo`, scope: gist/read:org/repo/
     workflow)를 사용, **Gerrit은 기존 `gerrit_fetch.py`가 쓰던 `~/code/ccr/gerrit/global_variables.py`
     자격증명을 그대로 재사용**하되 owner 필터를 자기 자신에서 풀어야 한다(아래 4번 참고).
   - `.env`에는 GitHub/Confluence용 토큰이 없었으나, 위 대체 경로(MCP·`gh` CLI)로 커버되므로 신규 토큰
     발급은 불필요한 것으로 확인됨. `GITLAB_TOKEN`은 "사내 git" 커버용으로 이미 존재.
3. **검증 규모 → 여러 저장소를 합쳐 총 ~20명 규모**. 특정 조직/팀 단위가 아니라, `~/code` 하위 여러
   저장소(예: 기존 `pvs_crawler` 4명 + `sage-wiki` 3명 등, 실제 조합은 구현 단계에서 재확정)를 합산해
   총 인원 수 기준으로 20명 규모를 맞춘다.
4. **AGILEDEV-1118과의 관계 → (b) "나머지 부분은 신경 쓰지 않아도 됨"으로 확정**. Recognition/Warning
   Signal 등 1118의 다른 부분은 이번 작업에서 손대지 않고, 1132는 "전문가 찾기"만 독립적으로 완성한다.

## ⚠️ 이번 확장이 건드리는 기존 안전장치 — 명시적 사용자 승인 필요했던 지점

`gerrit_fetch.py` 상단 주석에 **"기본적으로 특정 owner(자기 자신)로 쿼리를 제한해, 동료 데이터가 섞여
들어오지 않도록 한다"**는 의도적 설계 원칙이 이미 명시돼 있었다. 이번 20명 규모 확장은 이 안전장치를
푸는 것이므로, 담당 agent가 별도로 사용자에게 승인을 요청했고 **"라우팅 목적 한정" 전제 하에 승인**받았다
(성과평가·개인 비교 전용 금지 원칙은 그대로 유지). Jira 쪽도 동일한 정신(본인 범위 한정 원칙의 예외)이
적용된다.

- **베이스 브랜치 이력**: 최초 herdr-intent가 사용자 확인 없이 `intent/2026-09-09-developer-expertise-grading`
  기반으로 worktree를 만들었던 판단은 위 1번에서 `main` 기준으로 정정됐다(재확인 완료, 더 이상 열린
  질문 아님).
