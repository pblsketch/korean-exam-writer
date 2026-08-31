# 02 · 인지 요구 계약 (demand ladder)

> 독립 설계. 구성타당도(construct validity) 원리와 읽기 이해 처리 수준에서
> 도출. 난이도는 어휘·길이가 아니라 **인지 처리 깊이와 근거 분산**에서 나온다.

## demand 사다리 (schema `questions.demand`, 오름차순)

정렬 순서가 곧 계약이다. 상위 단계는 하위 처리를 포함한다(누적적).

1. **`recall`** — 지문에 명시된 정보를 그대로 확인. 한 문장/한 지점 근거.
2. **`inference`** — 명시되지 않은 함축·관계를 한두 단계 추론. 인접 근거 통합.
3. **`integration`** — 흩어진 근거(여러 문단·〈보기〉·복수 지문)를 종합·적용.
4. **`critique`** — 논증의 타당성·전제·한계를 평가·비판. 근거+외적 기준.

## 두 가지 설계 약속 (CI로 검증되는 불변식)

1. **구성 관련 난이도(construct-relevant difficulty).**
   난이도는 `demand`와 근거 분산에서 온다. 문장을 더 어려운 어휘로 바꾸거나
   지문을 무작정 길게 늘여 난이도를 올리지 **않는다**. 문장 길이 대역은 학년
   대역에 고정되고 demand에 따라 소폭만 넓어진다(`06`).
2. **단조성(monotonicity).**
   인지 부하 지표는 demand 순위(recall→inference→integration→critique)에 대해
   **비감소**다. "더 높은" 목표가 "더 쉬운" 프로파일을 낳는 일은 없다.

## demand 분포 권고 (세트 단위)

세트는 recall만으로 채우지 않는다 — 최소 1문항은 recall 초과여야 한다
(구성타당도). demand 상향에 따라 상위 문항 비율이 커진다. 구체 수치(문항 수·
추론 비율·문장 대역)는 학년×난이도로 `06-grade-difficulty-map.md`가 정한다.

권장 개형(난이도별 대략):
- **하**: recall 중심 + inference 1
- **중**: recall·inference 균형 + integration 1
- **상**: inference 중심 + integration 1~2
- **최상**: integration·critique 포함, recall 최소화

## 근거 분산이 난이도를 만든다

같은 `type`이라도 근거가:
- 한 문장에 있으면 → recall/inference
- 한 문단 안 여러 문장에 있으면 → inference
- 여러 문단·〈보기〉에 흩어져 있으면 → integration
- 지문 + 외적 판단 기준을 요구하면 → critique

출제 시 `evidenceLocations[]`의 개수·분산이 실제 demand와 일치하는지 확인한다.

## 근거(공개 문헌)
- Kane, M. T. (2013). Validating the interpretations and uses of test scores.
  *Journal of Educational Measurement, 50*(1).
- AERA, APA, & NCME (2014). *Standards for Educational and Psychological Testing.*
