# 06 · 학년 × 난이도 매핑

> 독립 설계. 구성타당도·가독성 원리에서 도출한 작고 투명한 결정 모델.
> 어휘·길이가 아니라 **인지 요구(demand)와 근거 분산**으로 난이도를 만든다
> (`02-cognitive-contract.md`).

## 학년 → 대역 (schema `meta.grade`)

중1~고3을 두 대역으로 앵커한다. 고등이 중등보다 긴 문장·많은 문단을 허용한다.

| 대역 | 학년 | 기본 문장 길이(자) | 문단 수 |
|---|---|---|---|
| middle | 중1·중2·중3 | 30–70 | 2–3 |
| high | 고1·고2·고3 | 45–95 | 3–5 |

## demand → 구조 파라미터

demand 순위 rank(recall=0 … critique=3)로 조정한다:

- **문장 길이 대역**: 상한만 `+5×rank`로 소폭 확장(하한은 학년 대역에 고정).
  → 어휘/길이를 난이도 지렛대로 쓰지 않는다.
- **권장 문항 수**: `3 + rank` (3~6). 실증 코퍼스의 독립 독서 세트 문항 수
  (최소 3·중앙 4·최대 6)와 부합.
- **추론 비율**(recall 초과 문항 몫): `rank / 3` (0 → 1.0).
- **인지 부하 지표**: `grade_base(고등 0.5) + rank`. demand 순위에 **비감소**
  (단조). 상위 목표가 더 쉬운 프로파일을 내지 않는다.
- **지문 길이 봉투**: 실증 관측 [최소, 최대] 안. 하한은 학년·demand로 상향,
  상한은 관측 최댓값에 고정.

## 난이도 라벨 → demand 개형 (schema `meta.difficulty`)

meta의 하/중/상/최상은 세트의 demand 분포로 실현한다(`02` 권장 개형):

| 난이도 | demand 분포(권장) | 추론 비율 |
|---|---|---|
| 하 | recall 중심 + inference 1 | 낮음 |
| 중 | recall·inference 균형 + integration 1 | 중 |
| 상 | inference 중심 + integration 1~2 | 높음 |
| 최상 | integration·critique 포함, recall 최소 | 최고 |

## 검증 연결

출제 후 세트의 실제 demand 분포·근거 분산이 목표 난이도와 맞는지 확인한다.
어휘 난도만 올리고 demand는 recall에 머무는 "가짜 어려움"을 금지
(`08-verification-checklist.md`).

## 근거(공개 문헌)
- AERA, APA, & NCME (2014). *Standards for Educational and Psychological Testing.*
- Kane, M. T. (2013). *Journal of Educational Measurement, 50*(1).
- 실증 앵커: `docs/EMPIRICAL_ANALYSIS_2017_2026.md`.
