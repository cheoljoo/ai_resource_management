# 개발자 생산성/전문성 측정 관련 문헌 조사 — 인덱스

이 디렉터리는 `developer_evaluation_metrics.md`와 `intents/2026-09-09-developer-expertise-grading/spec.md`에서 다루는
"개발자 업무 역량/성과 측정 프레임워크"를 보강하기 위해, 소프트웨어 엔지니어링 생산성/전문성 측정 분야의
대표 학술 문헌·기업 기술 리포트를 조사한 결과다. 웹 검색으로 실재와 접근 가능성을 확인한 논문만 수록했다.

## 조사한 논문 목록

| 제목 | 연도 | 한 줄 요약 | 파일 |
| :--- | :---: | :--- | :--- |
| The SPACE of Developer Productivity | 2021 | 생산성은 5차원(만족도·성과·활동·협업·효율성)으로 봐야 하며 단일 지표(특히 Activity)는 위험하다는 원조 프레임워크 | [space-framework.md](./space-framework.md) |
| DevEx: What Actually Drives Productivity | 2023 | SPACE를 계승해 Feedback Loops/Cognitive Load/Flow State 3축으로 실무 적용성을 높인 개발자 경험 프레임워크 | [devex-productivity.md](./devex-productivity.md) |
| Accelerate / DORA (State of DevOps Report 연구) | 2018 (연구는 2014-2019) | 배포빈도·리드타임·변경실패율·복구시간 등 4~5개 지표로 팀 배포 성과를 실증 측정; 속도와 안정성은 트레이드오프가 아님 | [accelerate-dora.md](./accelerate-dora.md) |
| Software Developers' Perceptions of Productivity | 2014 (FSE) | 개발자 본인은 생산성을 산출량이 아니라 "방해 없는 완료감"으로 인식한다는 것을 설문+관찰로 실증 | [meyer-perceptions-of-productivity.md](./meyer-perceptions-of-productivity.md) |
| Quality and Productivity Outcomes Relating to Continuous Integration in GitHub | 2015 (ESEC/FSE) | GitHub 대규모 마이닝으로 CI 도입이 PR 처리량 증가와 연관됨을 실증(단, 품질 효과는 미묘함) | [vasilescu-ci-github.md](./vasilescu-ci-github.md) |
| Modern Code Review: A Case Study at Google | 2018 (ICSE-SEIP) | Google 900만 건 리뷰 로그 + 인터뷰/설문으로 코드 리뷰가 결함탐지뿐 아니라 지식전파·팀응집 기능을 한다는 것을 규명 | [sadowski-modern-code-review.md](./sadowski-modern-code-review.md) |
| What Predicts Software Developers' Productivity? | 2021 (TSE, 원 게재 2019) | 622명 설문 결과 기술적 요인보다 직무열정·동료지지·피드백 같은 비기술적 요인이 생산성 인식과 더 강하게 상관 (Google 연구; 후보 목록의 "마이크로소프트" 표기는 확인 결과 정정 필요) | [murphy-hill-what-predicts-productivity.md](./murphy-hill-what-predicts-productivity.md) |
| Expertise Browser: A Quantitative Approach to Identifying Expertise | 2002 (ICSE) | 설문/자기기술 없이 형상관리 변경 이력만으로 "경험 원자(EA)"를 정의해 전문성을 자동 산출하는 원조 데이터 전용 접근 | [mockus-herbsleb-expertise-browser.md](./mockus-herbsleb-expertise-browser.md) |
| Identifying Experts in Software Libraries and Frameworks among GitHub Users | 2019 (arXiv/SANER) | GitHub 메타데이터만으로 전문가 식별 시 고활동 클러스터는 실제 전문가와 65~75% 겹치지만(신뢰 가능), 저활동값은 초보자·숨은전문가 구분 불가(F=0.56, 신뢰 불가) — **비대칭적 신뢰도**를 실증 | [montandon-identifying-experts-github.md](./montandon-identifying-experts-github.md) |
| Common Method Biases in Behavioral Research | 2003 (J. Applied Psychology) | 동일 응답자가 원인·결과를 모두 자기보고할 때 발생하는 공통방법편향(CMB)의 4대 원인과 해결책을 정리한 방법론 고전 | [podsakoff-common-method-bias.md](./podsakoff-common-method-bias.md) |
| Survey Research in Software Engineering: Problems and Strategies | 2017 (arXiv/e-Informatica) | SE 설문 연구 24개 문제·65개 완화전략을 실증연구자 인터뷰로 정리 — 표본추출 어려움, 응답률 미보고, 사회적 바람직성 편향이 특히 빈번 | [ghazi-survey-research-se-problems-strategies.md](./ghazi-survey-research-se-problems-strategies.md) |

## 공통 시사점

1. **단일 지표, 특히 "활동량(Activity)" 계열 지표는 반드시 다른 차원과 결합해야 한다.** SPACE, DevEx, DORA, Meyer, Murphy-Hill 논문 모두 이 원칙을 각자의 방식으로 뒷받침한다 — 이는 `developer_evaluation_metrics.md` 1.3절(Goodhart's Law)의 가장 강력한 학술적 근거다.
2. **정량 메타데이터만으로는 "왜"를 설명할 수 없고, 정성적 자기보고/인터뷰가 필수적으로 병행되어야 한다.** Meyer(2014), DevEx(2023), Murphy-Hill(2021)이 공통적으로 강조 — 순수 시스템 로그 기반 지표(문서 [O]/[△] 항목들)의 한계를 보완할 자기보고 채널이 필요하다는 근거.
3. **생산성 지표는 원래 팀/조직 단위 진단 도구로 설계되었으며, 개인 순위화·인사평가 연동은 설계 목적을 벗어난 오용이다.** DORA, SPACE, DevEx 모두 공식 문서/저자 발언에서 이를 명시적으로 경고 — `developer_evaluation_metrics.md` 7장 및 spec.md의 "범위 밖: 단일 등급으로 줄세우기 금지" 결정을 뒷받침하는 산업 표준급 근거.
4. **생산성 저하의 원인은 개인 역량보다 조직/프로세스 환경(동료 지지, 피드백 문화, 방해 요인, 도구 마찰)에 있는 경우가 많다.** Murphy-Hill, Meyer, DevEx 공통 발견 — 낮은 지표는 "누구를 탓할 것인가"가 아니라 "무엇을 개선할 것인가"를 묻는 데 써야 한다.
5. **저장소/CI 메타데이터 기반 지표는 프로세스 변화(예: CI 도입) 전후 비교처럼 준실험적으로 해석해야 신뢰도가 높아진다.** Vasilescu et al.의 방법론이 시사 — 절대 수치의 조직 간/시점 간 단순 비교는 위험하다.

## 이 프로젝트에 우선순위 높게 적용해야 할 Top 3

1. **다차원 프로필 산출 로직에 최소 3개 이상 대항목이 채워져야 발행되는 가드레일 추가** (SPACE 근거) — 단일 항목만으로 진단하지 않도록 spec.md의 산출물 요구사항에 반영.
2. ~~정량 지표 옆에 짧은 자기보고(self-report) 항목을 나란히 배치~~ — **2026-09-09 사용자 결정(데이터 우선 원칙)으로 보류.** Meyer/DevEx/Murphy-Hill의 권고는 여전히 유효하나, Podsakoff(2003)·Ghazi et al.(2017)의 자기보고 편향 근거(아래 절 참고)에 따라 이번 intent에서는 구현하지 않고 "향후 검토"로만 문서에 남긴다.
3. **모든 산출물 상단에 "이 지표는 팀/조직 진단·자기 회고용이며 인사평가에 쓰면 안 되는 이유"를 DORA/SPACE/DevEx 등 산업 표준 근거와 함께 명시** — spec.md 완료 조건 5번이 이미 요구하는 부분이나, 이번 조사에서 확인한 각 논문의 명시적 경고 문구를 직접 인용하면 설득력이 강화된다.

---

## 데이터 전용 접근 및 설문 데이터 한계에 관한 추가 시사점 (2026-09-09 추가조사)

2026-09-09 사용자 결정("설문/자기보고를 1차 지표로 쓰지 않고 시스템 메타데이터 중심으로 먼저 접근하며,
부작용은 코멘트로 남긴다")을 뒷받침/보완하기 위해 두 갈래를 추가 조사했다.

### A. 설문 없이 메타데이터만으로 전문성을 식별하려는 연구
- **Mockus & Herbsleb(2002)**: 형상관리 변경 이력만으로 "경험 원자(EA)"를 집계해 전문성을 자동 산출하는
  원조 접근. 설문/자기기술이 전혀 필요 없다는 것을 20년 전에 이미 실증. 이 프로젝트의 데이터 우선
  원칙과 방법론적으로 가장 가까운 선행 사례.
- **Montandon et al.(2019)**: GitHub 메타데이터 기반 전문가 식별에서 **비대칭적 신뢰도**를 발견 —
  고활동 클러스터(커밋 수·코드 처치량 상위)는 실제 전문가와 65~75% 일치(신뢰 가능한 양성 신호)하지만,
  지도학습으로 저활동/중간값을 초보자와 구분하는 정확도는 F=0.56에 그침(신뢰 불가). **"메타데이터
  값이 낮다"는 것은 "역량이 낮다"는 증거가 아니라 판별 불능(모를 뿐)이라는 뜻**이라는 게 핵심 발견.

### B. 자기보고/설문을 객관적 데이터처럼 다룰 때의 편향
- **Podsakoff et al.(2003)**: 동일 응답자가 원인(자기보고 행동)과 결과(평가)를 모두 생성하면 발생하는
  공통방법편향(CMB) — 자기 선언형 Focus 태깅, Peer Kudos 등이 "실제 행동"이 아니라 "평가받고 싶어서
  하는 행동"으로 왜곡될 수 있음을 이론적으로 뒷받침.
- **Ghazi et al.(2017)**: SE 설문 연구의 고질적 문제(표본추출 실패, 응답률 미보고, 사회적 바람직성
  편향)를 실증연구자 인터뷰로 정리 — "설문을 쓰지 말라"가 아니라 "최소 방법론 기준(익명성, 응답률
  공시, 사전 테스트) 없이 쓰면 안 된다"는 결론.

### 종합: "데이터만으로 극단값은 판별 가능한가"에 대한 근거 기반 답
Montandon et al.(2019)의 비대칭적 신뢰도 발견은 이 프로젝트의 핵심 실무 질문 — "정량 지표만으로 매우
잘하는 사람과 매우 안 하는 사람을 가려낼 수 있는가" — 에 **부분적으로 "그렇다"**는 근거를 제공한다.
단, 방향에 따라 신뢰도가 다르다:

- **고신호(High Signal) → 신뢰할 만한 양성 지표**: 여러 독립적 축(커밋/리뷰/리드타임/문서화 등)에서
  꾸준히 상위권이면서 동시에 재작업률·결함밀도가 낮다면(단일 지표가 아니라 조합), 실제 고기여자일
  가능성이 높다 — 이는 인정/보상 신호로 쓸 수 있는 근거가 있다.
- **저신호(Low Signal) → 확정적 부정 지표가 아니라 "경고 신호(Warning Sign)"**: 활동량이 낮다고 곧
  역량 부족이나 태만을 의미하지 않는다(숨은 전문가, 접근 권한 제약, 비가시 업무 등 다른 설명이 항상
  가능 — Montandon 논문의 F=0.56이 바로 이 불확실성의 정량적 증거). 따라서 저신호는 **"사람에 대한
  결론"이 아니라 "추가로 확인이 필요하다는 신호"로만 취급**해야 하며, 확인 방법은 데이터 재조회가
  아니라 사람(매니저/본인)의 정성적 개입이어야 한다.
- 실무 적용: `developer_evaluation_metrics.md`에 "데이터 기반 극단값 해석의 비대칭 원칙"을 신설해
  이 비대칭성을 명문화할 것을 제안(아래 plan.md 반영 참고).
