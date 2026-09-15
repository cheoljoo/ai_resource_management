# Common Method Biases in Behavioral Research: A Critical Review of the Literature and Recommended Remedies

- 저자: Philip M. Podsakoff, Scott B. MacKenzie, Jeong-Yeon Lee, Nathan P. Podsakoff
- 출처/venue/연도: Journal of Applied Psychology, Vol. 88(5), pp. 879-903, 2003
- 링크: https://www.researchgate.net/publication/9075176_Common_Method_Biases_in_Behavioral_Research_A_Critical_Review_of_the_Literature_and_Recommended_Remedies (원문 유료, 초록/전문 발췌는 ResearchGate/scispace에서 확인 가능)

## 핵심 주장 요약
행동과학 연구에서 예측 변수(predictor)와 결과 변수(criterion)를 동일한 응답자로부터 동일한 측정 방식(예: 같은 설문지, 같은 시점, 같은 자기보고 형식)으로 수집하면, 실제로는 존재하지 않는 상관관계가 인위적으로 부풀려지거나 실제 상관관계가 왜곡되는 "공통방법편향(Common Method Bias, CMB)"이 발생한다. 저자들은 CMB의 잠재적 원인을 응답자 측 요인(사회적 바람직성 편향, 일관성 동기, 무드/기분 상태), 문항/척도 특성 요인(모호한 문항, 척도 형식의 공통성, 문항 사회적 바람직성), 문항의 맥락 요인(공통 척도 앵커, 공통 맥락 유발)으로 체계적으로 분류하고, 이를 통제하기 위한 절차적 해결책(응답원 분리, 시간·공간적 분리, 심리적 분리, 방법론적 분리)과 통계적 해결책(Harman의 단일요인검정, 잠재요인 통제 등)을 제시한다. 이 논문은 조직행동·심리측정 분야의 고전이지만, 소프트웨어공학 실증연구(특히 설문 기반 생산성/역량 연구)에서도 방법론적 타당성 검토 시 표준적으로 인용된다.

## 주요 발견/모델
- **CMB의 4대 원인 범주**: (1) 공통 응답원(Common Rater Effects) — 동일인이 원인과 결과를 모두 응답할 때 발생하는 일관성 편향·사회적 바람직성 편향, (2) 문항 특성(Item Characteristic Effects) — 모호하거나 복잡한 문항, (3) 문항 맥락(Item Context Effects) — 문항 순서/근접성으로 인한 점화(priming) 효과, (4) 측정 맥락(Measurement Context Effects) — 동일 시점·장소에서 측정.
- **절차적 해결책**: 예측변수와 결과변수를 서로 다른 응답자로부터, 서로 다른 시점에, 서로 다른 형식/매체로 수집(temporal, proximal, psychological, methodological separation).
- **통계적 해결책**: Harman의 단일요인검정(모든 문항이 하나의 요인으로 묶이는지 검사), 마커 변수(marker variable) 기법, 잠재방법요인(latent method factor) 통제 모델 등을 제시하되, 사후 통계 보정만으로는 완전한 해결이 어렵다고 경고.
- **핵심 결론**: CMB는 자기보고 데이터를 사용하는 거의 모든 연구 설계에 내재된 위협이며, 사전 설계 단계에서의 절차적 예방이 사후 통계 보정보다 훨씬 효과적이다.

## 이 프로젝트에 적용한다면 (상세)
이 논문은 B 갈래(자기보고를 객관적 데이터처럼 다룰 때의 편향)의 이론적 토대다. `developer_evaluation_metrics.md`가 이번에 채택한 방침 — "설문/자기보고를 1차 지표로 쓰지 않고 시스템 메타데이터 중심으로 접근" — 을 정당화하는 핵심 근거로 삼을 수 있다.

- **2.2 몰입 시간 확보율(Focus Time)의 "자기 선언형(Self-Report) 인터페이스"**: 현재 문서는 Jira `#focus-block` 태그나 Confluence Focus 모드 선언을 보완 대안으로 제시한다. 이때 CMB 위험은, 동일한 개발자가 (a) 자기 스스로 Focus 세션을 선언(입력)하고 (b) 그 선언 빈도가 나중에 그 사람의 "몰입도 평가"에 그대로 쓰인다는 점에서 "같은 응답원이 원인과 결과를 모두 생성"하는 전형적 공통방법편향 조건을 만든다 — 태그를 자주 남기는 사람이 실제로 더 몰입해서가 아니라 "잘 평가받고 싶어서/평가 기준을 알아서" 태깅 행동 자체를 늘릴 수 있다. 이 문구를 2.2절 "보완 대안" 하단에 코멘트로 추가할 것을 권장: "자기 선언형 Focus 태깅은 Podsakoff et al.(2003)이 지적한 공통방법편향(같은 응답원이 원인 행동과 평가 결과를 동시에 생성) 위험을 가지므로, 태깅 빈도 자체를 정량 점수화하지 말고 시스템 메타데이터(Inter-Event Gap, Jira 상태 전이 구간)와 태깅 시점이 실제로 일치하는지 교차검증하는 정성적 참고용으로만 활용해야 한다."
- **3.3 블로커 해결 및 동료 멘토링의 "Peer Feedback"·"Kudos 태깅"**: 동료 다면평가나 자발적 감사(Kudos) 태깅 역시, 평가하는 사람과 평가받는 사람의 관계(같은 팀, 최근 도움을 주고받은 맥락)가 응답에 영향을 미치는 유사 편향(사회적 바람직성 편향 및 문항 맥락 효과)에 노출된다. 3.3절에 "Peer Feedback/Kudos 태깅 결과는 특정 시점에 특정 관계에서 수집된 것이므로 CMB 소지가 있다 — 정량 순위화가 아닌 정성적 신호(누가 도움을 주고받았는지 파악)로만 활용하고, 동일 페어의 반복 상호 추천은 가중치를 낮춘다"는 코멘트를 추가하는 것을 권장한다.
- **문서 전체에 걸친 일반 원칙**: `developer_evaluation_metrics.md` 4절(3단계 하이브리드 평가 체계)의 3단계(동료 다면 피드백)에 "이 단계는 CMB로 인해 절대적 점수가 아닌 정성적 참고 자료로만 활용해야 한다"는 문구를 추가하면, 문서가 이미 채택한 "설문은 보조 신호"라는 원칙에 학술적 근거를 명시적으로 결합할 수 있다.
