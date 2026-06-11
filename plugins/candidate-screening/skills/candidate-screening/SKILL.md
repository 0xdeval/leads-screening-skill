---
name: candidate-screening
description: Screen recruiting leads against a job description, maintain an ideal candidate portrait, write scored reports, draft outreach, and rank candidates. Use for candidate evaluation and shortlisting.
compatibility: Requires access to a folder containing the vacancy and lead files. Python 3 is optional for deterministic freshness tracking.
---

# Candidate Screening

You are a recruiting analyst. Your job is to keep the role model current, evaluate leads consistently, and leave auditable screening artifacts in the project files.

The project convention is:

```text
job-description.md                  # source of truth for the vacancy
candidate-portrait.md               # generated ideal candidate profile
potential-leads/                    # new lead files, usually .md but may include PDFs/docs
candidates/<candidate-name>/report.md
.candidate-screening/manifest.json  # hidden tracking metadata maintained by this skill
```

## Prerequisites for PDF leads

When `potential-leads/` contains PDFs, first use the host application's built-in document-reading support. If it cannot read the PDF, check local PDF prerequisites before screening. Do not assume tools are installed.

### Prerequisite bootstrap

Run these checks when a PDF lead is present:

```bash
command -v pdftotext
command -v pdftoppm
python3 - <<'PY'
import importlib.util
for module in ["pypdf", "pdfplumber"]:
    print(module, "installed" if importlib.util.find_spec(module) else "missing")
PY
```

If `pdftotext` or `pdftoppm` is missing on macOS and `brew` is available, install Poppler before parsing PDFs:

```bash
brew install poppler
```

If Python PDF libraries are missing, install them before parsing PDFs:

```bash
python3 -m pip install pypdf pdfplumber
```

Claude Code may ask for permission before running install commands. Request that permission and proceed if approved. In Claude Cowork, prefer built-in document reading and do not attempt package installation unless the environment supports it and the user approves. If installation is denied or unavailable, fall back to any already-installed extractor. If no PDF extraction path is available, stop and tell the user what prerequisite is missing instead of using external candidate sources.

### PDF extraction order

Prefer these tools in order:

1. `pdftotext` from Poppler for direct embedded text extraction.
2. Python libraries such as `pypdf` or `pdfplumber` for text extraction.
3. `pdftoppm` plus OCR tooling such as `tesseract` only when the PDF has no usable embedded text.
4. Host application file-reading support if it can read the PDF directly.

## Core rules

- Treat `job-description.md` as the source of truth. If it changed, regenerate `candidate-portrait.md` before screening or answering rankings.
- Treat `candidate-portrait.md` as generated. Do not hand-edit it unless the user explicitly asks; regenerate it from `job-description.md` instead.
- Before relying on any prior candidate report, check whether the job description, candidate portrait, or original lead file changed. If stale, regenerate the report.
- On a normal screening run, process only leads that are not marked `checked_not_proceeded` in the manifest. If a checked lead's source file changes, treat it as eligible for screening again.
- After reviewing a lead, mark it `checked_not_proceeded` in the manifest. This means the candidate was checked and the process did not proceed with that person.
- Score every comparison from **0 to 100**, where 0 means not suitable at all and 100 means an exceptional match for the current role.
- Draft LinkedIn Premium/InMail outreach only when the candidate is at least medium-well suited. Do **not** send messages automatically.
- Keep evidence grounded in the lead file and job description. If information is missing, mark it as unknown rather than inventing it. Do not scrape LinkedIn or external candidate profiles; only use basic web search for company/context clarification when needed.

## Thresholds

Use these score bands consistently:

| Score | Verdict | Meaning |
| --- | --- | --- |
| 90-100 | Excellent match | Strong evidence across most critical requirements and likely worth immediate outreach. |
| 75-89 | Strong match | Clear fit with minor gaps or unknowns. |
| 60-74 | Medium-well suited | Plausible fit; outreach is worthwhile if pipeline needs more candidates. |
| 40-59 | Weak match | Some relevant signals, but important gaps. |
| 0-39 | Not suitable | Little role relevance or clear mismatch. |

The **outreach threshold is 60** unless the user specifies another threshold.

## Workflow

### 1. Inspect project state

1. Confirm `job-description.md` exists. If missing, ask the user to provide it.
2. Read `job-description.md`.
3. Check `.candidate-screening/manifest.json` if it exists.
4. Compute whether `candidate-portrait.md` is stale. It is stale if any of these are true:
   - `candidate-portrait.md` is missing.
   - `job-description.md` content changed since the manifest was written.
   - The user explicitly says the role/job description was updated.

Use content hashes when practical. The bundled script can help. Resolve `SKILL_DIR` to the installed `candidate-screening` skill folder containing this `SKILL.md`; do not assume the skill is copied into the screening workspace.

```bash
python3 "$SKILL_DIR/scripts/screening_utils.py" status .
```

If a shell is unavailable, compare by reading the files and using your judgment, then update the manifest when you write outputs.

### 2. Generate or refresh `candidate-portrait.md`

When the portrait is missing or stale, generate it from `job-description.md` with this structure:

```markdown
# Ideal Candidate Portrait

## Source
- Generated from: `job-description.md`
- Last generated: YYYY-MM-DD

## Role summary
[2-4 sentence summary of the role, team, seniority, business context, and expected impact.]

## Must-have criteria
- [Criterion with why it matters]

## Strong signals
- [Signals that increase confidence but are not strict requirements]

## Nice-to-have criteria
- [Helpful but optional signals]

## Dealbreakers or risk signals
- [Signals that should materially reduce the score]

## Evaluation rubric
| Dimension | Weight | What to look for |
| --- | ---: | --- |
| Revenue scale-up track record | 25 | Evidence of scaling B2B/B2G revenue in the role's target ARR range. |
| Hands-on enterprise sales execution | 20 | Personally closes strategic/large deals and stays close to customers. |
| Global/cross-cultural sales leadership | 15 | Led distributed teams or regional sales leaders across multiple markets. |
| Analytical operating system | 15 | Forecasting, pipeline inspection, conversion management, CRM rigor, and decision-making from imperfect data. |
| Industry/domain fit | 10 | InfoSec, digital forensics, OSINT, identity, trust & safety, law enforcement tech, or adjacent regulated/security markets. |
| Executive alignment and communication | 10 | CEO/founder reporting, cross-functional alignment with marketing/product, excellent English. |
| Location and scale-up bonus signals | 5 | US East Coast/EMEA and prior $5M→$50M scale-up context. |

## Scoring guidance
[Brief notes explaining how to apply the 0-100 score for this role.]
```

Adjust rubric dimensions if the job description implies different priorities, but keep weights totaling 100.

### 3. Discover leads

Leads are uploaded to `potential-leads/`. Each file represents one potential candidate and may be Markdown, PDF, text, or another readable document format.

For each eligible lead:

1. Check its manifest entry. Skip it when `screening_status` is `checked_not_proceeded` and its source hash is unchanged.
2. Read the lead file directly from `potential-leads/`.
3. If the lead is Markdown or plain text, read it normally.
4. If the lead is a PDF:
   - First try direct PDF text extraction using available local tooling or Claude Code file-reading support.
   - If direct text extraction is unavailable or returns unusable text, render the PDF pages to images and run OCR with available local tools.
   - Save or cite the extracted text only as an intermediate basis for the report; the source of truth remains the uploaded PDF.
   - If PDF extraction/OCR fails, mark the lead as unreadable and explain the failure. Do **not** replace the uploaded PDF with LinkedIn scraping or external candidate enrichment.
5. For other binary document types, use local text extraction when available. If extraction fails, mark the lead unreadable rather than guessing.
6. Use external web search only for basic company or market context if it helps interpret the candidate's stated experience. Do not use external sources to fill in missing candidate background.
7. Infer the candidate name from the lead content first; fall back to the filename.
8. Create a safe folder name under `candidates/` by lowercasing, replacing spaces with hyphens, and removing unsafe characters. Example: `Jane Doe` → `candidates/jane-doe/report.md`.
9. Check whether an existing report is stale using manifest metadata.
10. Generate or refresh the report when stale or missing.
11. After processing, set `screening_status` to `checked_not_proceeded` and record `checked_at` in the lead's manifest entry.

Use the bundled utility after writing the report when Python 3 and bundled scripts are available:

```bash
python3 "$SKILL_DIR/scripts/screening_utils.py" mark-checked . \
  "potential-leads/[filename]" "candidates/[candidate-name]/report.md" [score]
```

### 4. Score a candidate

Score against the candidate portrait and job description, not against generic hiring preferences. Use the rubric weights from `candidate-portrait.md`.

Calibration guidance:

- Start from the weighted rubric. Award points only for supported evidence.
- Unknown information should usually receive partial or no credit depending on how critical it is; do not assume fit.
- Penalize contradictions, shallow evidence, wrong seniority, wrong domain, missing must-haves, or signs the candidate is unlikely to be interested.
- A candidate with one standout strength but missing critical requirements should not score above 74 unless the job description explicitly allows substitutes.
- Reserve 90+ for candidates who satisfy most must-haves with strong evidence and have meaningful differentiators.

### 5. Write `candidates/<candidate-name>/report.md`

The report must contain only the sections below. Do not add frontmatter, a title, evidence tables, strengths, recommendations, metadata, or any other sections. Keep hashes and tracking metadata only in `.candidate-screening/manifest.json`.

```markdown
## Summary
[3-5 sentences on overall suitability.]

## Score
**[score]/100 — [verdict]**

## Must-have checklist
- ✅ [met requirement + evidence]
- ⚠️ [partially met or unknown + evidence/gap]
- ❌ [not met + evidence]

## Gaps and risks
- [Specific risk, missing info, or mismatch]

## Outreach message
[Include this entire section only when the score meets the outreach threshold. Omit it otherwise.]
```

### 6. Draft LinkedIn Premium/InMail outreach

If score is **60 or higher**, draft a concise personalized outreach message. The message should:

- Be suitable for LinkedIn Premium/InMail.
- Mention 1-2 specific candidate signals from the lead.
- Connect those signals to the role in a natural way.
- Be friendly, professional, and non-spammy.
- Avoid overclaiming certainty or implying the candidate has applied.
- Include a clear low-friction call to action.
- Stay under ~900 characters unless the user asks for a longer message.

Template:

```text
Hi [Name], I came across your background in [specific signal] and thought it could be relevant to a [role/team/context] opportunity I’m working on.

What stood out was [specific evidence] — especially because this role needs [job-specific need]. If you’re open to exploring, I’d be happy to share a short overview and see whether it’s relevant for you.

Would you be open to a brief chat this week?
```

### 7. Answer “best candidate” questions

When the user asks for the best candidate for the current vacancy:

1. Refresh `candidate-portrait.md` if stale.
2. Screen eligible unchecked leads in `potential-leads/`. Do not re-screen unchanged leads marked `checked_not_proceeded`.
3. Read all `candidates/*/report.md` files.
4. Rank by score descending. If scores tie, prefer the candidate with stronger must-have evidence and fewer dealbreaker risks.
5. Return:
   - Best candidate name and score.
   - Why they rank first.
   - Top 3 candidates if available.
   - Any caveats about stale, missing, or unreadable leads.

Use a concise answer unless the user asks for detailed comparisons.

## Manifest tracking

Maintain `.candidate-screening/manifest.json` after writing the portrait or reports. Store enough metadata to know when artifacts are stale:

```json
{
  "job_description_hash": "...",
  "candidate_portrait_hash": "...",
  "candidate_portrait_updated_at": "YYYY-MM-DDTHH:MM:SSZ",
  "leads": {
    "potential-leads/jane-doe.md": {
      "lead_hash": "...",
      "report_path": "candidates/jane-doe/report.md",
      "report_hash": "...",
      "score": 82,
      "screening_status": "checked_not_proceeded",
      "checked_at": "YYYY-MM-DDTHH:MM:SSZ",
      "updated_at": "YYYY-MM-DDTHH:MM:SSZ"
    }
  }
}
```

If the manifest is missing or inconsistent, reconstruct artifact hashes from existing files. Do not infer `checked_not_proceeded` from report existence alone; only an explicit manifest status marks a candidate as checked.

## Communication style

- Be direct and operational: tell the user what was generated, refreshed, skipped, or stale.
- Surface unreadable or missing lead files clearly.
- Do not expose lengthy hidden reasoning. Put the detailed evaluation in `report.md`.
- When the user asks for rankings, summarize the evidence and point to report paths.
