#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_exam.py — machine verification gate (the P0 anti-hallucination enforcer).

Runs BOTH structural (JSON Schema, if `jsonschema` is installed) and semantic checks.
The core protection (H1/H5) is that every factual claim carries a VERBATIM quote that
must be a literal substring of its source — this is checked mechanically here, so
grounding cannot be faked by model self-attestation.

Exit code 0 = pass. Non-zero = fail; a JSON report is printed to stdout listing the
offending ids so a repair loop (or a human) can act.

Usage:
    python validate_exam.py path/to/exam.json [--schema path/to/exam.schema.json]
"""
import argparse
import json
import os
import re
import sys

# Force UTF-8 stdout so Korean text / em-dashes don't crash on Windows cp949 consoles.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))

# difficulty -> cognitive contract (근거·도출 최소치)
CONTRACT = {
    "하":   {"minEvidence": 1, "minDerivation": 1, "forbidSingleSentence": False},
    "중":   {"minEvidence": 2, "minDerivation": 2, "forbidSingleSentence": True},
    "상":   {"minEvidence": 2, "minDerivation": 2, "forbidSingleSentence": True},
    "최상": {"minEvidence": 3, "minDerivation": 3, "forbidSingleSentence": True},
}


def norm(s):
    """Whitespace-insensitive normalization for robust substring checks."""
    return re.sub(r"\s+", "", s or "")


def is_sub(needle, haystack):
    return norm(needle) in norm(haystack)


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def err(self, _id, rule, detail):
        self.errors.append({"id": _id, "rule": rule, "detail": detail})

    def warn(self, _id, rule, detail):
        self.warnings.append({"id": _id, "rule": rule, "detail": detail})

    def as_dict(self):
        return {
            "ok": len(self.errors) == 0,
            "errorCount": len(self.errors),
            "warningCount": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
        }


def schema_check(exam, schema_path, rep):
    try:
        import jsonschema  # type: ignore
    except Exception:
        rep.warn("_schema", "schema-skip",
                 "jsonschema 미설치 — 구조 스키마 검증 생략(의미 검증은 수행됨).")
        return
    try:
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
        jsonschema.validate(exam, schema)
    except FileNotFoundError:
        rep.warn("_schema", "schema-missing", f"스키마 파일 없음: {schema_path}")
    except Exception as e:  # jsonschema.ValidationError etc.
        rep.err("_schema", "schema-invalid", str(e).splitlines()[0][:300])


def validate(exam, schema_path):
    rep = Report()
    schema_check(exam, schema_path, rep)

    meta = exam.get("meta", {})
    difficulty = meta.get("difficulty", "중")
    mode = meta.get("sourceMode", "B_material")
    contract = CONTRACT.get(difficulty, CONTRACT["중"])

    # index sources
    sources = {s["sourceId"]: s for s in exam.get("sources", [])}

    # index passage sentences
    sent = {}          # sid -> text
    for p in exam.get("passages", []):
        for s in p.get("sentences", []):
            sent[s["sid"]] = s.get("text", "")

    # ---- H1: passage factual sentences grounded by verbatim source quote ----
    needs_grounding = mode in ("B_material", "C_research")
    for p in exam.get("passages", []):
        for s in p.get("sentences", []):
            sid = s.get("sid")
            if not s.get("factual"):
                continue
            sq = s.get("sourceQuote")
            src_id = s.get("sourceId")
            if needs_grounding and not sq:
                rep.err(sid, "H1-missing-sourceQuote",
                        "사실 문장에 sourceQuote(원자료 축자 인용)가 없음.")
                continue
            if sq:
                src = sources.get(src_id)
                if not src:
                    rep.err(sid, "H1-bad-sourceId",
                            f"sourceId '{src_id}' 가 sources에 없음.")
                elif not is_sub(sq, src.get("text", "")):
                    rep.err(sid, "H1-quote-not-substring",
                            f"sourceQuote가 원자료의 실제 부분문자열이 아님: '{sq[:40]}...'")
            # marker span must actually appear in the sentence
            for m in s.get("markers", []):
                if not is_sub(m.get("span", ""), s.get("text", "")):
                    rep.err(sid, "marker-span-missing",
                            f"밑줄 표지 {m.get('marker')} 대상 '{m.get('span')}' 가 문장에 없음.")

    # ---- questions ----
    seen_types = {}
    answer_indexes = []
    for q in exam.get("questions", []):
        qid = q.get("qid", "?")
        qtype = q.get("type")
        ai = q.get("answerIndex")
        answer_indexes.append(ai)

        # type distribution: no duplicate type in one exam
        if qtype in seen_types:
            rep.err(qid, "type-duplicate",
                    f"문항 유형 '{qtype}' 중복 (앞선 {seen_types[qtype]}). 유형은 겹치지 않게 배분해야 함.")
        else:
            seen_types[qtype] = qid

        # cognitive contract minimums
        ev = q.get("evidenceLocations", [])
        dv = q.get("derivation", [])
        if len(ev) < contract["minEvidence"]:
            rep.err(qid, "contract-evidence",
                    f"근거 {len(ev)}개 < 난이도 '{difficulty}' 최소 {contract['minEvidence']}개.")
        if len(dv) < contract["minDerivation"]:
            rep.err(qid, "contract-derivation",
                    f"도출 {len(dv)}단계 < 난이도 '{difficulty}' 최소 {contract['minDerivation']}단계.")
        if contract["forbidSingleSentence"] and len({e.get("passageRef") for e in ev}) < 2 and len(ev) >= 1:
            rep.warn(qid, "single-sentence-shortcut",
                     "근거가 한 문장에 몰려 있음(단일 문장 조회 지름길 우려).")

        # evidence quotes resolve (H1 chain: evidence.quote ⊆ passage sentence)
        for i, e in enumerate(ev):
            ref = e.get("passageRef")
            if ref not in sent:
                rep.err(qid, "evidence-ref-unresolved",
                        f"evidenceLocations[{i}].passageRef '{ref}' 가 지문에 없음.")
            elif not is_sub(e.get("passageQuote", ""), sent[ref]):
                rep.err(qid, "evidence-quote-not-substring",
                        f"evidenceLocations[{i}].passageQuote가 {ref} 문장의 부분문자열이 아님.")

        # choices / answer / distractor coverage
        choices = q.get("choices", [])
        if not (isinstance(ai, int) and 0 <= ai < len(choices)):
            rep.err(qid, "answer-index-range", f"answerIndex {ai} 범위 오류.")
        dists = q.get("distractors", [])
        d_idx = [d.get("index") for d in dists]
        if ai in d_idx:
            rep.err(qid, "answer-in-distractors",
                    f"정답 인덱스 {ai} 가 오답 목록에 포함됨(정답을 오답으로 표기).")
        expected = set(range(len(choices))) - {ai}
        if set(d_idx) != expected:
            rep.err(qid, "distractor-coverage",
                    f"오답 인덱스 {sorted([x for x in d_idx if x is not None])} 가 기대치 {sorted(expected)} 와 불일치.")

        # H5: each distractor's whyFalse must resolve to a contradicting passage quote
        weak = []
        for d in dists:
            di = d.get("index")
            ref = d.get("whyFalseRef")
            wq = d.get("whyFalseQuote", "")
            if ref not in sent or not is_sub(wq, sent.get(ref, "")):
                weak.append(di)
                rep.err(qid, "H5-whyFalse-unresolved",
                        f"오답 {di}의 반증 인용(whyFalseQuote)이 {ref} 문장에서 확인되지 않음 → 약한 오답.")
        if len(weak) >= 2:
            rep.err(qid, "weak-distractors",
                    f"약한 오답 {len(weak)}개(≥2) — 문항 재생성 필요. indexes={weak}")

    # answer spread (soft)
    if answer_indexes and len(set(answer_indexes)) == 1 and len(answer_indexes) >= 3:
        rep.warn("_set", "answer-monotone",
                 f"모든 정답이 {answer_indexes[0]}번으로 동일 — 정답 분산 권장.")

    # verification report must carry a disclaimer (H4)
    vr = exam.get("verificationReport", {})
    if not vr.get("disclaimer"):
        rep.err("_report", "H4-no-disclaimer",
                "verificationReport.disclaimer(교사 최종 검토 고지)가 없음.")

    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exam")
    ap.add_argument("--schema", default=os.path.join(HERE, "exam.schema.json"))
    args = ap.parse_args()

    with open(args.exam, encoding="utf-8") as f:
        exam = json.load(f)

    rep = validate(exam, args.schema)
    out = rep.as_dict()
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0 if out["ok"] else 1)


if __name__ == "__main__":
    main()
