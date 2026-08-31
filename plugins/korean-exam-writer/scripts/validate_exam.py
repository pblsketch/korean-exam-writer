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

# domain -> allowed evidence roles. Cross-domain use is a design error, not a preference:
# Meyer text-structure roles describe expository prose; poetic roles describe verse.
ROLES = {
    "독서": {"definition", "claim", "evidence_support", "cause_effect",
             "comparison_contrast", "condition_qualification", "exception_limit",
             "process_sequence"},
    "운문": {"speaker_attitude", "imagery_sensory", "figurative_symbol", "tone_diction",
             "structure_repetition", "situation_setting", "theme_statement",
             "external_criterion"},
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
    domain = meta.get("domain", "독서")
    contract = CONTRACT.get(difficulty, CONTRACT["중"])

    # index sources
    sources = {s["sourceId"]: s for s in exam.get("sources", [])}

    # ---- H7 (운문): a real literary work must carry an explicit copyright basis ----
    # 운문 quotes actual poems. Without a stated basis the skill cannot show the work is
    # safe to reproduce, so this is a hard gate rather than a note.
    for s in exam.get("sources", []):
        if s.get("kind") != "public_domain_work":
            continue
        cr = s.get("copyright") or {}
        if not cr.get("basis"):
            rep.err(s.get("sourceId", "?"), "H7-no-copyright-basis",
                    "public_domain_work 소스에 copyright.basis(저작권 만료 근거)가 없음. "
                    "예: '저자 1945년 사망 — 사후 70년 경과'.")

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

        # ---- H1-view (운문): the <보기> external criterion must itself be grounded ----
        view = q.get("view") or {}
        if view.get("sourceId"):
            vsrc = sources.get(view["sourceId"])
            if not vsrc:
                rep.err(qid, "H1-view-bad-sourceId",
                        f"view.sourceId '{view['sourceId']}' 가 sources에 없음.")
            elif view.get("sourceQuote") and not is_sub(view["sourceQuote"], vsrc.get("text", "")):
                rep.err(qid, "H1-view-quote-not-substring",
                        "view.sourceQuote가 원자료의 실제 부분문자열이 아님 → 외적 준거를 지어냄.")

        # evidence quotes resolve (H1 chain: evidence.quote ⊆ passage sentence, or ⊆ this
        # question's own <보기> box when passageRef is v0)
        for i, e in enumerate(ev):
            ref = e.get("passageRef")
            if ref == "v0":
                if not view.get("text"):
                    rep.err(qid, "evidence-ref-unresolved",
                            f"evidenceLocations[{i}]가 v0(<보기>)를 참조하지만 이 문항에 view가 없음.")
                elif not is_sub(e.get("passageQuote", ""), view["text"]):
                    rep.err(qid, "evidence-quote-not-substring",
                            f"evidenceLocations[{i}].passageQuote가 <보기> 본문의 부분문자열이 아님.")
            elif ref not in sent:
                rep.err(qid, "evidence-ref-unresolved",
                        f"evidenceLocations[{i}].passageRef '{ref}' 가 지문에 없음.")
            elif not is_sub(e.get("passageQuote", ""), sent[ref]):
                rep.err(qid, "evidence-quote-not-substring",
                        f"evidenceLocations[{i}].passageQuote가 {ref} 문장의 부분문자열이 아님.")

            # role must belong to this domain's vocabulary
            role = e.get("role")
            if role and role not in ROLES.get(domain, set()):
                other = [d for d, rs in ROLES.items() if role in rs]
                rep.err(qid, "role-domain-mismatch",
                        f"evidenceLocations[{i}].role '{role}' 은 domain '{domain}' 의 역할이 아님"
                        + (f" ({other[0]} 전용)." if other else "."))

            # ---- H6 (운문): a verbatim span alone cannot ground an inference in verse ----
            # In prose the quote IS the evidence; in verse the quote is only the anchor and
            # the reading must be stated so a teacher can check it.
            if domain == "운문" and q.get("demand") != "recall" and not (e.get("interpretation") or "").strip():
                rep.err(qid, "H6-missing-interpretation",
                        f"evidenceLocations[{i}]에 interpretation이 없음. 운문에서 demand가 recall이 "
                        "아니면 인용 스팬만으로 근거가 성립하지 않는다(인용=기계 검증, 해석=교사 검증).")

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
            haystack = view.get("text", "") if ref == "v0" else sent.get(ref, "")
            if (ref != "v0" and ref not in sent) or not is_sub(wq, haystack):
                weak.append(di)
                rep.err(qid, "H5-whyFalse-unresolved",
                        f"오답 {di}의 반증 인용(whyFalseQuote)이 {ref} 문장에서 확인되지 않음 → 약한 오답.")
        # a set repeating one recipe teaches one misreading only (03 §5)
        recipes = [d.get("recipe") for d in dists]
        if len(set(recipes)) == 1 and len(recipes) == 4:
            rep.warn(qid, "recipe-monotone",
                     f"오답 4개가 모두 '{recipes[0]}' — 서로 다른 오독을 겨냥하도록 분산 권장.")
        if len(weak) >= 2:
            rep.err(qid, "weak-distractors",
                    f"약한 오답 {len(weak)}개(≥2) — 문항 재생성 필요. indexes={weak}")

    # answer spread. A set whose answers all sit on one index is solvable without the
    # passage, so this is a hard gate; a merely lopsided spread is a warning.
    if answer_indexes and len(set(answer_indexes)) == 1 and len(answer_indexes) >= 3:
        rep.err("_set", "answer-monotone",
                f"모든 정답이 {answer_indexes[0]}번으로 동일 — 지문 없이 풀리는 세트. 정답 위치를 분산할 것.")
    elif answer_indexes:
        top = max(answer_indexes.count(a) for a in set(answer_indexes))
        if top > len(answer_indexes) / 2:
            rep.warn("_set", "answer-skew",
                     f"정답 {len(answer_indexes)}개 중 {top}개가 한 번호에 몰림 — 분산 권장.")

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
