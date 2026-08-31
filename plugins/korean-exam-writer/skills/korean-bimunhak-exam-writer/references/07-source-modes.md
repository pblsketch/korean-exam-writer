# 07 · 출처 모드 (source modes)

> 독립 설계. 생성형 AI 근거·출처 원칙(NIST AI RMF 생성형 프로파일, UNESCO
> 생성형 AI 교육 지침)에서 도출. 사실은 항상 축자 인용으로 접지된다.

## 3종 (schema `meta.sourceMode`)

| sourceMode | 의미 | `sources[].kind` | 접지 요구 |
|---|---|---|---|
| `A_textbook` | 교과서/기존 지문 **재구성** | `teacher_original` | 교사 원본을 sources에 저장, 사실 접지 |
| `B_material` | 교사 제공 자료 재구성 | `teacher_material` | 자료 축자 인용(`sourceQuote`) |
| `C_research` | AI 리서치 기반 지문 생성 | `web` | 검색 근거 축자 인용 + 출처 URL |

## 접지 원칙 (H1/H3)

1. **모든 사실 문장은 근거의 축자 인용을 단다.** `factual: true` 문장은
   (B/C에서) `sourceQuote`가 원자료의 실제 부분문자열이어야 하며
   `validate_exam.py`가 기계 검증한다(`00-anti-hallucination.md`).
2. **근거 없는 사실은 생성하지 않는다.** 수치·연도·인명·인용·인과를 근거 밖에서
   지어내지 않는다.

## C→B 강등 규칙 (H3, 생략 불가)

C 모드에서 검색 근거가 없거나 인용 불가한 주장이 나오면:
- 그 주장을 **거부**하고,
- 세트를 **B 모드로 강등**해 교사에게 자료를 요청한다.

근거를 못 대는 주제로 지문을 억지로 만들지 않는다. 이는 CP3(원본 출처 확인)
체크포인트에서 강제된다(`13-interactive-workflow.md`).

## 출처 기록

- `sources[]`에 `sourceId`·`kind`·`text`(+ C모드: `title`·`url`·`retrievedAt`)를
  남긴다. 지문의 `sourceQuote`·`sourceId`가 이를 가리킨다.
- 완성본에는 교사용 검증 리포트에 무엇을 어디서 가져왔는지 요약한다.

## 근거(공개 문헌)
- NIST (2024). *AI RMF: Generative AI Profile (NIST AI 600-1).*
- UNESCO (2023). *Guidance for generative AI in education and research.*
