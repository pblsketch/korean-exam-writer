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
        PageNumber, PageSize, Margins, Metadata, PageBreak, Table,
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
                    kids.append(Paragraph(text=""))      # 연 사이 빈 줄
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
        kids.append(Table(
            header=["항목", "결과", "상세"],
            rows=[[c.get("name", ""), "통과" if c.get("ok") else "위반", c.get("detail", "")] for c in checks],
            header_shading="EAF1FB", column_widths=[2, 1, 4]))
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
        _cap = (" " + _vt) if _vt and _vt not in ("보기", "<보기>", "〈보기〉") else ""
        cp.add_run("<보기>" + _cap, bold=True, size=BODY)
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
        def fix_p(pm):
            if "보기" not in pm.group(0):
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
    args = ap.parse_args()

    with open(args.exam, encoding="utf-8") as f:
        exam = json.load(f)

    if args.md:
        with open(args.md, "w", encoding="utf-8", newline="\n") as f:
            f.write(to_markdown(exam))
        print("wrote %s" % args.md)

    if args.out:
        try:
            import hwpx  # noqa
        except Exception:
            fallback = os.path.splitext(args.out)[0] + ".md"
            with open(fallback, "w", encoding="utf-8", newline="\n") as f:
                f.write(to_markdown(exam))
            print("python-hwpx 미설치 → 마크다운으로 대체 저장: %s" % fallback)
            print("설치: python -m pip install -U python-hwpx lxml")
            sys.exit(2)
        gates = build_hwpx(exam, args.out, columns=args.columns)
        print("wrote %s (%d bytes, %d단)" % (args.out, os.path.getsize(args.out), args.columns))
        print("hard_gates: %s" % {k: v for k, v in gates.items()})

    if not args.out and not args.md:
        ap.error("Provide -o (hwpx) and/or --md")


if __name__ == "__main__":
    main()
