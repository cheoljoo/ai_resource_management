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
- **베이스 브랜치를 `main`이 아니라 `intent/2026-09-09-developer-expertise-grading`으로 잡았다** — 이
  intent가 그 브랜치(커밋 `231c41f`)에서 분기됐다. 이유: `expert_finder.py`/`experience_atoms.py` 등
  핵심 구현이 전부 그 브랜치에만 있고 `main`에는 없다(`main`은 대신 SMILE 관련 내용만 가진 별도 커밋
  `cdb9884`로 갈라져 있음). **이 판단은 herdr-intent 실행 중 사용자 확인 없이 내린 것**이므로, 이
  intent 착수 전에 사용자에게 재확인받는 것을 권장한다(plan.md 착수 전 체크리스트 참고).
