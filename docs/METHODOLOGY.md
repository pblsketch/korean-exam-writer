# Methodology

## Goal

Let a Korean-language teacher author 독서/비문학 reading assessments — single or
composite passages, five-choice items with one correct answer, verbatim-grounded
evidence, distractor diagnostics — and export a printable 2-column A4 exam sheet
(HTML→PDF) and HWPX, with a fail-closed validator between authoring and rendering.

## Two design axes

1. **Orchestration** — the skill runs as an orchestrator directing role
   subagents (research · design · writing · fact-check · item-writing · review ·
   assembly), separating generators from verifiers (`references/12-orchestration.md`).
2. **Human-in-the-loop** — generation stops at teacher approval checkpoints
   (context → topic → source → outline → passage → items), never one-shot
   (`references/13-interactive-workflow.md`).

Both are the author's own original work.

## Independently designed generation methodology

The item taxonomy, cognitive-demand ladder, distractor error taxonomy,
evidence-role scheme, passage formulas, and the grade × difficulty model
(`references/01`–`07`) are designed from public educational-measurement and
text-linguistics principles (citations below).

Two commitments run through the model:

1. **Construct-relevant difficulty.** Difficulty comes from cognitive demand and
   evidence spread, not harder vocabulary or sheer length. Sentence-length bands
   are anchored to the grade band (`references/06-grade-difficulty-map.md`).
2. **Monotonic demand.** The demand ladder (`recall → inference → integration →
   critique`) is ordered; a higher target never yields an easier item profile
   (`references/02-cognitive-contract.md`).

## Empirical anchor (2017–2026), non-reconstructive

The demand model and passage formulas are anchored to a 10-year aggregate of the
main CSAT 독서/비문학 section (admission years 2017–2026). The aggregate is
**non-reconstructive**: no passage text, item numbers, answer keys, or n-grams —
only corpus-level statistics and metadata-only source provenance. See
[EMPIRICAL_ANALYSIS_2017_2026](EMPIRICAL_ANALYSIS_2017_2026.md) and
[PROVENANCE](PROVENANCE.md); data in `data/`.

## Validation-first rendering

Every factual claim carries a verbatim `sourceQuote` that `scripts/validate_exam.py`
checks as a literal substring of its source (H1/H5). Rendering is refused unless
validation exits 0 (`references/00-anti-hallucination.md`). Teacher-only content
(answers, diagnostics, verification report) renders in a separate teacher block,
never on the student sheet.

## Limitations

Synthetic fixtures and the model support authoring and pipeline testing; they are
**not** evidence of empirical student difficulty or fairness. Real psychometric
validation with consenting students is pending and not claimed
(see [NON_AFFILIATION](NON_AFFILIATION.md)).

## Public references (principles only)

1. Haladyna, Downing, & Rodriguez (2002). A review of multiple-choice
   item-writing guidelines. *Applied Measurement in Education, 15*(3).
2. AERA, APA, & NCME (2014). *Standards for Educational and Psychological Testing.*
3. Kane, M. T. (2013). Validating the interpretations and uses of test scores.
   *Journal of Educational Measurement, 50*(1).
4. Meyer, B. J. F. (1985). Prose analysis: Purposes, procedures, and problems.
5. Kintsch, W. (1998). *Comprehension: A Paradigm for Cognition.*
6. NIST (2024). *AI RMF: Generative AI Profile (NIST AI 600-1).*
7. UNESCO (2023). *Guidance for generative AI in education and research.*
8. W3C (2024). *WCAG 2.2.*
