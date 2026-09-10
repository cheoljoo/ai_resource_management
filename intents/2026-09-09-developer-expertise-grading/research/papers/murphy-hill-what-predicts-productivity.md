# What Predicts Software Developers' Productivity?

- 저자: Emerson Murphy-Hill, Ciera Jaspan, Caitlin Sadowski, David C. Shepherd, Michael Phillips, Collin Winter, Andrea Knight, Edward K. Smith, Matthew Jorde
- 출처/venue/연도: IEEE Transactions on Software Engineering, 47(3): 582-594, 2021 (arXiv/IEEE Xplore 게재는 2019년)
- 링크: https://getdx.com/research/what-predicts-software-developers-productivity/ , https://www.researchgate.net/publication/331219121 , https://dblp.uni-trier.de/rec/journals/tse/Murphy-HillJSSP21.html

> 참고: 원 조사 후보 목록에는 "마이크로소프트의 개발자 생산성 측정 연구"로 언급되어 있었으나, 실제 확인 결과 이 논문의 저자진은 **Google** 소속이다(Murphy-Hill, Jaspan, Sadowski 등 다수가 Google Engineering Productivity Research 팀). 마이크로소프트가 아닌 Google 연구로 정정하여 수록한다.

## 핵심 주장 요약
3개 기업(그 중 하나는 Google로 알려짐)에 걸쳐 622명의 개발자를 대상으로 설문을 실시해, 자기보고식(self-rated) 생산성과 상관관계가 있는 요인이 무엇인지 광범위하게 조사한 실증 연구다. 핵심 발견은 기술적 요인(도구, 코드베이스 품질 등)보다 비기술적 요인 — 직무에 대한 열정(job enthusiasm), 새로운 아이디어에 대한 동료의 지지(peer support for new ideas), 업무 성과에 대한 유용한 피드백 수신 — 이 자기 인식 생산성과 더 강하게 연관된다는 것이다. 또한 소프트웨어 개발자는 다른 지식노동자 직군과 비교했을 때 "작업의 다양성(task variety)"과 "재택근무 가능 여부"가 생산성 인식과 더 강하게 상관된다는 차별점도 보고했다. 이는 순수 활동 로그 기반 지표만으로는 실제 생산성 인식의 핵심 동인을 포착할 수 없음을 시사한다.

## 주요 발견/모델
- 비기술적 요인(직무 열정, 동료 지지, 성과 피드백)이 자기보고 생산성과 가장 강한 상관관계를 보임 — 기술적 요인(도구/환경)보다 우선.
- 작업 다양성(task variety)이 개발자 생산성 인식에 유의미한 긍정적 영향 — 반복적 단순 작업만 계속하면 생산성 인식이 낮아짐.
- 재택/원격 근무 가능성이 개발자 그룹에서 특히 두드러진 긍정적 요인으로 나타남(다른 지식노동자 대비).
- 대규모(622명), 3개 조직 교차 비교 설문으로 일반화 가능성을 높인 방법론.

## 이 프로젝트에 적용한다면 (상세)
- **기존 지표 보완**: spec.md의 "활동 폭/다양성" 신규 지표(완료 조건 1번)는 이 논문의 "task variety가 생산성 인식과 상관관다"는 발견과 직접적으로 연결된다 — 즉 이번 티켓에서 추가하려는 신규 지표의 학술적 근거로 이 논문을 인용할 수 있다. 여러 프로젝트/기술 스택에 걸친 활동 범위를 측정하는 것은 단순한 "산만함"이 아니라 이 논문이 실증한 긍정적 생산성 신호일 수 있다는 해석을 신규 지표 설명에 추가할 수 있다.
  - 3.3(블로커 해결 및 동료 멘토링, `[X]`)의 보완 대안에 "동료 지지(peer support for new ideas)"가 생산성의 핵심 예측 변수라는 이 논문의 발견을 근거로 추가 — Peer Feedback 설계 시 "이 동료가 내 아이디어를 지지/장려했는가" 문항을 포함하도록 구체적으로 제안할 수 있다.
- **새로 추가할 지표**: 이 논문의 핵심 시사점은 "자기보고 없이는 진짜 생산성 동인을 알 수 없다"는 것이다. spec.md의 "다차원 프로필" 산출물에, 정량 지표(1~5장) 외에 반기 1회 "직무 열정/동료 지지/피드백 충분성"을 묻는 짧은 자기보고 항목(3문항)을 추가해, 시스템 메타데이터만으로 채울 수 없는 부분을 명시적으로 빈 칸(관찰 불가 영역)으로 남기지 않고 자기보고로 채우는 방식을 제안. 데이터 소스는 본인 작성(개인정보 문제 없음, spec.md의 "본인 범위 한정" 조건과 부합).
- **Goodhart's Law/인사평가 오용 방지 시사점**: 이 연구는 생산성의 가장 강력한 예측 변수가 "관리 가능한 개인 행동 지표"가 아니라 "조직 문화적 요인(동료 지지, 피드백 문화)"이라는 것을 보여준다. 이는 개인의 커밋/리뷰 수치를 인사평가에 연동하는 접근이 인과관계상 부적절할 수 있음을 강하게 시사한다 — 생산성 저하의 원인이 개인 역량이 아니라 조직/팀 환경(동료 지지 부족, 피드백 부재)일 가능성이 높기 때문이다. `developer_evaluation_metrics.md` 5장 "인사 평가 직접 연동 금지" 및 "Support, Not Surveillance" 원칙에 이 논문을 인용해, "낮은 지표 수치를 개인 문책이 아니라 팀 환경 개선 신호로 해석해야 한다"는 근거를 추가할 수 있다.
