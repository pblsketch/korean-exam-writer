#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exam_to_hwpx.py — exam JSON -> real HWPX via python-hwpx (hwpx-plugins stack).

Layout is built with `hwpx.builder` (proper OWPML: A4 page, 머리글/꼬리글, 쪽번호,
styled 문단·표) and then switched to a **2-column newspaper layout** with
`HwpxDocument.set_columns(2)`. This produces a real 한글 시험지 that opens natively
without the broken layout you get from a naive Markdown->HWPX dump.

Requires:  python-hwpx >= 3.2.0, lxml   (pip install -U python-hwpx lxml)

Usage:
    python exam_to_hwpx.py exam.json -o exam.hwpx           # 2-column (default)
    python exam_to_hwpx.py exam.json -o exam.hwpx --columns 1
    python exam_to_hwpx.py exam.json --md exam.md           # markdown fallback only

Fallback: if python-hwpx is not installed, writes an .md and prints how to install.
"""
import argparse
import json
import logging
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# python-hwpx emits informational "manifest fallback" notes on stderr; quiet them.
logging.getLogger("hwpx").setLevel(logging.ERROR)
logging.disable(logging.WARNING)

CIRCLED = ["①", "②", "③", "④", "⑤"]

# 연(stanza) 사이 빈 줄용. 빈 문단은 텍스트 매칭 기반 테두리 패치에서 누락돼 connect 체인을
# 끊으므로, strip()에 지워지지 않는 ZWSP를 넣어 지문 박스가 하나로 이어지게 한다.
STANZA_GAP = "​"


def _norm_label(s):
    """공백을 무시한 라벨 비교용(예: '보 기' == '보기')."""
    return re.sub(r"\s+", "", s or "")


def _label_text(xml_fragment):
    """XML 조각에서 표시 텍스트만 뽑는다(태그 제거 + 엔티티 복원 + 공백 무시).

    section0.xml 안에서 `<보 기>`는 `&lt;보 기&gt;`로 이스케이프돼 있으므로
    엔티티를 되돌리지 않으면 라벨 비교가 빗나간다.
    """
    import html
    return _norm_label(html.unescape(re.sub(r"<[^>]+>", "", xml_fragment or "")))


def _is_view_label(norm_text):
    """이 문단이 <보기> 라벨인가. 본문과 섞이지 않도록 짧은 것만 인정한다."""
    return norm_text in ("<보기>", "〈보기〉", "보기")


def _is_verse(sentences):
    """Verse passages carry stanzaStart. A line break in verse is meaning, not layout."""
    return any(s.get("stanzaStart") for s in sentences)


def _paragraphs(sentences):
    """Group passage sentences into blocks: by paragraphStart (prose) or stanzaStart (verse)."""
    key = "stanzaStart" if _is_verse(sentences) else "paragraphStart"
    para, out = [], []
    for s in sentences:
        if s.get(key) and para:
            out.append(para); para = []
        para.append(s)
    if para:
        out.append(para)
    return out


# ---------------------------------------------------------------------------
# claw-hwp fallback engine
#
# python-hwpx가 없거나 그 API가 깨졌을 때(5.0.0에서 hwpx.builder가 제거된 전례)
# 마크다운으로 떨어지는 대신 진짜 .hwpx를 낸다. claw-hwp는 rhwp WASM을 vendoring해
# pip 설치가 필요 없으므로, 교사 배포에서 설치 장벽이 사라진다.
#
# 품질 차이 — 지문 박스의 구현 방식이 다르다.
#   python-hwpx: 흐르는 4면 연결 테두리(connect=1). 아무리 길어도 단·페이지를 넘어 이어진다.
#   claw-hwp   : 1×1 표. claw-hwp에는 문단 테두리 op가 없다. apply_paragraph_style로
#                배경 음영을 주는 우회는 paraPr을 오염시켜 지문 정렬을 무너뜨린다
#                (claw-hwp 문서가 '미검증 — paraPr sanitize concerns'로 표시한 그 문제. 실측 확인).
#                표는 쪼개지지 못하므로 한 단에 들어갈 분량일 때만 쓰고, 길면 평문단으로 흘린다.
#                셀은 runs를 못 받아 ㉠~㉤ 표지의 굵게·밑줄이 평문이 된다(표지 문자는 남는다).
# 2단·<보기> 표·조판 기호는 동일하다.
# ---------------------------------------------------------------------------

def find_claw_hwp():
    """Locate claw-hwp's scripts dir. Returns None if unavailable."""
    env = os.environ.get("CLAW_HWP_SCRIPTS")
    if env and os.path.isfile(os.path.join(env, "create.js")):
        return env
    import glob
    home = os.path.expanduser("~")
    pats = [
        os.path.join(home, ".claude", "plugins", "cache", "claw-hwp", "claw-hwp",
                     "*", "skills", "hwp", "scripts"),
        os.path.join(home, ".claude", "plugins", "marketplaces", "claw-hwp", "plugins",
                     "claw-hwp", "skills", "hwp", "scripts"),
    ]
    cands = []
    for p in pats:
        cands += [d for d in glob.glob(p) if os.path.isfile(os.path.join(d, "create.js"))]
    if not cands:
        return None
    return sorted(cands)[-1]          # highest version dir


def _p(text, bold=False, underline=False):
    return {"text": text, "bold": bold, "underline": underline}


def _claw_col_cm(columns, margin_mm=18, gap_mm=8, page_mm=210):
    """단 하나의 폭(cm). append_table 은 기본이 페이지 전폭이라 2단에서 넘친다."""
    text_mm = page_mm - 2 * margin_mm
    if columns and columns >= 2:
        text_mm = (text_mm - gap_mm * (columns - 1)) / columns
    return round(text_mm / 10.0 - 0.3, 1)          # 여유 3mm


def _claw_passage_boxable(p):
    """지문을 1×1 표(=박스)로 감쌀 수 있는가.

    claw-hwp 표는 단·페이지를 넘어 쪼개지지 못한다(`set_table_property`의 page_split은
    문서에만 있고 create.js/hwpx-edit.js 둘 다 미구현 — 실측). 그러므로 한 단 안에
    들어갈 분량일 때만 박스로 만들고, 길면 평문단으로 흘려 **잘리지 않게** 한다.

    또 셀 문자열은 `**bold**`/`*italic*`이 자동 파싱되므로, 지문에 리터럴 `*`(고전시가
    각주 관례)가 있으면 표를 쓰지 않는다 — 각주가 이탤릭으로 먹히는 쪽이 더 나쁘다.
    """
    sents = p.get("sentences", [])
    if any("*" in (s.get("text") or "") for s in sents):
        return False
    if _is_verse(sents):
        lines = len(sents) + max(0, len(_paragraphs(sents)) - 1)
    else:
        chars = sum(len(s.get("text") or "") for s in sents)
        lines = -(-chars // 26)          # 단 폭 기준 대략 26자/줄
    return lines <= 30


def _claw_ops(exam, columns=2):
    """exam JSON -> (create.js operations, 지문 박스 적용 여부).

    지문 박스는 1×1 표로 만든다. claw-hwp에는 문단 테두리 op가 없고,
    apply_paragraph_style(background_color)로 음영을 주는 방법은 paraPr을 오염시켜
    지문 정렬을 무너뜨린다(claw-hwp 문서가 '미검증 — paraPr sanitize concerns'로 표시한
    바로 그 문제. 실측 확인). 그래서 음영 대신 표를 쓰되, 쪼개지지 못하는 표의 한계를
    _claw_passage_boxable() 로 막는다.
    """
    m = exam.get("meta", {})
    ops = [{"type": "setup_document", "page_size": "a4", "margin_mm": 18}]
    col_cm = _claw_col_cm(columns)
    boxed = []

    def para(runs):
        ops.append({"type": "append_paragraph", "runs": runs})

    def line(t, bold=False):
        para([_p(t, bold=bold)])

    ops.append({"type": "append_heading", "level": 1, "text": m.get("title", "국어 시험지")})
    line(" · ".join(filter(None, [m.get("grade"), "난이도 " + (m.get("difficulty") or ""),
                                  m.get("subjectField"),
                                  "%d문항" % (m.get("questionCount") or 0)])))
    for p in exam.get("passages", []):
        if p.get("instruction"):
            line(p["instruction"], bold=True)
        if p.get("title"):
            line(("(%s) " % p["part"] if p.get("part") else "") + p["title"], bold=True)
        verse = _is_verse(p.get("sentences", []))
        groups = _paragraphs(p.get("sentences", []))

        if _claw_passage_boxable(p):
            # 지문 전체를 한 셀에 넣어 박스로 만든다. 셀 안에서 \n 은 줄바꿈으로 보존된다.
            blocks = []
            for group in groups:
                # 운문은 행이 의미이므로 개행으로, 산문은 한 문단이므로 공백으로 잇는다.
                # (공백 없이 이으면 '…현상이다.이때…'처럼 문장이 붙어 버린다.)
                joiner = "\n" if verse else " "
                blocks.append(joiner.join(_sentence_text(s) for s in group))
            ops.append({"type": "append_table",
                        "rows": [["\n\n".join(blocks) if verse else "\n".join(blocks)]],
                        "no_header": True, "col_widths_cm": [col_cm]})
            boxed.append(True)
        else:
            for gi, group in enumerate(groups):
                if verse:
                    if gi:
                        line("")
                    for s in group:
                        para([_p(t, bold=b, underline=u)
                              for t, b, u in _sentence_segments(s) if t])
                else:
                    para([_p(t, bold=b, underline=u)
                          for s in group for t, b, u in _sentence_segments(s) if t])
            boxed.append(False)
        line("")

    for q in exam.get("questions", []):
        line("%d. %s" % (q.get("number", 0), q.get("stem", "")), bold=True)
        v = q.get("view") or {}
        if v.get("text"):
            # <보기>는 짧아 단을 넘지 않으므로 표 박스로 안전하게 낼 수 있다.
            # 라벨은 **머리글 행**으로 넣어 본문 셀과 분리한다 — 그래야 라벨만 가운데
            # 정렬할 수 있다(라벨+본문을 한 셀 한 문단에 넣으면 정렬 단위가 하나가 된다).
            # 예전에 머리글 셀이 '<','보','기>' 로 세로로 찌그러졌던 것은 머리글 탓이 아니라
            # `col_widths_cm` 미지정으로 표가 내용 폭에 맞춰 좁아졌기 때문이다(실측).
            ops.append({"type": "append_table",
                        "headers": ["<보 기>"],
                        "rows": [[v["text"]]],
                        "col_widths_cm": [col_cm]})
        for i, c in enumerate(q.get("choices", [])):
            line("%s %s" % (CIRCLED[i] if i < len(CIRCLED) else str(i + 1), c))
        line("")

    line("── 교사용 ──", bold=True)
    line("정답: " + "   ".join("%d번 %s" % (q.get("number", 0),
                                          CIRCLED[q.get("answerIndex", 0)])
                              for q in exam.get("questions", [])))
    dis = (exam.get("verificationReport") or {}).get("disclaimer")
    if dis:
        line(dis)
    return ops, (all(boxed) if boxed else False)


def _clawhwp_center_view_label(path):
    """claw-hwp 산출물의 `<보 기>` 머리글 셀을 가운데 정렬한다.

    claw-hwp에는 셀 안 텍스트를 **수평** 정렬하는 op가 없다 — `set_cell_property`는
    `valign`(수직)만 받고, `apply_paragraph_style`은 본문 문단만 주소지정한다(셀 안 문단
    인덱스는 범위를 벗어난다. 실측). 그래서 생성 후 XML을 직접 손본다.
    python-hwpx 경로의 `_center_view_labels()`와 같은 취지이며, 그쪽은 이미 존재하는
    CENTER paraPr을 재사용하지만 claw-hwp 산출물에는 그런 paraPr이 없어 **복제**해서 만든다.

    실패해도 문서는 유효하므로(정렬만 왼쪽으로 남음) 조용히 넘어간다.
    """
    import shutil
    import tempfile
    import zipfile
    try:
        zin = zipfile.ZipFile(path)
        data = {i.filename: zin.read(i.filename) for i in zin.infolist()}
        zin.close()
        sec = data["Contents/section0.xml"].decode("utf-8")
        hdr = data["Contents/header.xml"].decode("utf-8")

        # 라벨이 든 셀 문단의 paraPr 수집. 표 셀(`<hp:tc>`) 안으로 범위를 좁혀야 한다 —
        # 표를 감싼 바깥 `<hp:p>`가 먼저 매칭되면 비탐욕 매칭이 셀 문단을 통째로 삼킨다.
        targets = set()
        for tc in re.findall(r"<hp:tc\b.*?</hp:tc>", sec, re.S):
            for pm in re.finditer(r'<hp:p\b[^>]*paraPrIDRef="(\d+)"[^>]*>(.*?)</hp:p>', tc, re.S):
                if _is_view_label(_label_text(pm.group(2))):
                    targets.add(pm.group(1))
        if not targets:
            return False

        ids = [int(x) for x in re.findall(r'<hh:paraPr\b[^>]*?\bid="(\d+)"', hdr)]
        next_id = max(ids) + 1 if ids else 0
        clones, mapping = [], {}
        for pp in sorted(targets):
            src = re.search(r'<hh:paraPr\b[^>]*?\bid="%s"[^>]*>.*?</hh:paraPr>' % pp, hdr, re.S)
            if not src:
                continue
            block = src.group(0)
            block = re.sub(r'\bid="%s"' % pp, 'id="%d"' % next_id, block, count=1)
            block = re.sub(r'<hh:align\b[^>]*?horizontal="\w+"',
                           lambda mm: mm.group(0).replace(
                               re.search(r'horizontal="(\w+)"', mm.group(0)).group(0),
                               'horizontal="CENTER"'), block, count=1)
            clones.append(block)
            mapping[pp] = str(next_id)
            next_id += 1
        if not clones:
            return False

        hdr = hdr.replace("</hh:paraProperties>", "".join(clones) + "</hh:paraProperties>", 1)
        hdr = re.sub(r'(<hh:paraProperties\b[^>]*\bitemCnt=")(\d+)(")',
                     lambda mm: mm.group(1) + str(int(mm.group(2)) + len(clones)) + mm.group(3),
                     hdr, count=1)

        def repoint(pm):
            pp = pm.group(1)
            if pp in mapping and _is_view_label(_label_text(pm.group(2))):
                return pm.group(0).replace('paraPrIDRef="%s"' % pp,
                                           'paraPrIDRef="%s"' % mapping[pp], 1)
            return pm.group(0)

        # 수정 범위도 셀 안으로 한정한다(바깥 문단이 같은 paraPr을 써도 건드리지 않게).
        sec = re.sub(r"<hp:tc\b.*?</hp:tc>",
                     lambda tm: re.sub(r'<hp:p\b[^>]*paraPrIDRef="(\d+)"[^>]*>(.*?)</hp:p>',
                                       repoint, tm.group(0), flags=re.S),
                     sec, flags=re.S)

        data["Contents/section0.xml"] = sec.encode("utf-8")
        data["Contents/header.xml"] = hdr.encode("utf-8")
        fd, tmp = tempfile.mkstemp(suffix=".hwpx")
        os.close(fd)
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            for name, blob in data.items():
                z.writestr(name, blob)
        shutil.move(tmp, path)
        return True
    except Exception:
        return False


def build_hwpx_clawhwp(exam, out_path, columns=2, scripts=None):
    """Render via claw-hwp. Returns a gates-like dict; raises RuntimeError on failure."""
    import subprocess
    import tempfile
    scripts = scripts or find_claw_hwp()
    if not scripts:
        raise RuntimeError("claw-hwp를 찾을 수 없음 (CLAW_HWP_SCRIPTS 환경변수로 지정 가능)")

    out_path = os.path.abspath(out_path)
    tmpdir = tempfile.mkdtemp(prefix="clawhwp_")
    stem = os.path.join(tmpdir, "exam")
    made = stem + ".hwpx"
    try:
        ops, passage_boxed = _claw_ops(exam, columns)
        payload = {"path": made, "theme": "government", "operations": ops}
        r = subprocess.run(["node", os.path.join(scripts, "create.js")],
                           input=json.dumps(payload, ensure_ascii=False),
                           capture_output=True, text=True, encoding="utf-8")
        res = json.loads((r.stdout or "").strip().splitlines()[-1])
        # exit code 0 even on op-level failure — the JSON status is the truth.
        if res.get("status") != "success":
            raise RuntimeError("claw-hwp create 실패: %s (op %s)"
                               % (res.get("message"), res.get("op_index")))

        gates = {"engine": "claw-hwp", "create": "pass",
                 "ops_applied": res.get("ops_applied")}

        gates["passage_box"] = "table" if passage_boxed else "none (지문이 한 단을 넘어 표로 감싸면 잘린다)"
        edits = []
        if columns and columns >= 2:
            # 다단도 create가 아니라 edit op다. 음영과 함께 한 번에 적용한다.
            edits.append({"type": "set_columns", "count": columns, "spacing_mm": 8})

        if edits:
            # 편집기는 항상 <stem>_edited.hwpx 로 쓴다(출력 경로 지정 불가).
            r2 = subprocess.run(["node", os.path.join(scripts, "hwpx-edit.js")],
                                input=json.dumps({"path": made, "operations": edits},
                                                 ensure_ascii=False),
                                capture_output=True, text=True, encoding="utf-8")
            e = json.loads((r2.stdout or "").strip())
            if not e.get("ok"):
                raise RuntimeError("claw-hwp 편집 실패: %s" % e.get("error"))
            edited = e.get("output")
            if not os.path.isabs(edited):
                edited = os.path.join(tmpdir, os.path.basename(edited))
            made = edited
            if columns and columns >= 2:
                gates["columns"] = "pass"

        import shutil
        # os.replace는 드라이브가 다르면 Windows에서 실패한다(temp=C:, 산출물=E: 등).
        d = os.path.dirname(out_path)
        if d:
            os.makedirs(d, exist_ok=True)
        shutil.move(made, out_path)
        gates["view_label_center"] = "pass" if _clawhwp_center_view_label(out_path) else "n/a"
        return gates
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def _sentence_text(s):
    t = s.get("text", "")
    for m in s.get("markers", []):
        span, marker = m.get("span", ""), m.get("marker", "")
        if span and span in t:
            t = t.replace(span, marker + span, 1)
    return t


def _sentence_segments(s):
    """Split one sentence into (text, bold, underline) segments.
    Marked spans -> 원문자 ㉠(굵게) + 대상(굵게+밑줄); rest is plain."""
    text = s.get("text", "")
    occ = []
    for m in s.get("markers", []):
        span, marker = m.get("span", ""), m.get("marker", "")
        idx = text.find(span)
        if span and idx >= 0:
            occ.append((idx, marker, span))
    occ.sort()
    segs, cur = [], 0
    for idx, marker, span in occ:
        if idx < cur:
            continue
        if idx > cur:
            segs.append((text[cur:idx], False, False))
        segs.append((marker, True, False))      # 원문자 ㉠ (굵게)
        segs.append((span, True, True))         # 대상: 굵게 + 밑줄
        cur = idx + len(span)
    segs.append(((text[cur:] if cur < len(text) else "") + " ", False, False))
    return segs


def build_hwpx(exam, out_path, columns=2):
    from hwpx.builder import (
        Document, Section, Paragraph, Run, Heading, Header, Footer,
        PageNumber, PageSize, Margins, Metadata, PageBreak,
    )
    from hwpx.document import HwpxDocument

    m = exam.get("meta", {})
    kids = []
    keep_texts = set()   # body paragraph texts that must keep_with_next (question cohesion)
    BODY = 10            # unified body font size (pt): 발문·선지·지문 all match

    # title block
    metaline = " · ".join(filter(None, [
        m.get("grade"), "난이도 " + m.get("difficulty", ""),
        m.get("subjectField"), "%d문항" % m.get("questionCount", 0)]))
    kids.append(Paragraph(align="center", children=[Run(m.get("title", "국어 시험지"), bold=True, size=15)]))
    kids.append(Paragraph(align="center", children=[Run(metaline, size=9, color="555555")]))
    kids.append(Paragraph(text=""))

    # passages — 지문은 '흐르는 문단'으로 조판하고, 그 문단들에 4면 '연결 테두리'를 입혀
    # 박스처럼 보이게 한다(후처리). 표가 아니므로 단 안에서 시작해 단→단→페이지로 자연스럽게
    # 흐르며, connect=1 테두리가 텍스트를 따라 하나의 박스로 이어진다(아무리 길어도 잘리지 않음).
    # 문항 참조 표현은 원문자 ㉠(굵게) + 대상(굵게+밑줄)로 표시한다.
    # 테두리 대상은 '지문 본문 문단'과 '<보기> 문단' 뿐이다. 제목·머리글 등과 텍스트가 겹치지
    # 않도록, 제목은 박스에 넣지 않고(중복이므로 생략) 본문 문단만 passage_texts로 수집한다.
    passage_texts = set()   # 지문 본문 문단 텍스트 (흐르는 문단 테두리 대상)
    view_boxes = []         # <보기> = 짧으므로 단을 안 넘음 → 단일 셀 표 BOX (기존 방식)
    for p in exam.get("passages", []):
        if p.get("instruction"):
            kids.append(Paragraph(children=[Run(p["instruction"], bold=True, size=BODY)]))
        verse = _is_verse(p.get("sentences", []))
        for gi, group in enumerate(_paragraphs(p.get("sentences", []))):
            if verse:
                # one paragraph per 시행 — the line break carries meaning
                if gi:
                    # 연 사이 빈 줄. 그냥 빈 문단을 넣으면 텍스트가 없어 _box_passage_paragraphs
                    # 의 매칭에서 빠지고, 그 지점에서 connect 체인이 끊겨 **연마다 박스가 하나씩**
                    # 생긴다. ZWSP(U+200B)는 str.strip()이 지우지 않으므로 매칭에 걸리면서도
                    # 눈에는 빈 줄로 보인다 → 지문 전체가 하나의 박스로 이어진다.
                    kids.append(Paragraph(text=STANZA_GAP))
                    passage_texts.add(STANZA_GAP)
                for s in group:
                    runs, plain = [], []
                    for txt, b, u in _sentence_segments(s):
                        if txt:
                            runs.append(Run(txt, bold=b, underline=u, size=BODY))
                            plain.append(txt)
                    kids.append(Paragraph(children=runs))
                    passage_texts.add("".join(plain).strip())
                continue
            runs, plain = [], []
            for s in group:
                for txt, b, u in _sentence_segments(s):
                    if txt:
                        runs.append(Run(txt, bold=b, underline=u, size=BODY))
                        plain.append(txt)
            kids.append(Paragraph(children=runs))
            passage_texts.add("".join(plain).strip())
        kids.append(Paragraph(text=""))

    # questions — stem + all-but-last-choice keep_with_next so a 문항 stays together.
    # 발문 is bold but SAME size as choices (BODY), not the title size.
    for q in exam.get("questions", []):
        stem_text = "%d. %s" % (q.get("number", 0), q.get("stem", ""))
        kids.append(Paragraph(children=[Run("%d. " % q.get("number", 0), bold=True, size=BODY),
                                        Run(q.get("stem", ""), bold=True, size=BODY)]))
        keep_texts.add(stem_text)
        v = q.get("view")
        if v:
            token = "%%%%VBOX%d%%%%" % q.get("number", len(view_boxes))
            kids.append(Paragraph(text=token))
            view_boxes.append((token, v))
        choices = q.get("choices", [])
        for i, c in enumerate(choices):
            mark = CIRCLED[i] if i < len(CIRCLED) else "%d)" % (i + 1)
            ctext = "%s %s" % (mark, c)
            kids.append(Paragraph(children=[Run(ctext, size=BODY)]))
            if i < len(choices) - 1:          # last choice may break; earlier ones stick
                keep_texts.add(ctext)
        kids.append(Paragraph(text=""))

    # teacher-only section (delete before distributing)
    kids.append(PageBreak())
    kids.append(Heading(level=2, text="[교사용] 정답 · 검증 · 출처 (배부 전 삭제)"))
    ans = "   ".join("%d번 %s" % (q.get("number", 0),
                     CIRCLED[q.get("answerIndex", 0)] if q.get("answerIndex", 0) < 5 else "?")
                     for q in exam.get("questions", []))
    kids.append(Paragraph(children=[Run("정답: ", bold=True), Run(ans)]))
    vr = exam.get("verificationReport", {})
    checks = vr.get("checks", [])
    if checks:
        # 2단에서 표는 단 폭(~83mm)에 갇히고 '상세' 열은 ~47mm밖에 못 받아 긴 문장이 잘린다.
        # 검증 리포트는 셀 정렬이 필요한 자료가 아니라 읽는 글이므로 문단으로 흘린다.
        kids.append(Paragraph(children=[Run("검증", bold=True, size=BODY)]))
        for c in checks:
            mark = "통과" if c.get("ok") else "위반"
            kids.append(Paragraph(children=[
                Run("· %s " % c.get("name", ""), bold=True, size=BODY),
                Run("[%s] " % mark, bold=True, size=BODY),
                Run(c.get("detail", ""), size=BODY)]))
    srcs = exam.get("sources", [])
    if srcs:
        kids.append(Paragraph(children=[Run("근거·출처", bold=True)]))
        for s in srcs:
            label = s.get("title") or s.get("sourceId")
            url = (" (%s)" % s["url"]) if s.get("url") else ""
            kids.append(Paragraph(children=[Run("[%s] %s%s" % (s.get("sourceId", ""), label, url), size=9)]))
    if vr.get("disclaimer"):
        kids.append(Paragraph(children=[Run("⚠ " + vr["disclaimer"], bold=True, color="C00000")]))

    doc = Document(
        metadata=Metadata(title=m.get("title", "국어 시험지"), author="exam-generator", organization=""),
        sections=[Section(
            page=PageSize.A4,
            margins=Margins(top_mm=15, right_mm=12, bottom_mm=16, left_mm=12),
            header=Header(children=[Paragraph(align="right",
                          children=[Run((m.get("title", "") + "  "), size=9), PageNumber()])]),
            footer=Footer(children=[Paragraph(align="center", children=[PageNumber(format="page/total")])]),
            children=kids)])

    report = doc.save_to_path(out_path)
    gates = getattr(report, "hard_gates", {})
    bad = [k for k, v in gates.items() if v != "pass"]
    if bad:
        raise RuntimeError("builder hard gates failed: %s (%s)" % (bad, gates))

    # --- post-process 1: line spacing, 문항 keep, 지문 4면 연결 테두리(흐르는 박스) ---
    d = HwpxDocument.open(out_path)
    paras = list(d.paragraphs)

    # 빌더가 상단에 남기는 '제목:/작성자:' 문서정보 줄 제거(시험지에는 불필요)
    for x in paras:
        t = (x.text or "").strip()
        if (t.startswith("제목:") or t.startswith("작성자:") or t.startswith("소속:")) and hasattr(x, "clear_text"):
            x.clear_text()

    # <보기> = 단일 셀 표 BOX (짧아서 단을 안 넘음 → 표로 안전). 단 너비로 인라인 배치.
    col_w = (52724 - 2268) // 2 if (columns and columns >= 2) else 52724
    for token, v in view_boxes:
        ph = next((x for x in d.paragraphs if (x.text or "").strip() == token), None)
        if ph is None:
            continue
        vbf = d.ensure_border_fill(active_borders=["left", "right", "top", "bottom"],
                                   border_color="#333333", border_width="0.2 mm")
        tbl = ph.add_table(1, 1, width=col_w, border_fill_id_ref=vbf)
        cp = list(tbl.cell(0, 0).paragraphs)[0]
        if hasattr(cp, "clear_text"):
            cp.clear_text()
        _vt = (v.get("title") or "").strip()
        # 제목이 사실상 '보기'면 라벨을 덧붙이지 않는다. 공백을 무시하고 비교해야 한다 —
        # 예제의 title은 '보 기'(가운데 공백)라서 예전 비교는 빗나갔고, 결과적으로 박스 안에
        # '<보기> 보 기'가 두 번 찍혔다.
        _cap = (" " + _vt) if _vt and _norm_label(_vt) not in ("보기", "<보기>", "〈보기〉") else ""
        cp.add_run("<보 기>" + _cap, bold=True, size=BODY)
        cp2 = tbl.cell(0, 0).add_paragraph()
        cp2.add_run(v.get("text", ""), size=BODY)
        if hasattr(ph, "clear_text"):
            ph.clear_text()

    paras = list(d.paragraphs)   # recompute after 보기 표 삽입

    def _match(texts):
        return [i for i, x in enumerate(paras) if (x.text or "").strip() in texts and (x.text or "").strip()]

    passage_idx = _match(passage_texts)
    box_idx = set(passage_idx)                          # 흐르는 테두리 대상 = 지문 본문 뿐
    keep_idx = [i for i in _match(keep_texts) if i not in box_idx]
    kset = set(keep_idx)
    other_idx = [i for i in range(len(paras)) if i not in box_idx and i not in kset]

    box_border_id = None
    all_box_texts = passage_texts
    if box_idx:
        box_border_id = d.ensure_border_fill(active_borders=["left", "right", "top", "bottom"],
                                             border_color="#333333", border_width="0.2 mm")
        d.set_paragraph_format(paragraph_indexes=passage_idx, bottom_border=True,
                               line_spacing_percent=160, spacing_after_pt=0,
                               first_line_indent_mm=3)
    if keep_idx:
        d.set_paragraph_format(paragraph_indexes=keep_idx, line_spacing_percent=165,
                               spacing_after_pt=2, keep_with_next=True)
    if other_idx:
        d.set_paragraph_format(paragraph_indexes=other_idx, line_spacing_percent=165,
                               spacing_after_pt=2)
    d.save_to_path(out_path)

    # 지문/보기 문단의 테두리를 4면 + 연결(connect=1)로 승격 → 흐르는 하나의 박스
    if box_border_id and all_box_texts:
        _box_passage_paragraphs(out_path, box_border_id, all_box_texts)

    # --- post-process 2: section-level N columns + passage-box width (raw XML surgery) ---
    # The builder emits a single section column control (colCount="1"). We flip that in
    # place so the WHOLE section is N-column (an inline set_columns control does not apply
    # section-wide in 한글). We also widen the single-cell 지문 box from the 1-inch default
    # to the actual column width so it fills the column instead of a tiny stub.
    _postprocess_columns_and_box(out_path, columns)
    if view_boxes:
        _center_view_label(out_path)

    # verify it still opens (editor-open safety proxy) after raw surgery
    HwpxDocument.open(out_path)
    return gates


def _box_passage_paragraphs(path, bf_id, passage_texts):
    """Upgrade the 지문 문단 border to a 4-side CONNECTED box (connect=1) referencing a
    4-side border-fill. A connected paragraph border flows with the text across columns and
    pages, so long passages render as one continuous box (unlike a table, which cannot break
    across newspaper columns)."""
    import os
    import re
    import shutil
    import tempfile
    import zipfile

    zin = zipfile.ZipFile(path)
    sec = zin.read("Contents/section0.xml").decode("utf-8")
    hdr = zin.read("Contents/header.xml").decode("utf-8")
    infos = zin.infolist()
    data = {i.filename: zin.read(i.filename) for i in infos}
    zin.close()

    # collect paraPrIDRefs used by 지문 문단 (matched by text)
    pps = set()
    for m in re.finditer(r'<hp:p\b[^>]*paraPrIDRef="(\d+)"[^>]*>(.*?)</hp:p>', sec, re.S):
        txt = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if txt and txt in passage_texts:
            pps.add(m.group(1))
    if not pps:
        return

    def fix_border(b):
        s = b.group(0)
        s = re.sub(r'borderFillIDRef="\d+"', 'borderFillIDRef="%s"' % bf_id, s)
        s = s.replace('connect="0"', 'connect="1"')
        for attr, val in (("offsetLeft", "500"), ("offsetRight", "500"),
                          ("offsetTop", "400"), ("offsetBottom", "400")):
            s = re.sub(r'%s="\d+"' % attr, '%s="%s"' % (attr, val), s)
        return s

    def fix_parapr(mm):
        return re.sub(r'<hh:border\b[^>]*/>', fix_border, mm.group(0))

    for pp in pps:
        hdr = re.sub(r'<hh:paraPr\b[^>]*?\bid="%s"[^>]*>.*?</hh:paraPr>' % pp,
                     fix_parapr, hdr, flags=re.S)

    data["Contents/header.xml"] = hdr.encode("utf-8")
    fd, tmp = tempfile.mkstemp(suffix=".hwpx")
    os.close(fd)
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for i in infos:
            zout.writestr(i, data[i.filename])
    shutil.move(tmp, path)


def _center_view_label(path):
    """Center the '<보기>' label line inside each 보기 표. Reassigns the label paragraph's
    paraPrIDRef to an existing CENTER-aligned paraPr so only the label (not the body) centers."""
    import os
    import re
    import shutil
    import tempfile
    import zipfile

    zin = zipfile.ZipFile(path)
    sec = zin.read("Contents/section0.xml").decode("utf-8")
    hdr = zin.read("Contents/header.xml").decode("utf-8")
    infos = zin.infolist()
    data = {i.filename: zin.read(i.filename) for i in infos}
    zin.close()

    # an existing CENTER-aligned paraPr id (title/metaline are center-aligned)
    center_ids = []
    for m in re.finditer(r'<hh:paraPr\b[^>]*?\bid="(\d+)"[^>]*>(.*?)</hh:paraPr>', hdr, re.S):
        if re.search(r'<hh:align\b[^>]*horizontal="CENTER"', m.group(2)):
            center_ids.append(m.group(1))
    if not center_ids:
        return
    center_id = center_ids[0]

    # within each single-cell 보기 표, set the FIRST cell paragraph (the '<보기>' label) to center
    def fix_tbl(tm):
        block = tm.group(0)
        if 'colCnt="1"' not in block:
            return block
        # first <hp:p> that contains '보기' -> reassign paraPrIDRef
        # 라벨이 '<보 기>'(가운데 공백)이므로 태그를 걷어낸 뒤 공백 무시하고 비교한다.
        def fix_p(pm):
            if "보기" not in _norm_label(re.sub(r"<[^>]+>", "", pm.group(0))):
                return pm.group(0)
            fix_p.done = getattr(fix_p, "done", False)
            if fix_p.done:
                return pm.group(0)
            fix_p.done = True
            return re.sub(r'paraPrIDRef="\d+"', 'paraPrIDRef="%s"' % center_id, pm.group(0), count=1)
        return re.sub(r'<hp:p\b.*?</hp:p>', fix_p, block, flags=re.S)

    sec = re.sub(r'<hp:tbl\b.*?</hp:tbl>', fix_tbl, sec, flags=re.S)

    data["Contents/section0.xml"] = sec.encode("utf-8")
    fd, tmp = tempfile.mkstemp(suffix=".hwpx")
    os.close(fd)
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for i in infos:
            zout.writestr(i, data[i.filename])
    shutil.move(tmp, path)


def _postprocess_columns_and_box(path, columns):
    import re
    import shutil
    import tempfile
    import zipfile

    SEC = "Contents/section0.xml"
    zin = zipfile.ZipFile(path, "r")
    xml = zin.read(SEC).decode("utf-8")

    # orientation: the builder writes an invalid landscape="PORTRAIT" enum which 한글
    # falls back to landscape. Real portrait docs use "WIDELY" (with width<height).
    xml = xml.replace('landscape="PORTRAIT"', 'landscape="WIDELY"')

    # page geometry (HWPUNIT). Read margins to compute the real text width.
    def _attr(pat, default):
        m = re.search(pat, xml)
        return int(m.group(1)) if m else default
    pw = _attr(r'<hp:pagePr[^>]*\bwidth="(\d+)"', 59528)
    ml = _attr(r'<hp:margin[^>]*\bleft="(\d+)"', 3402)
    mr = _attr(r'<hp:margin[^>]*\bright="(\d+)"', 3402)
    gap = 2268  # ~8pt column gap
    text_w = pw - ml - mr

    if columns and columns >= 2:
        col_w = (text_w - gap * (columns - 1)) // columns
        # Replace the builder's single-column control with an N-column one that carries a
        # visible divider line (<hp:colLine>) — the 2단 사이 중간 구분선.
        new_colpr = (
            '<hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="%d" sameSz="true" sameGap="%d">'
            '<hp:colLine type="SOLID" width="0.12 mm" color="#888888"/></hp:colPr>'
            % (columns, gap))
        xml, nsub = re.subn(r'<hp:colPr\b[^>]*?colCount="1"[^>]*?/>', new_colpr, xml, count=1)
        if nsub == 0:  # fallback: flip attrs in place if the element wasn't self-closing
            xml = re.sub(r'(<hp:colPr\b[^>]*?)\bcolCount="1"([^>]*?)\bsameGap="0"',
                         r'\1colCount="%d"\2sameGap="%d"' % (columns, gap), xml, count=1)
    # (지문은 문단 연결 테두리로 처리하므로 여기서 표를 손대지 않는다. <보기> 표는 인라인·단
    #  너비 그대로 두어 단 안에서 문항과 함께 흐르게 한다.)

    # rewrite the package with the edited section
    fd, tmp = tempfile.mkstemp(suffix=".hwpx")
    os.close(fd)
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == SEC:
                data = xml.encode("utf-8")
            zout.writestr(item, data)
    zin.close()
    shutil.move(tmp, path)


def to_markdown(exam):
    m = exam.get("meta", {})
    L = ["# %s" % m.get("title", "국어 시험지"),
         "_%s_" % " · ".join(filter(None, [m.get("grade"), "난이도 " + m.get("difficulty", ""),
                              m.get("subjectField"), "%d문항" % m.get("questionCount", 0)])), ""]
    for p in exam.get("passages", []):
        if p.get("instruction"):
            L.append("**%s**" % p["instruction"])
        if p.get("title"):
            L.append("### %s%s" % (("(%s) " % p["part"]) if p.get("part") else "", p["title"]))
        verse = _is_verse(p.get("sentences", []))
        for gi, group in enumerate(_paragraphs(p.get("sentences", []))):
            if verse:
                if gi:
                    L.append(">")                      # 연 사이 빈 줄
                for s in group:
                    L.append("> " + _sentence_text(s))  # 시행 1줄 = 마크다운 1줄
            else:
                L.append("> " + " ".join(_sentence_text(s) for s in group))
        L.append("")
    for q in exam.get("questions", []):
        L.append("**%d.** %s" % (q.get("number", 0), q.get("stem", "")))
        L.append("")
        for i, c in enumerate(q.get("choices", [])):
            L.append("%s %s  " % (CIRCLED[i] if i < 5 else str(i + 1), c))
        L.append("")
    L.append("---\n\n## [교사용] 정답 · 검증 · 출처 (배부 전 삭제)")
    L.append("**정답:** " + "   ".join("%d번 %s" % (q["number"], CIRCLED[q["answerIndex"]])
             for q in exam.get("questions", [])))
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exam")
    ap.add_argument("-o", "--out", help="output .hwpx path")
    ap.add_argument("--md", help="also/instead write markdown to this path")
    ap.add_argument("--columns", type=int, default=2, choices=[1, 2, 3])
    ap.add_argument("--engine", default="auto",
                    choices=["auto", "python-hwpx", "claw-hwp"],
                    help="auto: python-hwpx 우선, 없으면 claw-hwp, 둘 다 없으면 마크다운")
    args = ap.parse_args()

    with open(args.exam, encoding="utf-8") as f:
        exam = json.load(f)

    if args.md:
        with open(args.md, "w", encoding="utf-8", newline="\n") as f:
            f.write(to_markdown(exam))
        print("wrote %s" % args.md)

    if args.out:
        # 엔진 선택. auto = python-hwpx(최상: 흐르는 지문 테두리 + hard_gates)
        #            → claw-hwp(pip 불필요, 지문 테두리만 없음) → 마크다운.
        def _py_ok():
            try:
                import hwpx  # noqa
                from hwpx.builder import Paragraph  # noqa — 5.0.0에서 제거된 모듈
                return True
            except Exception:
                return False

        engine = args.engine
        if engine == "auto":
            engine = "python-hwpx" if _py_ok() else (
                "claw-hwp" if find_claw_hwp() else "md")

        if engine == "python-hwpx":
            gates = build_hwpx(exam, args.out, columns=args.columns)
            print("wrote %s (%d bytes, %d단, engine=python-hwpx)"
                  % (args.out, os.path.getsize(args.out), args.columns))
            print("hard_gates: %s" % {k: v for k, v in gates.items()})
        elif engine == "claw-hwp":
            try:
                gates = build_hwpx_clawhwp(exam, args.out, columns=args.columns)
            except RuntimeError as e:
                print("claw-hwp 엔진 실패: %s" % e, file=sys.stderr)
                print("설치: claude plugin marketplace add "
                      "https://github.com/DoHyun468/claw-hwp", file=sys.stderr)
                sys.exit(2)
            print("wrote %s (%d bytes, %d단, engine=claw-hwp)"
                  % (args.out, os.path.getsize(args.out), args.columns))
            print("gates: %s" % gates)
            print("주의: claw-hwp 경로에는 지문의 흐르는 4면 테두리가 없다 "
                  "(문단 테두리 op 부재). 나머지 조판은 동일하다.")
        else:
            fallback = os.path.splitext(args.out)[0] + ".md"
            with open(fallback, "w", encoding="utf-8", newline="\n") as f:
                f.write(to_markdown(exam))
            print("python-hwpx·claw-hwp 모두 없음 → 마크다운으로 대체 저장: %s" % fallback)
            print("설치: python -m pip install -U 'python-hwpx>=3.2.0,<5' lxml")
            print("또는: claude plugin marketplace add https://github.com/DoHyun468/claw-hwp")
            sys.exit(2)

    if not args.out and not args.md:
        ap.error("Provide -o (hwpx) and/or --md")


if __name__ == "__main__":
    main()
