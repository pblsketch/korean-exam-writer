# examples — 결정론적 테스트 픽스처

교사의 실시간 LLM 없이도 스크립트를 검증할 수 있는 고정 샘플.

| 파일 | 용도 |
|---|---|
| `sample_exam.json` | 유효 시험지(삼투/과학기술, 고2·상, 3문항). 6개 검사 전부 통과. |
| `sample_exam_bad.json` | 의도적 위반본(축자 인용 불일치·근거 부족·정답/오답 중복·약한 오답). 게이트 거부 확인용. |
| `sample_output.html` | `render_html.py`의 골든 스냅샷(byte-stable). |
| `sample_exam.md` | `exam_to_hwpx.py`가 만든 HWPX용 마크다운. |
| `sample_exam.hwpx` | 마크다운→HWPX 변환 결과(왕복 파싱 검증됨). |

## 검증 명령 (Windows PowerShell / Git Bash)
```bash
export PYTHONUTF8=1   # (PowerShell: $env:PYTHONUTF8=1)

# T1 — 게이트: 통과 & 거부
python scripts/validate_exam.py examples/sample_exam.json       # expect exit 0, ok:true
python scripts/validate_exam.py examples/sample_exam_bad.json   # expect exit 1, ok:false + 위반 id

# T2 — 조판 스냅샷 (byte 동일)
python scripts/render_html.py examples/sample_exam.json -o /tmp/out.html
diff examples/sample_output.html /tmp/out.html                  # 차이 없어야 함

# T3 — HWPX 직접 조판 (python-hwpx, 2단)
python -m pip install -U python-hwpx lxml   # 최초 1회
python scripts/exam_to_hwpx.py examples/sample_exam.json -o /tmp/exam.hwpx
#   hard_gates 전부 pass + colCount="2" 확인 → 한글에서 정상 열림
```
