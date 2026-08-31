# 21 · 근거 역할 8종과 인용–해석 분리

> 독서의 `04-evidence-roles.md`를 운문으로 대체하는 문서. 역할 어휘와 2필드 규약을 정한다.

## 왜 2필드인가

운문 문항의 근거는 두 층이다.

```json
{
  "passageRef": "p8",
  "role": "speaker_attitude",
  "passageQuote": "돌아가다 생각하니 그 사나이가 가엾어집니다",
  "interpretation": "미움으로 떠났다가 연민으로 돌아서는 전환이 같은 행 안에서 일어난다. 대상을 밀어냈다가 다시 끌어당기는 왕복이 화자의 자기 인식 과정을 이룬다."
}
```

- **`passageQuote`** — 시행의 축자 스팬. `validate_exam.py`가 부분문자열인지 **기계로** 확인한다.
  지어낼 수 없다.
- **`interpretation`** — 그 스팬이 왜 이 선지를 지지하는지. 기계가 판정할 수 없고, **교사가 읽고
  동의하거나 반려한다.**

이 분리가 하는 일은 **책임 소재를 명확히 하는 것**이다. 인용이 틀리면 기계가 잡고, 읽기가 틀리면
사람이 잡는다. 하나로 뭉뚱그리면 둘 다 아무도 안 잡는다.

**금지**: `interpretation`에 감상문을 쓰지 마라. "아름다운 성찰의 시"는 근거가 아니다.
**스팬 → 선지 진술**을 잇는 한두 문장만 쓴다.

## 운문 근거 역할 8종 (schema `evidenceLocations[].role`)

| role | 무엇을 근거로 삼는가 | 전형적 type |
|---|---|---|
| `speaker_attitude` | 화자의 정서·태도와 그 변화 | `implicit_inference` |
| `imagery_sensory` | 감각적 심상(시각·청각·촉각·공감각) | `detail_check` |
| `figurative_symbol` | 비유·상징·알레고리 | `relation_reasoning` |
| `tone_diction` | 어조·시어 선택·종결 어미·경어체 | `detail_check`·`context_vocabulary` |
| `structure_repetition` | 반복·대구·수미상관·시상 전개 | `structure_flow` |
| `situation_setting` | 시적 상황·배경·화자의 처지 | `detail_check` |
| `theme_statement` | 주제 의식이 직접 드러난 시행 | `critical_evaluation` |
| `external_criterion` | `<보기>`의 비평·창작 배경 (`passageRef: "v0"`) | `crosstext_integration` |

`validate_exam.py`가 독서 역할(`definition`·`cause_effect` 등)을 운문 문항에서 발견하면
**거부**한다. 시를 설명문처럼 읽고 있다는 신호이기 때문이다.

## 역할과 demand의 관계

근거 역할은 난이도를 정하지 않는다. 난이도는 여전히 **근거의 분산**에서 나온다(`02`와 동일).

- 한 시행 안에서 끝나면 → `recall`~`inference`
- 여러 연에 흩어지면 → `inference`~`integration`
- 시행 + `<보기>` 외적 준거를 함께 요구하면 → `integration`
- 감상의 타당성 자체를 평가하면 → `critique`

## `v0` 참조 — `<보기>`를 근거로 쓰기

외적 준거 감상 문항에서는 근거의 절반이 지문 밖에 있다. `passageRef`에 `v0`을 쓰면 그 문항의
`view.text`를 참조한다. 인용 검증은 동일하게 걸린다.

```json
{"passageRef": "v0", "role": "external_criterion",
 "passageQuote": "우물은 자연을 함께 담아 내면을 비추는 거울로 기능한다",
 "interpretation": "<보기>가 제시한 거울 기능을, 자연물 나열 끝에 사나이가 놓이는 마지막 연의 배치가 시행 차원에서 구현한다."}
```

**규칙**: 외적 준거 문항은 `v0` 근거 1개 이상 + 지문 시행 근거 1개 이상을 **둘 다** 가져야 한다.
`<보기>`만 읽고 풀리면 그것은 시를 묻는 문항이 아니다.

## 체크리스트

- [ ] `demand ≠ recall`인 모든 근거에 `interpretation`이 있다. (기계, H6)
- [ ] `interpretation`이 감상이 아니라 스팬–선지 연결이다. (사람)
- [ ] `role`이 운문 8종 안에 있다. (기계)
- [ ] 외적 준거 문항에 `v0` 근거와 시행 근거가 모두 있다. (사람)
- [ ] 인용 스팬이 문항 간 중복되지 않는다 — 같은 시행으로 두 문항을 만들면 독립성이 무너진다.
