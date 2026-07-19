# 01 · 문항 유형 taxonomy (내용 초점 7종)

> 독립 설계. 공개 문항작성 문헌(Haladyna·Downing·Rodriguez 2002)과 읽기 이해
> 구인(construct) 이론에서 도출했다.

## 설계 원칙 — 2축 분리

기존 관행은 인지과정·내용초점·지문역할을 **한 축에 뒤섞어** 유형이 서로
배타적이지 않았다(분류학 오류). 본 taxonomy는 두 축을 분리한다:

- **축 A — 내용 초점(`type`)**: 문항이 *무엇을* 묻는가 (아래 7종, 단일 차원).
- **축 B — 인지 요구(`demand`)**: *얼마나 깊은* 처리를 요구하는가 → `02-cognitive-contract.md`.
- **지문 역할**(가/나, 복수 지문)은 유형이 아니라 `evidenceLocations[].passageRef`가 담는다.
  → `part_a` 같은 값을 유형에 넣지 않는다.

한 문항은 정확히 하나의 `type`과 하나의 `demand`를 가진다. 난이도는 `type`이
아니라 `demand`와 근거 분산에서 나온다.

## 7종 (schema `questions.type`)

| type | 무엇을 묻나 | 전형적 demand | 근거(role) 경향 |
|---|---|---|---|
| `detail_check` | 지문에 명시된 세부 정보의 정오 | recall | definition·evidence_support |
| `structure_flow` | 글의 구조·전개 방식·서술 전략 | inference | comparison_contrast·process_sequence |
| `relation_reasoning` | 정보 간 관계(인과·조건·비교) 추론 | inference~integration | cause_effect·condition_qualification |
| `implicit_inference` | 함축·전제·생략된 정보 추론 | inference | claim·exception_limit |
| `crosstext_integration` | 〈보기〉·복수 자료·복수 지문 통합 적용 | integration~critique | claim·evidence_support |
| `critical_evaluation` | 논증 타당성·관점 비판·적절성 평가 | critique | claim·exception_limit |
| `context_vocabulary` | 문맥적 어휘·지시어·바꿔쓰기 | recall~inference | definition |

## 출제 규칙 (Haladyna 기반)

1. **단일 초점**: 한 문항은 한 가지 `type`만 겨눈다. 한 문항에서 두 초점을
   섞지 않는다.
2. **유형 다양성**: 한 세트는 최소 3종 이상의 `type`을 포함한다(암기 편중 방지).
3. **발문 다양화**: "적절한 것은?/적절하지 않은 것은?/알 수 있는 것은?/추론한
   내용으로 가장 적절한 것은?" 등 발문을 반복하지 않는다.
4. **부정 발문 표시**: 부정 발문(적절하지 *않은*)은 부정어를 굵게/밑줄로 명시.
5. **정답 유일성**: 정답은 정확히 하나. 나머지 4개는 `03-distractor-recipes.md`의
   오답 원리로 *그럴듯하되 명백히 틀린* 것.
6. **근거 접지**: 모든 문항은 `evidenceLocations[]`에 지문의 축자 인용을 단다
   (`04-evidence-roles.md`, `00-anti-hallucination.md`).

## 유형 × demand 짝짓기

`type`은 초점을, `demand`는 깊이를 정한다. 같은 `relation_reasoning`도 근거가
한 문단에 모이면 inference, 여러 문단·〈보기〉에 분산되면 integration이다. 세트
전체의 demand 분포는 `02`·`06`이 학년/난이도에 맞게 권고한다.

## 근거(공개 문헌)
- Haladyna, Downing, & Rodriguez (2002). A review of multiple-choice item-writing
  guidelines. *Applied Measurement in Education, 15*(3).
- AERA, APA, & NCME (2014). *Standards for Educational and Psychological Testing.*
