# 리서치 — 빅테크의 개발자 성과 모니터링 방식

> 조사 방법: 공식 엔지니어링 블로그, 컨퍼런스/연구 발표(ACM Queue, arXiv), 신뢰할 만한 기술 매체(The Pragmatic
> Engineer, GetDX)를 우선 인용했습니다. 사내 비공개 프로세스(예: 실제 승진/PIP 심사 세부 기준)는 대부분 외부에
> 공개되어 있지 않으므로, 추측한 부분은 **"확인 안 됨"**으로 명시했습니다.

---

## 1. Google

### 무엇을 측정하는가
- **DORA 4대 지표 (Four Keys)**: 배포 빈도(Deployment Frequency), 변경 리드타임(Lead Time for Changes),
  변경 실패율(Change Failure Rate), 서비스 복구 시간(Time to Restore Service). Google Cloud DevOps
  Research and Assessment(DORA) 팀이 6년간의 연구로 정립했으며, 팀/애플리케이션 단위 성과를 low~elite로
  구분한다. (최근에는 "Deployment Rework"를 더한 5개 지표로 확장되는 추세도 있음 — dora.dev.)
- **SPACE 프레임워크**: Nicole Forsgren(당시 GitHub/DORA 창시자), Margaret-Anne Storey(Univ. of
  Victoria), Microsoft Research 공동 연구진이 2021년 ACM Queue에 발표. Satisfaction & well-being,
  Performance, Activity, Communication & collaboration, Efficiency & flow 5개 축으로 구성되며, "생산성은
  단일 지표/차원으로 측정될 수 없다"는 것이 핵심 전제.
- **GSM(Goals → Signals → Metrics) 프레임워크**: Google 내부에서 무엇을 측정할지 정할 때 쓰는 절차. 먼저
  목표(예: 속도, 인지 부하/Ease, 품질)를 정의하고, 그 목표를 나타내는 신호(Signal)를 고른 뒤, 마지막에
  구체적 지표(Metric)를 선택한다. 지표를 먼저 정하고 목표를 끼워 맞추는 순서를 명시적으로 피한다.
- **분기별 Engineering Satisfaction 설문 + 실시간 Experience Sampling 설문**, **시스템 로그**(코딩 시간,
  코드 리뷰 시간, 문서 열람 시간, 회의 시간 등 워크플로 세션 트래킹)을 결합해 VP부터 개별 개발자까지 보는
  대시보드를 구성.

### "일을 잘한다"의 판단 방식
- 성과 평가(Perf review)에서 라인 수(LOC)·커밋 수·코드리뷰 수 같은 산출물 카운트가 **완전히 배제되지는
  않지만, 평균에서 크게 벗어나지 않는 한 비중 있게 다뤄지지 않는다** — 즉 이상치 탐지용 보조 신호이지
  평가 근거 자체가 아니다.
- 정량 지표(DORA/SPACE 기반 시스템 로그)와 정성 신호(동료·매니저의 서술형 코드리뷰 문화, 설계 문서 리뷰)를
  결합. Google의 코드 리뷰 문화 자체가 "완벽함이 아니라 지속적 개선"을 지향하는 것으로 알려져 있음(코드
  리뷰가 곧 팀 협업/멘토링의 핵심 채널).
- 설문 데이터는 **응답자를 식별할 수 없도록 집계**하여, 애초에 개별 개발자 평가에 쓸 수 있는 구조 자체를
  차단한다.

### 단일 지표 줄세우기 방지 장치
- SPACE·GSM 프레임워크 자체가 "단일 지표로 생산성을 재려는 시도"에 대한 명시적 반작용으로 설계됨.
- DORA 공식 가이드(dora.dev)는 "지표는 팀/애플리케이션 단위로 적용하고 개별 엔지니어를 줄세우는 데 쓰지
  말라"고 명시적으로 경고하며, Goodhart's Law를 직접 언급("배포를 하루 몇 회 이상 하라"는 식의 일괄 목표가
  지표 게이밍을 유발함).
- 만족도 설문의 익명 집계 설계로 개인 식별·평가 연결 자체를 구조적으로 차단.

### 출처
- Forsgren, Storey et al., "The SPACE of Developer Productivity" — https://queue.acm.org/detail.cfm?id=3454124 (ACM Queue, 2021)
- Microsoft Research 소개 페이지 — https://www.microsoft.com/en-us/research/publication/the-space-of-developer-productivity-theres-more-to-it-than-you-think/
- Google Cloud, "Use Four Keys metrics ... to measure your DevOps performance" — https://cloud.google.com/blog/products/devops-sre/using-the-four-keys-to-measure-your-devops-performance
- DORA 공식 가이드 — https://dora.dev/guides/dora-metrics/
- GetDX, "How Google measures developer productivity" — https://getdx.com/blog/how-google-measures-developer-productivity/
- Google SWE Book(Abseil), "Why Should We Measure Engineering Productivity?" — https://abseil.io/resources/swe-book/html/ch07.html

---

## 2. Spotify

### 무엇을 측정하는가
- **Spotify Model (Squad/Tribe/Chapter/Guild)**: Squad(8명 이하 자율 미션 단위) → Tribe(연관 Squad
  묶음) → Chapter(직군별 스킬 공유·피플 매니지먼트) → Guild(자발적 관심사 커뮤니티)로 구성된 조직 구조.
  이 구조 자체는 "개인 성과 측정 체계"가 아니라 **자율성(Autonomy)과 정렬(Alignment)의 균형**을 위한
  조직 설계이며, 개인 단위 KPI를 강제하지 않는다.
- **Squad Health Check Model**: Henrik Kniberg가 Spotify 재직 중 만들어 2014년 CC 라이선스로 공개한
  자가진단 도구. "재미있는가", "쉽게 릴리스할 수 있는가", "배우고 있는가", "코드베이스 상태" 등 11개
  지표를 팀이 스스로 신호등(Red/Yellow/Green)으로 평가한다. **팀 단위 정성적 자기평가**이며 개인 랭킹과는
  무관.
- **DXI(Developer Experience Index)**: 조사 결과 이 지표는 Spotify 자체가 만든 것이 아니라 업계 컨설팅/
  플랫폼 회사 **DX(getdx.com)**가 800개 이상 조직·4만 명 이상 개발자 데이터를 바탕으로 만든 프레임워크로
  확인됨. Ease of release, 코드 리뷰, 문서화, Deep work, 로컬 반복 속도 등 14개 차원을 팀·롤·연차별로
  집계해 조직 차원의 마찰(friction) 지점을 찾는 데 쓰인다. 개인 단위 트래킹에 대한 언급은 없음. **Spotify가
  DXI를 공식 도입했다는 근거는 확인 안 됨** — Spotify 관련 자료에서 실제로 확인되는 것은 위의 Squad Health
  Check 쪽이다.

### "일을 잘한다"의 판단 방식
- Squad 단위의 자율성을 전제로, "일을 잘한다"의 판단이 상당 부분 **팀 자체의 자기 진단(Health Check)**과
  **Chapter Lead(직군 리더)의 정성 평가**에 위임되는 구조로 알려져 있다(공식 성과평가 세부 기준 자체는
  외부에 상세히 공개되어 있지 않음 — 확인 안 됨).
- 개인 성과보다 "이 팀/미션이 건강하게 돌아가는가"를 먼저 진단하고, 그 결과를 바탕으로 조직적 개선(프로세스,
  툴, 로드맵 조정)을 하는 흐름이 강조된다.

### 단일 지표 줄세우기 방지 장치
- Squad Health Check은 애초에 **정성적 색상 코드(Red/Yellow/Green) + 토론**으로 설계되어, 숫자 하나로
  줄세우는 것 자체가 구조적으로 불가능하다. 목적이 "개선 대화를 여는 것"이지 "팀/개인 순위를 매기는 것"이
  아님이 원 저자(Kniberg)에 의해 명시됨.
- Squad 자율성 모델은 애초에 상부에서 획일적 KPI를 하향 지시하기보다 팀이 스스로 우선순위와 작업 방식을
  정하게 하여, 특정 단일 지표에 조직 전체가 최적화되는 위험을 줄이는 설계 철학을 갖는다.

### 출처
- Henrik Kniberg, "Squad Health Check model – visualizing what to improve" — https://blog.crisp.se/2014/09/16/henrikkniberg/squad-health-check-model
- Atlassian, "Discover the Spotify model" — https://www.atlassian.com/agile/agile-at-scale/spotify
- GetDX, "What is the DXI? The guide to the Developer Experience Index" — https://getdx.com/blog/guide-to-developer-experience-index/ (DXI가 DX사(社)의 프레임워크임을 확인 — Spotify 공식 도입 여부는 확인 안 됨)

---

## 3. Uber

### 무엇을 측정하는가
- **Eng Metrics Dashboard**: PR(Uber 용어로 "diff") 관련 지표, 코드 리뷰 지표, Focus Time(몰입 시간)
  통계를 전사 엔지니어에게 노출하는 대시보드. 2023~2024년경 CEO 다라 코스로샤히가 직접 주도해 전사
  롤아웃한 것으로 The Pragmatic Engineer 뉴스레터가 보도.
  - 전신인 2017년 버전은 **조직(팀) 단위 집계 데이터만** 제공했고, 개인별 수치는 리더십에게만 제한적으로
    공개되었다.
  - 2020년에 매니저 레벨까지 개인 지표를 확장하는 안이 논의되었으나 실제 구현되지 않았다(엔지니어들의
    반발 우려 때문으로 추정 — 확인 안 됨). 이번 신규 대시보드는 개인 단위 가시성을 높이는 방향으로
    전환된 것으로 보도됨.
- **uMetric**: 엔지니어링 생산성 지표가 아니라 **비즈니스 지표 표준화 플랫폼**(메트릭 정의·뷰를 다양한
  저장소에 걸쳐 단일화)으로, ML 피처 엔지니어링 등에 쓰이는 사내 데이터 플랫폼. 개발자 개인 성과 평가와는
  직접 관련이 없는 것으로 확인됨(별도 시스템).

### "일을 잘한다"의 판단 방식
- 확인된 공개 자료 범위에서는, Uber가 개인 성과를 어떻게 "판단"하는지(승진/평가 기준의 세부 가중치, peer
  review 여부 등)에 대한 공식 문서는 찾지 못함 — **확인 안 됨**.
- 다만 대시보드 도입 초기 히스토리에서 나타나는 원칙은 "집계 데이터는 조직 개선에, 개인 데이터는 신중하게
  제한적으로만 노출"이었다는 점.

### 단일 지표 줄세우기 방지 장치
- 초기(2017)에는 **개인별 지표를 의도적으로 엔지니어 본인에게도 숨겼다** — 리더십은 "직접 보이면 잘못된
  행동에 최적화(게이밍)할 것"이라 판단했고, 실제로 지표를 몰랐던 기간에는 게이밍이 관찰되지 않았다고
  보도됨.
- 최근 개인 단위 가시성 확대에 대해 **엔지니어와 매니저 양쪽에서 "개인 랭킹/평가 도구로 오남용될 수
  있다"는 우려가 제기**되었음 — 이는 업계 컨센서스(단일 지표 줄세우기 위험)가 실제 사내에서도 논쟁거리임을
  보여주는 사례.
- 참고(타사 비교, 같은 기사에서 언급): Amazon의 "Crux"류 도구나 자동 커밋/트리비얼 코드 생성으로 지표가
  쉽게 게이밍될 수 있다는 지적, Facebook은 명시적 목표치를 두지 않는 편, GitLab은 2020~2021년 "MR
  20% 증가" 목표를 시도했다가 부작용으로 철회한 사례가 함께 보도됨 — Goodhart's Law의 실제 사례로
  참고할 만함.

### 출처
- The Pragmatic Engineer, "How Uber is Measuring Engineering Productivity" — https://newsletter.pragmaticengineer.com/p/uber-eng-productivity
- Uber Engineering Blog, "The Journey Towards Metric Standardization"(uMetric) — https://eng.uber.com/umetric/ (해당 페이지 실제 접근이 일부 제한되어 검색 스니펫으로만 교차 확인 — 원문 상세 접근 재시도 권장)

---

## 4. LinkedIn

### 무엇을 측정하는가
- **Developer Productivity and Happiness Framework**의 핵심 지표: Developer Build Time(P50/P90),
  Code Reviewer Response Time(P50/P90), Post-Commit CI Speed, CI Determinism(테스트 플래키니스의 역),
  Deployment Success Rate, Net Satisfaction(NSAT, 설문 기반).
- 위 지표들을 0~5 스케일의 **자체 "Developer Experience Index"**로 환산 — 예: 빌드 5분 초과는 나쁜
  경험, 10초 미만은 훌륭한 경험으로 매핑. 팀 단위로 여러 지표의 평균 인덱스를 산출.
- **코드 리뷰 참여**(작성자·리뷰어 양쪽 모두)는 공식적으로 승진 심사(promotion evaluation)에서
  고려 요소로 언급됨 — LinkedIn Engineering, "Effective Code Reviews and File Ownerships"(2016).

### "일을 잘한다"의 판단 방식
- LinkedIn은 이 인덱스에 대해 **"이 지표는 개발자의 성과(performance)를 나타내는 것이 아니라, 소프트웨어
  개발 관련 활동을 하면서 겪는 경험(experience)을 나타낸다"**고 원문에서 명시적으로 선을 긋는다. UI와
  용어 선택 단계에서부터 "성과 평가 도구로 오인되지 않도록" 별도로 신경 썼다고 밝힘.
- 승진 심사에서는 코드 리뷰 참여도(정량 카운트가 아니라 "참여했는가")가 정성적 판단 요소 중 하나로
  들어가되, 위 Developer Experience Index/빌드시간류 지표와는 별개의 트랙으로 운영된다.

### 단일 지표 줄세우기 방지 장치
- 개별 지표(빌드시간, 리뷰 응답시간 등)를 그대로 노출하지 않고 **복합 인덱스로 합성**해 특정 지표 하나에
  최적화(게이밍)하는 유인을 줄인다.
- "성과 평가 도구가 아니다"라는 점을 UI/용어 설계 단계에서부터 명시 — 즉 지표 설계뿐 아니라 **지표를
  보여주는 방식(제품 UX) 자체가 오용 방지 장치**로 다뤄짐. 관리자에게는 "개선 지점을 찾는 도구"로만
  제공되도록 정보 과부하를 줄이는 레이어드 설계를 적용.

### 출처
- LinkedIn Engineering Blog, "Inside Look: Measuring Developer Productivity and Happiness at LinkedIn" — https://www.linkedin.com/blog/engineering/developer-experience-productivity/inside-look-measuring-developer-productivity-and-happiness-at-l
- LinkedIn Engineering Blog, "Effective Code Reviews and File Ownerships"(2016) — https://engineering.linkedin.com/blog/2016/01/effective-code-reviews-and-file-ownerships

---

## 5. 공통 패턴 종합

### 공통으로 나타나는 원칙 (3~5개)

1. **단일 지표는 금지, 복합/다차원 프레임워크로 대체한다.**
   Google(SPACE·DORA·GSM), Spotify(Squad Health Check 11개 지표), Uber(대시보드가 diff·리뷰·Focus
   Time을 함께 봄), LinkedIn(6개 지표를 하나의 Experience Index로 합성) 모두 "지표 하나로 줄세우지
   않는다"는 설계를 공유한다.
2. **개인 식별·개인 랭킹으로 이어지는 경로를 구조적으로 차단한다.**
   Google은 설문을 익명 집계해 개인 평가에 원천적으로 못 쓰게 만들고, LinkedIn은 "이건 성과 지표가
   아니다"를 UI 문구로 못 박고, Uber는 초기에 개인 지표 자체를 숨겼다. 즉 "정책으로 하지 말라"뿐 아니라
   "구조/UI/집계 방식으로 아예 못 하게" 만드는 것이 실질적으로 작동한 사례들이다.
3. **Goodhart's Law를 명시적으로 경계 문구에 넣는다.**
   DORA 공식 가이드는 "일괄 목표(예: 배포 횟수 강제)"가 게이밍을 유발한다고 직접 서술하며, GitLab의 "MR
   20% 증가" 목표 실패 사례가 반복적으로 반면교사로 인용된다.
4. **정량 시스템 신호 + 정성 평가(동료/리드 리뷰)를 병행한다.**
   Google의 코드 리뷰 문화, LinkedIn의 승진 심사 정성 요소, Spotify의 팀 자가진단+Chapter Lead 판단이
   공통적으로 "숫자만으로 결론 내지 않는다"는 2트랙 구조를 취한다.
5. **측정의 목적을 "지원/개선"으로 프레이밍하고, 그 프레이밍을 제품/문구 단계에서부터 고정한다.**
   LinkedIn의 "이건 performance가 아니라 experience다" 명시, Spotify Health Check의 "개선 대화를 열기
   위한 도구"라는 원저자 설명, Google의 "Focus Time·Ease" 중심 목표 설정이 모두 여기 해당한다.

### 이 프로젝트에 구체적으로 어떻게 적용할지

`developer_evaluation_metrics.md`와 `self_performance_report_2026-08.md`는 이미 SPACE·DORA·Goodhart's
Law·"인사 평가 직접 연동 금지" 원칙을 문서 상단에 명시하고 있어 업계 컨센서스와 방향이 일치한다. 다만 위
리서치에서 확인된 구체적 실행 장치들을 다음과 같이 더 반영할 수 있다.

1. **[문서] `developer_evaluation_metrics.md` 3장 종합 매트릭스에 "인덱스 합성 원칙" 절 신설**
   - LinkedIn 사례(개별 원시값 대신 0~5 합성 인덱스로만 1차 노출)를 참고해, 대항목 1~5의 소항목 원시값
     (예: Patchset 수, Lead Time, WIP 건수 등)을 **그대로 사람 단위로 나열해 보여주지 말고**, 대항목별
     "관찰 필요/양호/우수" 3단계 정성 밴드(spec.md 후보안 A/B의 절충)로 1차 합성한 뒤 원시값은 "상세
     보기"에만 두는 구조를 `scripts/dev_metrics/` 리포트 출력 포맷에 반영.
   - `self_performance_report_2026-08.md` 리포트 최상단에 LinkedIn 문구를 응용한 고정 문구를 넣는다:
     "이 리포트의 지표는 성과(performance) 평가가 아니라 업무 경험/병목(experience & friction) 진단
     지표입니다." — 이는 spec.md 완료조건 5번(인사평가 금지 원칙 명시)을 문서 서두에 실제로 박아 넣는
     구체적 실행 방법이 된다.

2. **[스크립트] 개인 식별이 가능한 원시 수치를 단독으로 출력하는 CLI 옵션에는 항상 경고 문구를 강제 출력**
   - Uber가 초기에 "개인별 수치를 숨겨서 게이밍을 막았다"는 사례를 참고, `scripts/dev_metrics/` 안에
     본인 1인만 대상으로 하는 이번 intent 범위에서도, 추후 여러 명으로 확장될 것을 대비해 "개인 raw
     지표를 화면에 그대로 뿌리는 모드"는 기본값이 아니라 `--raw` 같은 명시적 옵션으로만 노출하고, 그
     옵션 실행 시 "이 출력을 인사평가/비교에 쓰지 마십시오" 경고를 stdout에 항상 함께 찍도록 구현한다.
     (spec.md의 "C안" — 등급 옵션에 경고를 항상 동봉 — 과 동일한 패턴을 raw 수치 출력에도 확장 적용.)

3. **[스크립트] "활동 폭/다양성"(spec.md 완료조건 1) 지표를 설계할 때 Goodhart's Law 안티패턴을 표에
   명시적으로 추가**
   - 현재 `developer_evaluation_metrics.md` 1.2절 표에는 LOC/커밋 수/근무시간/버그 수정 건수 4개
     안티패턴이 있다. 신설되는 "활동 폭/다양성" 지표(여러 프로젝트/기술 스택 분포)도 "다양성 점수를
     높이기 위해 여러 프로젝트에 의미 없이 사소한 커밋을 흩뿌리는 행동"이라는 새로운 게이밍 위험이 있으므로,
     이를 표의 5번째 행으로 추가하고 "정규화 방식"(예: 프로젝트당 최소 실질 기여량 임계치 이상만 카운트)을
     명시한다.

4. **[문서] 대항목 3.3(블로커 해결/멘토링)에 Spotify Squad Health Check 스타일의 정성 자가진단을
   "보완 대안"으로 구체화**
   - 현재는 "Peer Feedback / Kudos 채널"만 제시되어 있는데, Spotify의 색상 코드(Red/Yellow/Green) +
     토론 방식처럼 **숫자화하지 않는 정성 신호 수집 템플릿**(예: 반기 1회, 5~7개 질문에 Red/Yellow/Green
     응답 + 자유 서술)을 구체 양식으로 `developer_evaluation_metrics.md` 3.3절에 예시로 추가하면,
     "정성 평가를 어떻게 구조화할지"에 대한 실행 가능한 절차가 생긴다.

5. **[반패턴 회피 체크리스트] 이번 intent 산출물(3단계 종합 로직, self_performance_report)에 적용할 때
   반드시 피해야 할 것**
   - 대항목별 소항목 원시값을 단순 합산해 "총점"을 만들지 않는다(Google/LinkedIn 모두 지표를 곱하거나
     더해 단일 스칼라로 만드는 방식을 쓰지 않고, 차원별로 분리해 보여줌 — spec.md B안과 일치).
   - "우수/양호/관찰 필요" 같은 밴드를 매기더라도, 그 산출 근거(어떤 원시값이 어느 임계값을 넘었는지)를
     항상 함께 노출해 블랙박스 점수가 되지 않게 한다(LinkedIn이 "빌드 5분=나쁨" 식으로 매핑 기준을
     투명하게 공개한 것과 동일 원칙).
   - 리포트 제목이나 파일명에 "등급", "평가", "점수" 같은 단어보다는 "진단", "프로필", "경험 지표" 같은
     표현을 사용해, 산출물 자체의 프레이밍부터 인사평가 오용 가능성을 낮춘다(LinkedIn의 UI/용어 설계
     사례를 그대로 적용).
   - 본인(cheoljoo.lee) 외 타인 데이터를 실행하지 않는다는 spec.md의 범위 제한은 Uber가 개인 지표
     노출을 단계적으로/신중하게 확장한 히스토리와도 부합하므로 그대로 유지한다.
