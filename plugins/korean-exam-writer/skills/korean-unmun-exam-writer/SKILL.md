---
name: korean-unmun-exam-writer
description: >-
  중·고등학교 국어 교사가 수능 국어 '운문(현대시·고전시가·갈래복합)' 문항·해설을 만들 때 사용한다.
  실제 시 작품을 지문으로 삼아 화자·심상·시상 전개·외적 준거 감상 문항을 학년(중1~고3)·세부
  난이도(하/중/상/최상)에 맞춰 출제하고, 인쇄용 2단 A4 시험지(HTML→PDF)와 한글(HWPX)로 출력한다.
  두 가지가 기계 게이트로 강제된다 — (1) 저작권: 작품은 저작권 만료작이거나 교사가 제공한 자료여야
  하며 만료 근거를 명시한다. (2) 근거: 정답 근거는 '축자 인용 스팬 + 해석'으로 분리해 인용은 기계가,
  해석은 교사가 검증한다. 트리거: "시 문제 출제", "현대시 문항 만들어", "고전시가 시험지",
  "운문 지문 문제", "<보기> 감상 문항", "갈래복합 출제", "화자 태도 문항", "시 모의고사".
  비문학(독서)은 korean-bimunhak-exam-writer를, 소설·수필 등 산문은 아직 지원하지 않는다.
---

# 국어 운문 시험지 생성기 (korean-unmun-exam-writer)

수능 국어형 **시 작품 → 문항 → 해설**을 만드는 스킬. `korean-bimunhak-exam-writer`의 설계를
상속하며, **상속·변경 목록은 [`references/20-verse-adaptation.md`](references/20-verse-adaptation.md)가
단일 출처다. 작업 시작 전에 20번을 먼저 읽어라.**

동작 원리는 비문학과 같다:
1. **오케스트레이션(분업)** — 오케스트레이터가 지휘하고 역할별 서브에이전트가 산출물을 만든다.
   생성자와 검증자를 분리한다.
2. **휴먼인더루프(대화형)** — 체크포인트마다 교사에게 묻고 승인받는다. 딸깍 X.

## ⛔ 최우선 원칙 (P0) — 두 개의 하드 게이트

### P0-A · 저작권 (운문 고유)
비문학은 지문을 **재구성**해 저작권을 피한다. 운문은 작품 원문을 그대로 싣기에 그 우회가 없다.

1. 작품은 **저작권 만료작**(`public_domain_work`) 또는 **교사가 적법하게 제공한 자료**
   (`teacher_material`)여야 한다.
2. 만료작은 `copyright.basis`에 **사망 연도와 계산**을 적는다. 비어 있으면 `validate_exam.py`가
   거부한다(H7).
3. 판단이 서지 않으면 **추측하지 말고 거부**한다 — 다른 작품을 제안하거나 교사에게 원문을 요청한다.
4. **LLM이 시를 창작해 지문으로 쓰지 않는다.** 정전성이 없어 감상 문항이 성립하지 않는다.
→ [`references/25-copyright-safety.md`](references/25-copyright-safety.md)

### P0-B · 근거 — 인용과 해석의 분리 (운문 고유)
산문에서는 인용이 곧 근거다. 운문에서는 **인용이 위치를 지목할 뿐 읽기를 확정하지 않는다.**

- `passageQuote` — 시행의 축자 스팬. **기계 검증**(H1).
- `interpretation` — 그 스팬을 선지에 잇는 읽기. **교사 검증**.

`demand`가 `recall`이 아닌 모든 문항에서 `interpretation`은 **필수**다(H6, 기계 게이트).
이걸 빼면 "인용은 맞는데 해석은 근거 없음"인 문항이 통과한다.
→ [`references/21-evidence-interpretation.md`](references/21-evidence-interpretation.md)

비문학의 P0(환각 금지, H1/H5)은 **그대로 적용**된다.
→ `../korean-bimunhak-exam-writer/references/00-anti-hallucination.md`

## 오케스트레이터로서의 진행 (당신 = 오케스트레이터)

각 역할은 서브에이전트에 위임하고(불가하면 역할 페르소나를 선언하며 순차 수행), 각 단계 산출물을
교사에게 제시하고 **⏸ 승인 체크포인트**를 거친다. ⏸에서는 교사 응답 전까지 진행하지 않는다.

- **CP1 · 교실 맥락 수집** ⏸ — 학년·난이도·문항 수·수업 목적. 빠진 항목만 2~4개씩 질문.
  (`../korean-bimunhak-exam-writer/references/09-classroom-context.md`)
- **CP2 · 작품 선정** ⏸ — (자료조사관) 갈래·주제에 맞는 후보 3편 제시. 각 후보에 **저작권 상태와
  문항 지탱력**(태도 변화·구조·상징·문체 표지 중 몇 개를 갖췄는지)을 함께 보고 → 교사 선택.
  (`23-genre-poetics.md` 작품 선정 기준)
- **CP3 · 저작권·원문 확인** ⏸(생략 불가) — 만료 근거 계산 또는 교사 자료 수령. **원문 정확성**도
  여기서 확인한다 — 행갈이·연 구분·표기가 저본과 일치하는지 교사에게 확인받는다.
  기억으로 복원한 시행을 그대로 쓰지 마라. (`25-copyright-safety.md`)
- **CP4 · 출제 설계 검토** ⏸ — (설계자) 유형(`type`)×인지요구(`demand`) 배분, ㉠~㉤ 표지 계획,
  `<보기>` 사용 여부와 유형, 근거 역할 배분 개요 제시 → 승인.
  (`01`·`02` 상속 + `21` 역할, `24-external-criterion.md`)
- **CP5 · 지문 확정** ⏸(생략 불가) — 시행 단위로 `sentences[]` 구성(`stanzaStart`로 연 구분),
  ㉠~㉤ 표지 삽입, 어휘 주석(고전시가) 확정 → 교사 확인. **행갈이는 의미이므로 재배치 금지.**
- **CP6 · 문항 검토** ⏸(생략 불가) — 슬롯을 나눠 **문항 병렬 출제(팬아웃)** → **팬인 일괄 검증**
  → 기계 게이트 → 문항+정답+해설+검증리포트 제시 → 승인(수정 시 해당 문항만 재생성·재게이트).
  오답은 `22-distractor-literary.md`의 8+1종에서 서로 다른 recipe로 뽑는다.
- **CP7 · 조판·출력** — (조립관) 스크립트로 HTML/HWPX 생성 후 무엇을 검증·제거했는지 요약 보고.

**기계 게이트가 최종 심판**: 주관적 "괜찮음"과 별개로 `validate_exam.py`가 exit 0이어야 조판한다.

## 검증 (CP6) — 3층

스크립트 경로는 이 SKILL.md 기준 `../../scripts/`다(플러그인 루트의 공유 코어).

| 층 | 명령 | 무엇을 보는가 | 지위 |
|---|---|---|---|
| **L1·L2** | `python ../../scripts/validate_exam.py exam.json` | 축자 인용(H1) · 오답 반증(H5) · 해석 필수(H6) · 저작권(H7) · 역할 도메인 · 세트 구조 | **필요조건.** exit 0 아니면 조판 금지 |
| **L3** | `python ../../scripts/probe_uniqueness.py exam.json --emit` | **정답 유일성** | 최종본 선언·export 직전 **필수** |

**L3 절차 (생략 불가)**
1. `--emit`으로 프로브를 받는다. 각 문항에서 **정답 선지가 제거된** 4선지가 나온다.
2. 각 프로브를 **콜드 서브에이전트**(`Agent(subagent_type: "general-purpose")`)에 넘긴다.
   같은 세션에서 역할만 바꾸면 정답이 이미 컨텍스트에 있어 검증이 원천 무효다.
3. 응답을 `results.json`으로 모아 `--ingest results.json --write`로 채점한다.
4. `verdict: picked`가 하나라도 나오면 **그 문항만** 재출제하고 재실행한다.

> **L3 PASS의 의미**: 유일성의 증명이 아니라 **반증 실패**다. 검증자와 출제자가 같은 오독을
> 공유하면 통과한다. 특히 감상 문항은 사람 검토가 여전히 필요하다. 이 한계를 교사에게 숨기지 마라.

## 조판·출력 (CP7)

- exam JSON은 `../../scripts/exam.schema.json` 형식. `meta.domain`을 **`"운문"`**으로 설정한다
  (이 값이 H6·H7·역할 도메인 게이트를 켠다).
- `python ../../scripts/render_html.py exam.json -o exam.html` → 2단 A4 HTML(Chrome에서 PDF 인쇄).
- `python ../../scripts/exam_to_hwpx.py exam.json -o exam.hwpx` → HWPX 조판.
  설치: `pip install -U 'python-hwpx>=3.2.0,<5' lxml`.
  **python-hwpx가 없으면 `--engine auto`가 claw-hwp로 폴백**해 마크다운 대신 진짜 `.hwpx`를 낸다(pip 불필요). 이때 지문의 흐르는 테두리만 빠지고 2단·표·조판 기호는 동일하다 → `10-hwpx-mapping.md`.
- 시험지 말머리 배너에 **작품 출처 고지**를 한 줄 덧붙인다(`25` 산출물 고지).

## 참조 파일

**운문 전용** — 작업 전 `20`을 먼저, 나머지는 필요할 때.

| 문서 | 언제 |
|---|---|
| [`20-verse-adaptation.md`](references/20-verse-adaptation.md) | **항상 먼저.** 상속·변경 목록 |
| [`21-evidence-interpretation.md`](references/21-evidence-interpretation.md) | 근거 작성 시(CP6) — 역할 8종·2필드·`v0` |
| [`22-distractor-literary.md`](references/22-distractor-literary.md) | 오답 작성 시(CP6) |
| [`23-genre-poetics.md`](references/23-genre-poetics.md) | 작품 선정·갈래 판단 시(CP2) |
| [`24-external-criterion.md`](references/24-external-criterion.md) | `<보기>` 문항 설계 시 |
| [`25-copyright-safety.md`](references/25-copyright-safety.md) | **CP3 필수** |

**비문학에서 상속** — `../korean-bimunhak-exam-writer/references/` 의
`00`(환각금지) · `01`(유형 7종) · `02`(demand) · `03`(오답 원리) · `06`(학년×난이도) ·
`08`(검증 체크리스트) · `09`(교실 맥락) · `10`(HWPX 매핑) · `12`(오케스트레이션) · `13`(대화형).

## 산출물 규격

`meta.domain: "운문"`, `meta.subjectField`는 `현대시` / `고전시가` / `갈래복합`.
각 문항은 `evidenceLocations[]`(축자 인용 + `demand≠recall`이면 `interpretation`),
`derivation[]`, `distractors[]`(recipe + whyFalse + 축자 인용)를 갖는다.
샘플: `../../examples/unmun/jahwasang_exam.json`.

## 하지 않는 것

- **산문(소설·극·수필)** — 서술자·시점·장면 전환은 이 스킬의 근거 역할 어휘로 담기지 않는다.
- **시 창작** — `23`의 "하지 말 것" 참조.
- **작품 임의 발췌·행갈이 변경** — 발췌 시 `[전략]`·`[후략]` 명시.
