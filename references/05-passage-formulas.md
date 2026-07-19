# 05 · 지문 구성 공식

> 독립 설계. 공개 텍스트언어학(전개 구조)과 실증 코퍼스 앵커(2017–2026 수능
> 독서 집계, 비재구성 통계)에서 도출. 원문·문항번호·정답은 담지 않는다.

## 구성 (schema `meta.passageForm`, `passages[].part`)

- **`single`** — 단일 지문. `part`는 `""`.
- **`integrated`** — 주제 통합형. 지문 (가)/(나) 두 편(`part`=`"가"`,`"나"`).
  두 지문은 같은 화제를 다른 관점/자료로 다루며, `crosstext_integration`
  문항으로 연결한다.

## 분야 (schema `meta.subjectField`)

인문 / 사회 / 과학기술 / 예술 / 문학 / 기타. 분야별 전형 전개(골격일 뿐,
`11-development-methods.md`가 확장):

| 분야 | 전형 전개 | 자주 쓰는 evidence role |
|---|---|---|
| 인문 | 개념 정의 → 관점 제시 → 논증 → 한계 | definition·claim·exception_limit |
| 사회 | 현상 → 원인 → 제도/모형 → 효과·한계 | cause_effect·condition_qualification |
| 과학기술 | 문제 → 원리 → 과정/메커니즘 → 변수·응용 | process_sequence·cause_effect |
| 예술 | 사조/작품 → 특징 → 해석 → 비교 | comparison_contrast·claim |

> 실증 주: 이 코퍼스 창(2017–2026 수능 독서)에서 인문·사회·과학기술은 독립
> 지문 세트로 확인됨. 예술은 독립 독서 지문으로는 관측되지 않았으나 교사
> 선택 분야로 지원한다(`data/empirical_aggregate.json` 참조).

## 문단·문장 골격

- 문단은 각기 하나의 기능(정의·원리·과정·비교·한계 등)을 맡는다.
- 문단 수·문장 길이 대역은 학년×난이도로 `06-grade-difficulty-map.md`가 정한다.
- **분류·나열만으로 채우지 않는다.** 관계(인과·조건·비교)와 논증을 넣어
  inference 이상 문항이 접지될 표면을 만든다.
- 지문 길이는 실증 코퍼스의 관측 최소~최대 봉투 안에 둔다(하한은 학년·demand로
  상향, 상한은 관측 최댓값에 고정).

## 사실 문장과 접지 (H1)

- 수치·연도·인명·고유명사·인용·인과 주장을 담은 문장은 `factual: true` +
  (B/C 모드에서) `sourceQuote`(원자료 축자 인용) 필수. `00-anti-hallucination.md`.

## 〈보기〉 박스 (schema `questions[].view`)

- 지문에 없는 외적 사례·조건·자료가 필요한 문항에만 `view`(제목+본문)를 단다.
- 〈보기〉는 `crosstext_integration`·`critical_evaluation` 문항의 통합 대상.
- 렌더에서 `<보기>`는 표 박스로 조판된다(`10-hwpx-mapping.md`).

## 밑줄 표지 (schema `sentences[].markers`)

- ㉠~㉤ 표지는 어휘·지시·특정 구절을 겨냥하는 문항용. 지문 집필 시
  `markers`(marker+정확한 span)로 심고, 대상은 렌더에서 굵게+밑줄된다.
- 밑줄 계획은 지문 개요 단계에서 미리 세운다(어떤 문항이 어느 표지를 쓸지).

## 근거(공개 문헌·자료)
- Meyer, B. J. F. (1985). Prose analysis.
- 비재구성 실증 집계: `docs/EMPIRICAL_ANALYSIS_2017_2026.md`, `docs/PROVENANCE.md`.
