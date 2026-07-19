# 10 · HWPX 변환 (python-hwpx / hwpx-plugins)

한국 교사는 대부분 한글(HWP)을 쓰므로 `.hwpx` 출력을 지원한다.
**조판은 `python-hwpx`(hwpx-plugins 스택)로 직접 한다** — 마크다운→HWPX 단순 변환은 레이아웃이 깨지므로 쓰지 않는다.

## 방법: `hwpx.builder` 조립 → 인쇄 품질 후처리
`scripts/exam_to_hwpx.py`가 수행한다. PDF(HTML) 조판과 동일한 시각 요소를 맞춘다.
1. `hwpx.builder`로 OWPML 조립: A4, 머리글(제목·쪽번호)/꼬리글(page/total), 제목·발문·선택지.
2. **지문 박스 = 흐르는 문단 + 4면 연결 테두리** — 지문을 단일 셀 '표'에 넣으면 한글에서 표가
   신문식 2단 사이를 넘나들며 쪼개지지 못해, 한 단에 통째로 박히고 페이지를 넘으면 잘린다. 그래서
   지문은 '흐르는 문단'으로 조판하고, 그 문단들의 paraPr 테두리를 **4면 + `connect="1"`(문단 연결)**
   로 만든다(`_box_passage_paragraphs`). 연결 테두리는 텍스트를 따라 흐르므로, 지문이 단 안에서
   시작해 단→단→페이지로 이어지며 하나의 박스로 그려지고 **아무리 길어도 잘리지 않는다**(CSS의
   border가 흐르는 것과 동일). 표 박스는 단을 넘지 않는 교사용 검증표에만 쓴다. 밑줄 ㉠~㉤은
   문단 내 rich run으로 유지.
3. 후처리(`HwpxDocument`):
   - `set_paragraph_format(line_spacing_percent=165, spacing_after_pt=2)` — 본문 줄간격/문단 간격.
   - `set_paragraph_format(keep_with_next=True)` — **각 문항(발문+마지막 前 선택지)이 단·쪽 경계에서
     쪼개지지 않도록** 응집(문항당 5개 문단, 한 지문 3문항이면 keepWithNext=15).
   - `set_columns(2, col_type="NEWSPAPER", separator_type="SOLID")` — **2단 + 단 사이 구분선**.
4. `save_to_path`의 `hard_gates`(package_validation·document_errors·reopen·editor_open_safety)가
   모두 `pass`여야 한다 → 한글에서 변조 경고 없이 열림.

```bash
python scripts/exam_to_hwpx.py exam.json -o exam.hwpx            # 2단(기본)
python scripts/exam_to_hwpx.py exam.json -o exam.hwpx --columns 1
python scripts/exam_to_hwpx.py exam.json --md exam.md            # 마크다운만(대체)
```
설치: `python -m pip install -U python-hwpx lxml` (미설치 시 자동으로 .md 대체 저장).

## 매핑
| exam 요소 | HWPX 결과 |
|---|---|
| meta.title | 가운데 정렬 제목 + 머리글 |
| 지문 지시문 | 볼드 문단 |
| 지문 본문(문단) | paragraphStart 기준 문단 분리, 2단 흐름 |
| 밑줄 표지 ㉠~㉤ | 문장 내 표지+대상 |
| 발문 | 볼드 문단(번호 포함) |
| 5지선다 | ①~⑤ 문단 |
| `<보기>` | 별도 문단 |
| 교사용(정답·검증표·출처·고지) | PageBreak 후 별도 섹션(표 포함) — **배부 전 삭제** 안내 |

## 한계 / v2
- **keep-together:** v1은 `keepWithNext`로 문항 응집을 적용한다. 한글은 keepWithNext를 **단 응집엔
  존중하지만 쪽 경계는 미존중**할 수 있으므로, 오라클 측정 기반의 완전 수렴(columnBreak/pageBreak
  삽입)이 필요하면 `hwpx-mcp-server`의 `compose_exam` 경로를 쓴다. 참고: `hwpx-plugins/references/workflows-exam.md`.
- **시각 검증:** HWPX의 실제 화면 렌더는 한컴 한글이 필요하다(LibreOffice는 .hwpx 임포트 불가).
  구조 검증(하드 게이트·박스·2단·구분선·줄간격·keepWithNext·내용 보존)까지는 자동, 최종 화면 확인은 교사가 한글에서.
- 그림/표 자동 배치가 필요한 고급 문서는 `hwpx.builder`의 `Image`/`Table`를 확장한다.
