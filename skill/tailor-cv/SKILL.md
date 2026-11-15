---
name: tailor-cv
description: Tailors a CV (and, when asked, a cover letter) to one job from the user's master profile, and records the application. Use when the user shares a job description, link or posting and asks for a CV, says "tailor my CV", "apply to this" or "CV for <company>", or asks for a cover letter for a role.
---

# Tailor a CV to one job

The builder is a command line tool: in the commands below, `cv` stands for `{{CV_BIN}}`. Its data (the master profile, selections and applications) is in `{{CV_HOME}}`. If `cv outline` says there is no master profile, run `cv init` and ask the user to replace the example's facts with their own before going on.

Everything on a CV comes from the master profile. You select and reorder; you never add a fact. The builder refuses skills, numbers and technologies the profile does not contain, so do not work around a refusal: it means the claim is not backed.

## 1. Start the application

1. Get the full job description. A link: fetch it. If only a title and company are given, ask for the description.
2. `cv new "<Company>" "<Role>" --job -` with the description on standard input. It prints the application folder, which holds `job.md` and a `selection.json` copied from the general CV.
3. `cv outline` lists every bullet with its id, tags and available wordings. Read the profile file itself only for the exact text of bullets you are considering.

## 2. Read the job like a screener

From the description, work out:

- the three or four things the role is really about (what the first reader looks for in ten seconds);
- the must-have technologies and the nice-to-haves;
- the seniority, and what it implies (ownership, team size, scale);
- terms the description uses that the built-in vocabulary may not know. Put those in the selection's `"keywords"` so the match report counts them.

## 3. Edit `selection.json`

The output is always one page, with a short summary, bullets that each prove something with a number, and nothing said twice.

- **One page, always.** There is no longer option. Five strong bullets beat seven mixed ones; drop what does not help this role.
- **Order by relevance.** The most relevant bullets go first inside each entry.
- **Summary**: two or three lines, 60 words at most, written for this role from facts in the profile (years, stacks, kinds of system). No adjectives the user did not earn. Figures in a custom summary must already appear in one of the profile's stored summaries; when a role needs another figure, add a summary variant to the profile first and select it by name.
- **Numbers**: prefer bullets that carry a figure (time to deliver, percentages, counts, team size). The profile already bolds the proof numbers; keep them when rewording.
- **Wording**: each bullet is an id (its `short` wording), `{"id": "...", "variant": "long"}` for the fuller wording, or `{"id": "...", "text": "..."}` to reword. Keep the shape `*Project name (context):* what was done, with the number`. Reword to lead with what this job cares about and to use the job's own term for the same thing. Keep every number exactly as the profile has it.
- **Bold**: `"bold": [...]` takes up to ten of the job's most important terms that the user really has (for example `"Spring Boot"`, `"Kafka"`). Each is bolded once, where it first appears in a bullet. Choose the terms a screener scans for; do not bold generic words.
- **No repeats**: a skill appears in one group only; a technology named in three bullets does not need to be in all three; the summary does not restate a bullet.
- **Skills**: put the groups and items the job asks for first, and list only what this reader cares about. Every item must exist in the profile. A group's optional `"also"` list is shown after a semicolon, for the secondary items.
- **Links**: the header's email and profile links are clickable. A project gets a link from a `url = "https://..."` entry in the profile, and text can carry `[label](https://...)`. Never invent a link.

Do not stuff keywords. A term belongs on the CV only where a bullet shows it being used, or in the skills line.

## 4. Build and check

1. `cv build <folder>`. It refuses (PROBLEM) a second page, a summary over 60 words, a skill or bullet listed twice, more than ten bold terms, and anything the profile does not back. Fix each one.
2. Read its notes and act on the ones that apply: bullets with no number (swap for one that has a figure, or accept if the bullet is needed for a keyword), several bullets opening with the same verb (vary them when rewording), a phrase said in two bullets.
3. Fit: "Tight" means cut a bullet; "room to spare" means add the next most relevant one. The builder picks the largest type size that fills the page.
4. Read the match report:
   - "true but not shown": add the ones that matter for this role.
   - "not in your profile": real gaps. Leave them out and carry them to the report.
5. Open the PDF once and look at it: the top third answers "why this person for this job", and the bold terms are the ones a screener would look for.

## 5. Recruiter review (one round, two at most)

A fresh reader judges the built CV. It gives no score: it returns findings, and the builder counts the evidence.

1. Run the `cv-recruiter` agent. Give it only two paths: the CV's `.txt` file in the application folder and `job.md`. Do not give it the master profile, the selection, or your reasoning; it must know only what a recruiter would.
2. Save its JSON answer as `review.json` in the folder, then `cv review <folder>`. It checks that every quote the reviewer gave as evidence is really in the CV, prints "Must-have requirements with quoted evidence: N of M", and sorts the findings.
3. Act on the result:
   - **MUST FIX** (and a skim that says it would not keep reading): fix by reordering, cutting or rewording in `selection.json`. Do not add anything the profile lacks. Rebuild with `cv build`.
   - **GAP**, and requirements with no evidence: wording cannot fix these. If the profile has evidence the CV left out, add that bullet or skill. Otherwise leave it and carry it to the report as a question for the user.
   - **optional**: apply only when it costs nothing else on the page.
4. If must-fix items were open, run the agent once more on the rebuilt CV, telling it which items to verify, save over `review.json`, and `cv review` again. The second round only confirms the fixes; do not start a new open-ended critique.
5. Stop when `cv review` says "Done" or "Stop". Two rounds is the limit, whatever is left. Never revise to chase a higher count: a requirement the user does not meet stays unmet.

## 6. Report back

Keep it short:

- the PDF path;
- what the CV now leads with, and what was dropped;
- the review result: "N of M must-have requirements have evidence", and what the skim took away;
- the reviewer's interview questions, since they are what the user should prepare for;
- the gaps, plainly. For each one, ask whether the user has experience the profile lacks ("Have you used Kafka anywhere? If so, tell me where and I will add it to the profile"). A yes goes into the profile first, then into this CV.

## Cover letter (only when asked)

Write `letter.md` in the application folder: three or four short paragraphs, plain text, under 300 words. Open with the role and the single strongest reason the user fits; give two concrete pieces of evidence from the profile, with their numbers; close with availability. No "I am writing to apply", no "passionate", no restating the CV. Address it as the posting does, or "Dear Hiring Team". Then `cv letter <folder>`.

## Tracking

- When the user says they applied: `cv status <folder> applied`. Later: `assessment`, `interview`, `offer`, `rejected`, `withdrawn`.
- "What have I applied to?": `cv log`.
