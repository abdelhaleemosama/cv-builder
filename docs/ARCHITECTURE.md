# Architecture

## The idea

A CV is a *view* of a person's facts, not a document to edit. So the facts are stored once (the master profile), a view is described by a small *selection*, and the builder turns a selection into a document only if the selection claims nothing the profile does not.

```
profile/master.toml  ──┐
                       ├─►  selection.resolve()  ──►  document  ──►  render  ──►  PDF + text
selection.json  ───────┘         │
                                 └─►  problems (blocking, or notes)
```

## Modules

| Module | Responsibility |
| --- | --- |
| `master.py` | Loads the profile, indexes entries by id, builds the corpus of everything the profile says |
| `selection.py` | Resolves a selection against the profile and returns the document plus every problem found |
| `rules.py` | House rules: summary length, duplicates, keyword limit, and the advisory notes |
| `vocabulary.py`, `text.py` | Whole-term matching over a technology vocabulary; markup and number helpers |
| `match.py` | Job description against a CV: covered, addable, real gaps |
| `review.py` | Verifies a recruiter review's quotes against the CV and counts the evidence |
| `render.py` | HTML, plain text and PDF (headless Chromium), type size fitting, link verification |
| `install.py` | Installs the Claude Code skill and agent with real paths filled in |
| `cli.py`, `paths.py`, `errors.py` | Commands, where personal data lives, and the expected-failure type |

The dependency direction is one way: `cli` uses everything; `selection` uses `master`, `rules`, `text` and `vocabulary`; nothing below imports `cli`. There are no third-party dependencies.

## Design decisions

**Checks live in code, not in a prompt.** The `tailor-cv` skill tells an assistant not to invent facts, but an instruction can be skipped. The builder is the authority: a bullet id, a skill, a number or a technology that the profile does not back is a refusal, with the reason, whoever wrote the selection.

**A number is only backed by its own source.** A reworded bullet's numbers must appear in the bullet it rewords. Matching against the whole profile would let "9 years" through because "9 partners" is written elsewhere, so a custom summary is held to the figures the stored summaries state. This was found by a test, not by thought.

**Counted evidence instead of a score.** The recruiter review must quote the CV for each requirement, and the quote is verified by string comparison. The headline number is "must-haves with evidence: N of M". A model's own percentage is not repeatable; a verified quote is. The loop stops on a rule (one round, a second only to confirm fixes), not on a threshold, because a threshold invites chasing the metric.

**Real gaps are never fixed by wording.** The job match separates "true but not shown" (add it) from "not in your profile" (do not add it). The second list is information for the person, not a to-do list for the tool.

**One page, filled.** The page budget is a hard rule. The builder binary-searches type size (8.2 pt to 10.5 pt) for the largest that still fits, so the page is full rather than left with a gap, and it reports when there is room for another bullet or when the type is getting small.

**Plain text, one column.** What applicant tracking systems parse reliably. The text copy written beside the PDF is what the keyword check and the reviewer read, so they see what a parser sees.

**Chromium for printing.** Headless Chrome, Chromium, Edge or Brave already on the machine prints the PDF, which keeps the project dependency-free and gives real fonts and working link annotations. The cost is that a browser must exist; the error says how to point at one (`CV_BROWSER`).

**Personal data is separated by construction.** Code never hardcodes a profile path. `paths.py` resolves the data folder (`CV_HOME`), and the repository's `.gitignore` excludes it. Tests build their own temporary home from the fictional example, and a hygiene test fails if a tracked file holds a real email address or a personal path.

## Extending it

- **A section or field**: add it to `master.py` indexing, resolve it in `selection.py`, render it in `render.py` (HTML and text), and add a test against the example profile.
- **A house rule**: add it to `rules.py`. Return a plain message for a blocking rule, or one starting with `note:` for advice.
- **More technologies**: extend `vocabulary.py`; the job match and the "no new technology" check use it.
