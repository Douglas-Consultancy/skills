| name | description |
| --- | --- |
| litigation | Use when the task involves legal research, drafting litigation documents, analyzing case law, preparing motions or pleadings, reviewing contracts, or performing citation verification; enforces Bluebook citation format, hallucination prevention, and court-ready document standards. |

# Litigation Skill

## When to use

- Draft or review litigation documents: complaints, answers, motions, briefs, discovery requests, subpoenas.
- Perform legal research and case law analysis.
- Analyze contracts, settlement agreements, or regulatory filings.
- Prepare demand letters or cease-and-desist notices.
- Verify legal citations for accuracy and existence.
- Format documents to comply with federal or state court local rules.
- Summarize depositions, hearing transcripts, or judicial opinions.

## When NOT to use

- This skill does NOT provide licensed legal advice. Always disclaim AI-generated status.
- Do not use for tax preparation, immigration petitions, or patent prosecution (specialized domains).
- Do not use to generate fabricated or unverified case citations under any circumstances.

## Workflow

1. **Identify jurisdiction and court.**
   - Confirm federal vs. state, district, and division.
   - Load applicable local rules (page limits, font, margins, filing requirements).
   - Identify governing substantive law (state law in diversity, federal question, etc.).

2. **Research and cite only verifiable authorities.**
   - NEVER fabricate a case citation. If you cannot confirm a case exists, say so explicitly.
   - Use `scripts/verify_citations.py` to cross-reference citations against CourtListener or Caselaw Access Project APIs.
   - Prefer well-known, frequently cited authorities. Provide full Bluebook citations.
   - For statutes, cite the current codified version with year.

3. **Draft using proper legal formatting.**
   - Caption block: court name, case number, party names, document title.
   - Numbered paragraphs for complaints and answers.
   - Point headings for briefs and motions.
   - Signature block with attorney/party information.
   - Certificate of service where required.
   - Use `scripts/generate_pleading.py` to produce formatted `.docx` output.

4. **Review and verify.**
   - Re-read every citation. Confirm case name, volume, reporter, page, year.
   - Check procedural posture matches your argument.
   - Verify statutes of limitation, filing deadlines, and procedural prerequisites.
   - Flag any citation that could not be independently verified.

5. **Deliver with disclaimers.**
   - State clearly: "This document was generated with AI assistance and has not been reviewed by a licensed attorney."
   - Recommend human legal review before filing.

## Citation format (Bluebook)

- Cases: *Party v. Party*, Vol. Reporter Page (Court Year).
  - Example: *Ashcroft v. Iqbal*, 556 U.S. 662 (2009).
- Statutes: Title U.S.C. section (Year).
  - Example: 42 U.S.C. section 1983 (2018).
- Regulations: Title C.F.R. section (Year).
- California state cases: *Party v. Party* (Year) Vol. Cal.App.5th Page.

## Hallucination prevention

- Before including ANY case citation, attempt verification.
- If `scripts/verify_citations.py` returns no match, do NOT include the citation.
- Instead, note: "[Citation needed - unable to verify. Manual research recommended.]"
- Never invent case names, docket numbers, or holdings.
- If the user insists on an unverifiable citation, refuse and explain the risk.

## Document types supported

| Type | Key elements |
| --- | --- |
| Complaint | Caption, jurisdiction, parties, numbered allegations, causes of action, prayer for relief |
| Answer | Caption, numbered responses (admit/deny), affirmative defenses |
| Motion | Caption, notice of motion, memorandum of points and authorities, declaration(s) |
| Brief | Caption, table of contents, table of authorities, argument with point headings |
| Discovery | Interrogatories, requests for production, requests for admission |
| Demand letter | Header, factual background, legal basis, demand, deadline |
| Contract analysis | Clause-by-clause review, risk flags, plain-language summary |
| Case summary | Procedural history, holdings, key reasoning, practical implications |

## Jurisdiction-specific templates

- **Federal (N.D. Cal.)**: 25-page brief limit, 14pt Times New Roman, CM/ECF filing.
- **California Superior Court (Contra Costa County)**: CRC formatting, mandatory meet-and-confer declarations.
- **General federal**: FRCP compliance, local rule checks.
- Templates are extensible. Add new jurisdictions by creating a YAML config in `scripts/jurisdictions/`.

## Dependencies (install if missing)

Prefer `uv` for dependency management.

Python packages:

```
uv pip install python-docx requests beautifulsoup4
```

If `uv` is unavailable:

```
python3 -m pip install python-docx requests beautifulsoup4
```

## Temp and output conventions

- Use `tmp/litigation/` for intermediate files; delete when done.
- Write final artifacts under `output/litigation/`.
- Name files descriptively: `motion_to_dismiss_2026-03-18.docx`, `demand_letter_draft.docx`.

## Environment

- `COURTLISTENER_API_KEY` (optional): API key for CourtListener citation verification.
- `CAP_API_KEY` (optional): API key for Caselaw Access Project.
- If no API keys are set, `verify_citations.py` will attempt public endpoints with rate limiting.

## Quality expectations

- Every document must be court-ready: proper formatting, consistent typography, correct margins.
- Every citation must be verified or explicitly flagged as unverified.
- Legal reasoning must be logically structured with proper IRAC (Issue, Rule, Application, Conclusion) format.
- No hallucinated authorities, holdings, or procedural rules.
- Plain language summaries should accompany complex legal analysis when requested.

## Final checks

- Verify all citations one final time before delivery.
- Confirm document complies with applicable page/word limits.
- Ensure all required components are present (caption, signature block, certificate of service).
- Remove any placeholder text, TODO markers, or internal notes.
- Add AI-generated disclaimer.
