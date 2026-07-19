# 04 · 근거 역할 (evidence roles, 8종)

> 독립 설계. 설명적 텍스트의 수사 구조 유형(Meyer의 text-structure 이론 등
> 공개 텍스트언어학)에서 도출. 각 근거 인용이 지문 안에서 **어떤 기능**을
> 하는지 분류해, 문항의 추론이 실제 지문 구조에 접지되도록 한다.

## 왜 근거에 역할을 다나

문항의 정답 근거는 지문의 특정 문장이다. 그 문장이 지문에서 하는 역할
(정의냐, 주장이냐, 인과냐)을 명시하면 (1) 출제자가 근거를 정확히 겨냥하고,
(2) 검토자가 문항-근거 정합을 확인하며, (3) 해설이 지문 구조를 설명할 수 있다.

## 8종 (schema `evidenceLocations[].role`)

| role | 지문에서의 기능 | 자주 쓰는 문항 type |
|---|---|---|
| `definition` | 개념·용어를 정의·규정 | detail_check·context_vocabulary |
| `claim` | 필자의 주장·명제·입장 | critical_evaluation·implicit_inference |
| `evidence_support` | 주장을 뒷받침하는 근거·예시·자료 | crosstext_integration·critical_evaluation |
| `cause_effect` | 원인-결과 관계 진술 | relation_reasoning |
| `comparison_contrast` | 대상 간 비교·대조 | structure_flow·relation_reasoning |
| `condition_qualification` | 조건·전제·단서·한정 | relation_reasoning·implicit_inference |
| `exception_limit` | 예외·한계·반례 | critical_evaluation·implicit_inference |
| `process_sequence` | 과정·절차·단계·시간 순서 | structure_flow (과학기술 필수) |

## 접지 규칙 (H1)

1. 각 `evidenceLocations[]`는 `passageRef`(지문 문장 id) + `passageQuote`
   (그 문장의 **축자 부분문자열**)를 가진다. `validate_exam.py`가 실제
   부분문자열인지 기계 검증한다.
2. 하나의 문항은 근거를 **1개 이상** 가진다. demand가 높을수록 근거가 여러
   문장·문단에 분산된다(`02-cognitive-contract.md`).
3. role은 근거 문장의 *실제 기능*과 일치해야 한다. 인과 문장을 `definition`으로
   태그하지 않는다.
4. `claim`/`evidence_support`는 논증형 지문(critique 문항)에서, `process_sequence`는
   과정 서술형 지문(과학기술)에서 특히 중요하다.

## 근거(공개 문헌)
- Meyer, B. J. F. (1985). Prose analysis: Purposes, procedures, and problems.
- Kintsch, W. (1998). *Comprehension: A Paradigm for Cognition.*
