# examples — 결정론적 테스트 픽스처

교사의 실시간 LLM 없이도 스크립트를 검증할 수 있는 고정 샘플. 도메인별로 나뉜다.

```
examples/
├── bimunhak/   비문학(독서)
└── unmun/      운문
```

## bimunhak/ — 비문학

| 파일 | 용도 |
|---|---|
| `sample_exam.json` | 유효 시험지(삼투/과학기술, 고2·상, 3문항). 검사 전부 통과. |
| `sample_exam_bad.json` | 의도적 위반본(축자 인용 불일치·근거 부족·정답/오답 중복·약한 오답). 게이트 거부 확인용. |
| `sample_output.html` | `render_html.py`의 골든 스냅샷(byte-stable). |
| `sample_exam.md` | `exam_to_hwpx.py`가 만든 HWPX용 마크다운. |
| `sample_exam.hwpx` | 마크다운→HWPX 변환 결과(왕복 파싱 검증됨). |
| `game_exam` · `game_full_exam` · `map_exam` · `philosophy_exam` · `tech_exam` | 추가 유효 샘플(분야·문항 수 변형). |

## unmun/ — 운문

| 파일 | 용도 |
|---|---|
| `jahwasang_exam.json` | 유효 시험지(윤동주 「자화상」, 고2·중, 3문항). **운문 게이트 전부 통과** — H1 작품 축자 일치 · H6 인용–해석 분리 · H7 저작권 근거 · 운문 근거 역할 · L3 유일성 프로브 결과 수록. |
| `jahwasang_exam_bad.json` | 의도적 위반본. **운문 게이트 6종이 실제로 발화하는지** 확인용 — H6 해석 누락 · H7 저작권 근거 누락 · 독서 역할(`cause_effect`) 오용 · 작품 오인용 · 외적 준거 날조 · 정답 전부 동일. |

> `jahwasang_exam.json`은 **저작권 만료작**을 쓴다(윤동주 1945년 사망, 1946.1.1 기산 사후 70년 →
> 2015.12.31 만료). 이 계산이 `sources[0].copyright.basis`에 기재돼 있고, 비어 있으면 H7이 거부한다.

## 검증 명령 (Windows PowerShell / Git Bash)

```bash
export PYTHONUTF8=1        # (PowerShell: $env:PYTHONUTF8=1)
S=plugins/korean-exam-writer/scripts

# T1 — 게이트: 통과 & 거부
python $S/validate_exam.py examples/bimunhak/sample_exam.json        # exit 0, ok:true
python $S/validate_exam.py examples/bimunhak/sample_exam_bad.json    # exit 1, ok:false + 위반 id
python $S/validate_exam.py examples/unmun/jahwasang_exam.json        # exit 0
python $S/validate_exam.py examples/unmun/jahwasang_exam_bad.json    # exit 1 + H6·H7·역할·오인용

# T2 — 조판
python $S/render_html.py  examples/unmun/jahwasang_exam.json -o out.html   # 운문은 verse 모드
python $S/exam_to_hwpx.py examples/unmun/jahwasang_exam.json -o out.hwpx   # 시행별 개행 유지

# T3 — L3 유일성 프로브 (LLM 왕복 필요)
python $S/probe_uniqueness.py examples/unmun/jahwasang_exam.json --emit > probes.json
#   각 prompt를 콜드 서브에이전트에 전달 → 응답을 results.json으로 정리
python $S/probe_uniqueness.py examples/unmun/jahwasang_exam.json --ingest results.json
```

## 골든 스냅샷 주의

`render_html.py`의 출력은 byte-stable해야 한다. 렌더러나 CSS를 고치면 스냅샷도 함께 갱신한다.
운문 지문은 **행갈이가 의미**이므로, `passage-body verse` 블록에서 연 수(`<p>`)와 행바꿈(`<br />`)이
보존되는지 CI가 확인한다.
