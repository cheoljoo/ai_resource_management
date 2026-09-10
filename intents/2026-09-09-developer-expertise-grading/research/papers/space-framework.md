# The SPACE of Developer Productivity: There's more to it than you think

- 저자: Nicole Forsgren, Margaret-Anne Storey, Chandra Maddila, Thomas Zimmermann, Brian Houck, Jenna Butler
- 출처/venue/연도: ACM Queue, Vol 19(1), pp. 20-48, 2021 (동일 내용이 Communications of the ACM에도 게재)
- 링크: https://dl.acm.org/doi/10.1145/3454122.3454124 (ACM Queue), https://dl.acm.org/doi/10.1145/3453928 (CACM), https://www.microsoft.com/en-us/research/publication/the-space-of-developer-productivity-theres-more-to-it-than-you-think/

## 핵심 주장 요약
개발자 생산성은 개인의 활동량이나 엔지니어링 시스템 효율성만으로는 측정할 수 없는 다차원 개념이며, 단일 지표(특히 Activity 하나)로 판단하면 왜곡된 결론에 도달한다. 저자들은 생산성을 Satisfaction & well-being, Performance, Activity, Communication & collaboration, Efficiency & flow의 5개 차원(SPACE)으로 분해할 것을 제안한다. 각 차원은 서로 트레이드오프 관계에 있을 수 있으므로(예: Activity를 높이면 Well-being이 떨어짐), 최소 3개 이상의 차원을 조합해 균형 잡힌 지표 세트를 구성해야 한다. 이 프레임워크는 특정 지표 목록이 아니라 "어떤 질문을 던져야 하는가"를 안내하는 사고 도구다. 조직·팀·개인 등 측정 대상 레벨에 따라 적절한 차원과 지표가 달라진다는 점도 강조한다.

## 주요 발견/모델
- **S (Satisfaction and well-being)**: 개발자가 자기 업무·도구·팀에 대해 느끼는 만족도, 번아웃/피로도. 설문(eNPS, 만족도 서베이) 기반.
- **P (Performance)**: 코드/시스템이 낸 결과(산출물의 품질, 신뢰성, 비즈니스 임팩트) — 코드를 "얼마나 잘 짰나"가 아니라 "그 결과가 무엇을 달성했나".
- **A (Activity)**: 커밋 수, PR 수, 배포 수 등 카운트 가능한 산출물. 가장 측정하기 쉽지만 단독 사용 시 가장 위험한 차원.
- **C (Communication and collaboration)**: 문서화 품질, 지식 공유, 온보딩 속도, 발견 가능성(discoverability) 등 팀 간 정보 흐름.
- **E (Efficiency and flow)**: 방해 없이 몰입해서 작업을 이어갈 수 있는 정도 — 컨텍스트 스위칭, 대기 시간, 핸드오프 수.
- 핵심 권고: (1) 최소 2~3개 차원을 조합해서 측정, (2) 정성적 지표(설문)와 정량적 지표(시스템 로그)를 함께 사용, (3) 팀/조직 단위 진단에 적합하며 개인 성과 평가나 순위 매기기에는 부적합함을 명시적으로 경고.

## 이 프로젝트에 적용한다면 (상세)
- **관련 기존 지표 보완**: `developer_evaluation_metrics.md`의 5대 대항목 구조(품질/속도/협업/문제해결/웰빙) 자체가 SPACE의 5차원과 정확히 대응된다 — 1장(품질=Performance), 2장(속도=Efficiency&Flow+Activity), 3장(협업=Communication&Collaboration), 5장(웰빙=Satisfaction&Well-being)으로 매핑 가능. 이미 이 구조를 채택하고 있다는 점을 문서 1.1절에 "SPACE 프레임워크의 5개 차원을 이렇게 매핑했다"는 명시적 각주로 추가하면 근거가 강화된다.
  - 1.1(재작업률), 1.2(재수정 빈도) 등은 SPACE의 Activity/Performance 경계에 걸쳐 있는데, 현재는 Performance 차원(품질)으로만 분류되어 있다. SPACE 관점에서는 이 지표들을 "Activity 신호로만 보되 Performance 판단에는 반드시 다른 차원과 결합"하도록 1.2절 경고에 구체적으로 못박을 필요가 있다.
  - 2.2(몰입 시간 확보율)는 SPACE의 Efficiency&Flow 차원 정의와 정확히 일치한다. 이 논문의 "context switching 카운트"도 함께 지표화할 수 있다 — 하루 동안 서로 다른 Jira 프로젝트/저장소를 오간 횟수를 Efficiency 보조 지표로 추가 제안.
- **새로 추가할 지표**: SPACE의 Satisfaction 차원은 현재 5.1(번아웃 위험도)만 다루고 직접적 만족도 설문이 없다. Teams/Copilot 기반 짧은 pulse survey(예: 주간 1문항 "이번 주 업무 흐름 만족도 1-5")를 5.3 신규 소항목으로 제안할 수 있다 — 데이터 소스는 자기보고(Self-Report)이며 `[X]` 자동 수집 불가로 분류하되 정기 운영은 가능.
- **Goodhart's Law 시사점**: 이 논문은 "Activity 차원 하나만 보면 반드시 게이밍이 발생한다"는 것을 프레임워크 차원에서 공식화한 원 출처다. `developer_evaluation_metrics.md` 1.2절의 안티패턴 표(LOC, 커밋 수 등)는 사실상 SPACE의 "Activity 단독 사용 금지" 원칙을 구체화한 것이므로, 1.2절에 이 논문을 직접 인용하며 "SPACE 5차원 중 최소 3개 이상을 함께 봐야 한다"는 정량적 가드레일(예: 최종 프로필에는 5대 대항목 중 최소 3개 이상의 항목이 [O] 또는 [△]로 채워져야 리포트를 발행한다는 규칙)을 spec.md의 산출물 요구사항에 추가하는 근거로 쓸 수 있다.
