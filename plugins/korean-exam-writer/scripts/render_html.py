#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_html.py — exam JSON -> self-contained, printable 2-column A4 HTML.

Pure standard library (no Jinja/no browser) so it runs anywhere with zero installs.
Output is byte-stable (no timestamps, deterministic ordering) for snapshot testing.
The student sheet is the printed view; the teacher-only block (answer key +
verification report + sources) is shown on screen but hidden by @media print.

Usage:
    python render_html.py exam.json -o out.html
"""
import argparse
import html
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
CSS_PATH = os.path.join(HERE, "..", "assets", "templates", "exam.css")

CIRCLED = ["①", "②", "③", "④", "⑤"]


def esc(s):
    return html.escape(s or "", quote=True)


def render_sentence(s):
    """Render a sentence, injecting underline + marker at each marker span."""
    text = s.get("text", "")
    # Apply markers by wrapping the first occurrence of each span.
    for m in s.get("markers", []):
        span = m.get("span", "")
        marker = m.get("marker", "")
        if span and span in text:
            wrapped = '<span class="marker">%s</span><u>%s</u>' % (esc(marker), esc(span))
            # escape the rest around the span: split once
            idx = text.index(span)
            before = esc(text[:idx])
            after = esc(text[idx + len(span):])
            return before + wrapped + after
    return esc(text)


def render_passage(p):
    out = ['<div class="passage-block">']
    if p.get("instruction"):
        out.append('<div class="passage-instruction">%s</div>' % esc(p["instruction"]))
    if p.get("title"):
        part = p.get("part") or ""
        prefix = ("(%s) " % part) if part else ""
        out.append('<div class="passage-title">%s%s</div>' % (esc(prefix), esc(p["title"])))
    # Verse: a line break is meaning, not layout. Any stanzaStart in the passage switches
    # the whole block to verse mode — lines are kept, never re-flowed into a paragraph.
    sentences = p.get("sentences", [])
    verse = any(s.get("stanzaStart") for s in sentences)
    out.append('<div class="passage-body%s">' % (" verse" if verse else ""))
    # group sentences into paragraphs by paragraphStart (prose) / stanzaStart (verse)
    key = "stanzaStart" if verse else "paragraphStart"
    para = []
    paras = []
    for s in sentences:
        if s.get(key) and para:
            paras.append(para)
            para = []
        para.append(s)
    if para:
        paras.append(para)
    joiner = "<br />" if verse else " "
    for group in paras:
        out.append("<p>" + joiner.join(render_sentence(s) for s in group) + "</p>")
    out.append("</div></div>")
    return "".join(out)


def render_question(q):
    out = ['<div class="question">']
    out.append('<div class="stem"><span class="num">%d.</span>%s</div>'
               % (q.get("number", 0), esc(q.get("stem", ""))))
    v = q.get("view")
    if v:
        _vt = (v.get("title") or "").strip()
        _cap = (" " + _vt) if _vt and _vt not in ("보기", "<보기>", "&lt;보기&gt;", "〈보기〉") else ""
        out.append('<div class="view-box"><div class="view-title">&lt;보기&gt;%s</div><div>%s</div></div>'
                   % (esc(_cap), esc(v.get("text", ""))))
    out.append('<ul class="choices">')
    for i, c in enumerate(q.get("choices", [])):
        mark = CIRCLED[i] if i < len(CIRCLED) else str(i + 1)
        out.append("<li>%s %s</li>" % (mark, esc(c)))
    out.append("</ul></div>")
    return "".join(out)


def render_teacher_block(exam):
    out = ['<div class="teacher-only">']
    out.append("<h2>정답 (교사용 · 인쇄 시 자동 숨김)</h2>")
    ans = []
    for q in exam.get("questions", []):
        ai = q.get("answerIndex", 0)
        mark = CIRCLED[ai] if ai < len(CIRCLED) else str(ai + 1)
        ans.append("%d번 %s" % (q.get("number", 0), mark))
    out.append('<div class="answer-key">%s</div>' % esc("   ".join(ans)))

    out.append("<h2>검증 리포트</h2>")
    vr = exam.get("verificationReport", {})
    out.append("<ul>")
    for c in vr.get("checks", []):
        cls = "ok" if c.get("ok") else "bad"
        detail = (" — " + c["detail"]) if c.get("detail") else ""
        out.append('<li class="report-check %s">%s%s</li>' % (cls, esc(c.get("name", "")), esc(detail)))
    out.append("</ul>")
    removed = vr.get("removedItems") or []
    if removed:
        out.append("<div>제거·수정된 항목: %s</div>" % esc(", ".join(removed)))
    flags = vr.get("lowConfidenceFlags") or []
    if flags:
        out.append("<div>확인 필요(저신뢰): %s</div>" % esc(", ".join(flags)))

    srcs = exam.get("sources", [])
    if srcs:
        out.append("<h2>근거·출처</h2><ol class='sources-list'>")
        for s in srcs:
            label = s.get("title") or s.get("sourceId")
            url = (" (%s)" % s["url"]) if s.get("url") else ""
            out.append("<li>[%s] %s%s</li>" % (esc(s.get("sourceId", "")), esc(label), esc(url)))
        out.append("</ol>")

    out.append('<div class="disclaimer">%s</div>' % esc(vr.get("disclaimer", "")))
    out.append("</div>")
    return "".join(out)


def render(exam, css_text):
    meta = exam.get("meta", {})
    metaline = " · ".join(filter(None, [
        meta.get("grade"), "난이도 " + meta.get("difficulty", ""),
        meta.get("subjectField"), "%d문항" % meta.get("questionCount", 0)]))
    body = ['<div class="sheet">']
    body.append('<div class="exam-header"><p class="title">%s</p><p class="meta">%s</p></div>'
                % (esc(meta.get("title", "국어 시험지")), esc(metaline)))
    body.append('<div class="no-print"><button onclick="window.print()">🖨 학생용 인쇄(PDF)</button>'
                ' &nbsp; 화면의 빨간 점선 아래 정답·검증 리포트는 인쇄 시 자동으로 빠집니다.</div>')
    body.append('<div class="columns">')
    for p in exam.get("passages", []):
        body.append(render_passage(p))
    for q in exam.get("questions", []):
        body.append(render_question(q))
    body.append("</div>")
    body.append(render_teacher_block(exam))
    body.append("</div>")

    return (
        "<!DOCTYPE html>\n"
        '<html lang="ko"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>%s</title>\n<style>\n%s\n</style>\n</head>\n<body>\n%s\n</body></html>\n"
        % (esc(meta.get("title", "국어 시험지")), css_text, "\n".join(body))
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exam")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--css", default=CSS_PATH)
    args = ap.parse_args()

    with open(args.exam, encoding="utf-8") as f:
        exam = json.load(f)
    try:
        with open(args.css, encoding="utf-8") as f:
            css_text = f.read().rstrip("\n")
    except FileNotFoundError:
        css_text = "/* css not found */"

    out_html = render(exam, css_text)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(out_html)
    print("wrote %s (%d bytes)" % (args.out, len(out_html.encode("utf-8"))))


if __name__ == "__main__":
    main()
