#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_uniqueness.py — L3 leave-one-out 정답 유일성 반증 게이트.

validate_exam.py의 H5(`whyFalseQuote`)는 "각 오답이 지문으로 **반증 가능한가**"를 검사한다.
강력하지만 한계가 있다 — 그 반증 인용을 **출제자 자신이 써낸다.** 오답이 사실은 참인 경우
(복수정답)를 출제자가 못 알아보면, H5는 그 오답에 그럴듯한 반증 인용을 붙인 채 통과한다.

이 스크립트는 그 사각지대를 겨눈다. **정답 선지를 제거한** 나머지 4개만 제시하고
"이 중 정답이 있는가?"를 묻는다. 정답이 정말 유일했다면 답은 "없음"이어야 한다.
누군가를 고른다면 그것이 복수정답 후보다.

핵심은 목적함수의 비대칭이다. 출제자는 "그럴듯한 오답 만들기"를 수행하며 "이 오답이 참인가?"를
한 번도 묻지 않는다. 프로브는 정확히 그것만 묻는다. 같은 모델이어도 검사는 독립적이다.

**PASS의 의미**: 유일성의 증명이 아니라 **반증 실패**다. 검증자와 출제자가 같은 오독을 공유하면
통과한다. 이 스크립트는 반증을 1회 시도할 뿐이며, 교사의 최종 검토를 대체하지 않는다.

LLM을 직접 호출하지 않는다(이 도구는 서버·API 키 없이 교사의 모델 위에서 돈다).
오케스트레이터가 --emit으로 프롬프트를 받아 **콜드 서브에이전트**에 넘기고, 그 답을 --ingest로 되먹인다.

Usage:
    # 1) 프로브 발행 → 콜드 서브에이전트에 전달
    python probe_uniqueness.py exam.json --emit > probes.json

    # 2) 서브에이전트 답변을 results.json으로 정리한 뒤 채점 (exit 1 = 복수정답 후보 발견)
    python probe_uniqueness.py exam.json --ingest results.json --write

results.json 형식:
    [{"qid": "Q1", "verdict": "none"},
     {"qid": "Q2", "verdict": "picked", "pickedIndex": 2, "note": "④도 지문과 일치한다"}]
"""
import argparse
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

CIRCLED = ["①", "②", "③", "④", "⑤"]

INSTRUCTION = """너는 수능 국어영역 수험생이다. 아래 지문을 읽고 문항에 답하라.

**가장 중요한 지시:** 선택지 중에 **정답이 아예 없을 수 있다.** 억지로 하나를 고르지 마라.
지문에 비추어 "이것은 확실히 옳다"고 말할 수 있는 선택지가 없으면 반드시 **"없음"**이라고 답하라.
넷 중 가장 그럴듯한 것을 고르는 과제가 아니라, 옳은 것이 있는지 없는지를 판정하는 과제다.

답변은 `<번호> 또는 없음` + 근거 한 문장으로만 하라."""


def render_passages(exam):
    out = []
    for p in exam.get("passages", []):
        head = p.get("title") or p.get("subject") or ""
        part = p.get("part") or ""
        label = f"({part}) {head}".strip() if part else head
        if label:
            out.append(f"[{label}]")
        buf = []
        for s in p.get("sentences", []):
            if (s.get("paragraphStart") or s.get("stanzaStart")) and buf:
                out.append("".join(buf) if not s.get("stanzaStart") else "\n".join(buf))
                buf = []
            buf.append(s.get("text", ""))
        if buf:
            # verse keeps line breaks; prose re-flows into a paragraph
            joiner = "\n" if any(s.get("stanzaStart") for s in p.get("sentences", [])) else ""
            out.append(joiner.join(buf))
    return "\n\n".join(out)


def build_probes(exam):
    """Emit one leave-one-out probe per question: correct choice removed, rest renumbered."""
    passage = render_passages(exam)
    probes = []
    for q in exam.get("questions", []):
        ai = q.get("answerIndex")
        choices = q.get("choices", [])
        if not isinstance(ai, int) or not (0 <= ai < len(choices)):
            continue
        rest = [c for i, c in enumerate(choices) if i != ai]
        kept = [i for i in range(len(choices)) if i != ai]  # probe pos -> original index
        lines = [INSTRUCTION, "", "## 지문", "", passage, "", "## 문항", "", q.get("stem", "")]
        view = q.get("view") or {}
        if view.get("text"):
            lines += ["", f"> **<{view.get('title', '보 기')}>**", ">", f"> {view['text']}"]
        lines.append("")
        lines += [f"{CIRCLED[i]} {c}" for i, c in enumerate(rest)]
        probes.append({
            "qid": q.get("qid"),
            "number": q.get("number"),
            "removedIndex": ai,
            "probeToOriginal": kept,
            "prompt": "\n".join(lines),
        })
    return probes


def score(exam, results, probes):
    """A 'picked' verdict means a distractor reads as correct → multiple-answer candidate."""
    out, failed = [], []
    seen = {r.get("qid"): r for r in results}
    for p in probes:
        r = seen.get(p["qid"])
        if r is None:
            out.append({"qid": p["qid"], "verdict": "picked",
                        "note": "프로브 응답 없음 — 미검증을 통과로 취급하지 않는다."})
            failed.append(p["qid"])
            continue
        v = (r.get("verdict") or "").strip().lower()
        if v in ("none", "없음"):
            out.append({"qid": p["qid"], "verdict": "none"})
            continue
        pi = r.get("pickedIndex")
        entry = {"qid": p["qid"], "verdict": "picked"}
        if isinstance(pi, int) and 0 <= pi < len(p["probeToOriginal"]):
            entry["pickedIndex"] = p["probeToOriginal"][pi]  # map back to original numbering
        if r.get("note"):
            entry["note"] = r["note"]
        out.append(entry)
        failed.append(p["qid"])
    return out, failed


def main():
    ap = argparse.ArgumentParser(description="L3 leave-one-out uniqueness probe.")
    ap.add_argument("exam")
    ap.add_argument("--emit", action="store_true", help="프로브 프롬프트를 JSON으로 출력")
    ap.add_argument("--ingest", metavar="RESULTS", help="서브에이전트 응답 JSON을 채점")
    ap.add_argument("--write", action="store_true",
                    help="--ingest 결과를 exam.json의 verificationReport.uniquenessProbe에 기록")
    a = ap.parse_args()

    with open(a.exam, encoding="utf-8") as f:
        exam = json.load(f)
    probes = build_probes(exam)

    if a.emit:
        print(json.dumps({"probes": probes}, ensure_ascii=False, indent=2))
        return 0

    if not a.ingest:
        ap.error("--emit 또는 --ingest 중 하나가 필요합니다.")

    with open(a.ingest, encoding="utf-8") as f:
        results = json.load(f)
    if isinstance(results, dict):
        results = results.get("results", [])

    scored, failed = score(exam, results, probes)
    report = {"ran": True, "results": scored}

    if a.write:
        exam.setdefault("verificationReport", {})["uniquenessProbe"] = report
        with open(a.exam, "w", encoding="utf-8") as f:
            json.dump(exam, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "ok": not failed,
        "checked": len(probes),
        "multipleAnswerCandidates": failed,
        "uniquenessProbe": report,
        "note": "PASS는 유일성의 증명이 아니라 반증 실패다. 교사 검토를 대체하지 않는다.",
    }, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
