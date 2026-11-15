"""cv: build tailored one-page CVs from one master profile.

cv init                            create a private master profile and base selection from the example
cv outline                         what is in the master profile (ids, tags, wordings)
cv new <company> <role> [--job F]  start an application folder with a selection to edit
cv build <folder or selection>     check the selection, then write the PDF
cv check <folder or selection>     compare the CV with the job description
cv review <folder>                 check the recruiter review (review.json) against the CV
cv letter <folder>                 turn letter.md into a PDF with the same header
cv status <folder> <status>        record where an application stands
cv log                             every application and its status
cv install [--target DIR]          install the tailor-cv skill and recruiter agent for Claude Code
"""

from __future__ import annotations

import argparse
import csv
import datetime
import html
import json
import re
import shutil
import sys
from pathlib import Path

from . import __version__, paths, render
from .errors import CvError
from .install import install
from .master import Master
from .match import keyword_report
from .review import MAX_REVIEW_ROUNDS, review_summary
from .selection import blocking, resolve

LOG_FIELDS = ["date", "company", "role", "status", "folder", "cv", "pages", "evidence", "review_rounds", "updated"]


def slug(text: str, sep: str = "-") -> str:
    return re.sub(r"[^A-Za-z0-9]+", sep, text).strip(sep)


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise CvError(f"{path} is not valid JSON: {error}") from None


def locate(target: str) -> tuple[Path, Path]:
    """(folder, selection file) for a folder, a selection file, or the name of an application."""
    path = Path(target)
    if not path.exists() and (paths.applications_dir() / target).exists():
        path = paths.applications_dir() / target
    if path.is_dir():
        return path, path / "selection.json"
    if path.is_file():
        return path.parent, path
    raise CvError(f"Not found: {target}")


def load(target: str) -> tuple[Path, dict, Master]:
    folder, selection_path = locate(target)
    if not selection_path.exists():
        raise CvError(f"No selection.json in {folder}")
    return folder, _read_json(selection_path), Master(paths.profile_path())


# ---------------------------------------------------------------- the application log


def _log_path() -> Path:
    return paths.applications_dir() / "applications.csv"


def read_log() -> list[dict]:
    if not _log_path().exists():
        return []
    with _log_path().open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def upsert_log(folder: Path, **fields: object) -> None:
    rows = read_log()
    today = datetime.date.today().isoformat()
    row = next((r for r in rows if r["folder"] == folder.name), None)
    if row is None:
        row = dict.fromkeys(LOG_FIELDS, "") | {"date": today, "folder": folder.name, "status": "drafted"}
        rows.append(row)
    row.update({key: str(value) for key, value in fields.items() if value is not None})
    row["updated"] = today
    paths.applications_dir().mkdir(parents=True, exist_ok=True)
    with _log_path().open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=LOG_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------- output helpers


def print_report(report: dict[str, list[str]]) -> None:
    total = sum(len(v) for v in report.values())
    if total == 0:
        print("Job match: no known technology terms found in the job description.")
        return
    print(f"Job match: {len(report['covered'])} of {total} terms from the job description are in the CV.")
    if report["covered"]:
        print(f"  in the CV:            {', '.join(report['covered'])}")
    if report["addable"]:
        print(f"  true but not shown:   {', '.join(report['addable'])}   <- consider adding")
    if report["gaps"]:
        print(f"  not in your profile:  {', '.join(report['gaps'])}   <- real gaps; do not add")


def job_text(folder: Path) -> str:
    path = folder / "job.md"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    return "" if "Paste the job description" in text else text


def _long_date(day: datetime.date) -> str:
    return f"{day.day} {day:%B %Y}"


# ---------------------------------------------------------------- commands


def cmd_init(_args: argparse.Namespace) -> int:
    pairs = [
        (paths.examples_dir() / "master.toml", paths.profile_path()),
        (paths.examples_dir() / "general.json", paths.selections_dir() / "general.json"),
    ]
    for source, destination in pairs:
        if destination.exists():
            print(f"Kept your existing {destination}")
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        print(f"Created {destination}")
    print("\nThe example is a fictional person. Replace its facts with your own in the profile, then run `cv outline`.")
    print("Both files stay on your machine: the repository's .gitignore excludes them.")
    return 0


def cmd_outline(_args: argparse.Namespace) -> int:
    master = Master(paths.profile_path())
    print(master.outline())
    for problem in master.problems:
        print(f"! {problem}")
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    base = paths.selections_dir() / "general.json"
    if not base.exists():
        raise CvError(f"No base selection at {base}. Run `cv init` first.")
    folder = paths.applications_dir() / f"{datetime.date.today().isoformat()}-{slug(args.company).lower()}-{slug(args.role).lower()}"
    if folder.exists():
        raise CvError(f"Already exists: {folder}")
    selection = _read_json(base)
    selection = {"company": args.company, "role": args.role, "keywords": [], **{k: v for k, v in selection.items() if k not in ("company", "role", "keywords")}}
    folder.mkdir(parents=True)
    (folder / "selection.json").write_text(json.dumps(selection, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    description = sys.stdin.read() if args.job == "-" else Path(args.job).read_text(encoding="utf-8") if args.job else ""
    (folder / "job.md").write_text(description or "Paste the job description here.\n", encoding="utf-8")
    upsert_log(folder, company=args.company, role=args.role)
    print(folder)
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    folder, selection, master = load(args.target)
    doc, problems = resolve(master, selection)
    for problem in problems:
        print(f"{'  note' if problem.startswith('note:') else '! PROBLEM'}: {problem.removeprefix('note: ')}")
    if blocking(problems) and not args.force:
        raise CvError("\nNot built. Fix the problems above (a true fact goes into the master profile first), or pass --force to build anyway.")

    company, role = selection.get("company", ""), selection.get("role", "")
    suffix = "_".join(part for part in (slug(company, "_"), slug(role, "_")) if part)
    stem = selection.get("file") or f"{slug(doc['basics']['name'], '_')}_CV{'_' + suffix if suffix else ''}"
    pdf_path = folder / f"{stem}.pdf"
    used, size = render.build_pdf(render.body_html(doc), f"{doc['basics']['name']} - CV", pdf_path)
    text = render.to_text(doc)
    (folder / f"{stem}.txt").write_text(text, encoding="utf-8")
    if not args.keep_html:
        pdf_path.with_suffix(".html").unlink(missing_ok=True)

    print(pdf_path)
    print(f"{used} {'page' if used == 1 else 'pages'} at {size}pt, {len(text.split())} words.")
    if used > 1:
        print("! Does not fit one page even at the smallest type size. Remove a bullet or shorten one.")
    elif size == render.SIZES[-1]:
        print("  There is room to spare at the largest type size: add the next most relevant bullet.")
    elif size < 8.8:
        print("  Tight: the type is small. Cutting one bullet would make it easier to read.")
    wanted = {f"mailto:{doc['basics']['email']}", *[f"https://{link}" for link in doc["basics"].get("links", [])]}
    missing = sorted(wanted - render.links_in(pdf_path))
    print(f"  Links that open when clicked: {len(wanted) - len(missing)} of {len(wanted)}." + (f" ! Not clickable: {', '.join(missing)}" if missing else ""))
    if description := job_text(folder):
        print_report(keyword_report(description, text, master, selection.get("keywords")))
    if folder.parent == paths.applications_dir():
        upsert_log(folder, company=company, role=role, cv=pdf_path.name, pages=used)
    return 1 if used > 1 else 0


def cmd_check(args: argparse.Namespace) -> int:
    folder, selection, master = load(args.target)
    doc, problems = resolve(master, selection)
    for problem in blocking(problems):
        print(f"! PROBLEM: {problem}")
    description = job_text(folder)
    if not description.strip():
        raise CvError(f"No job description in {folder / 'job.md'}")
    print_report(keyword_report(description, render.to_text(doc), master, selection.get("keywords")))
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    folder, selection, master = load(args.target)
    source = folder / "review.json"
    if not source.exists():
        raise CvError(f"No review yet. Save the recruiter agent's JSON as {source}")
    review = _read_json(source)
    doc, _problems = resolve(master, selection)
    result = review_summary(review, render.to_text(doc))

    history_path = folder / "review-history.json"
    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else []
    stamp = json.dumps(review, sort_keys=True)
    if not history or history[-1]["review"] != stamp:
        history.append({"review": stamp, "evidence": f"{result['musts_proved']}/{result['musts']}", "must_fix": len(result["fixable"])})
        history_path.write_text(json.dumps(history, indent=1), encoding="utf-8")
    rounds = len(history)

    skim = review.get("skim", {})
    print(f"Review round {rounds} of {MAX_REVIEW_ROUNDS}.")
    verdict = "would keep reading." if result["keep_reading"] else f"WOULD NOT keep reading: {skim.get('why_not')}"
    print(f'Skim: reads as "{skim.get("reads_as", "?")}"; {verdict}')
    print(f"Must-have requirements with quoted evidence: {result['musts_proved']} of {result['musts']}.")
    for name in result["unproved"]:
        print(f"  no evidence: {name}")
    for name in result["weak"]:
        print(f"  skills list only: {name}")
    for name in result["misquoted"]:
        print(f'  ! the reviewer\'s quote for "{name}" is not in the CV, so it was not counted')
    groups = (
        ("MUST FIX (reorder, cut or reword)", result["fixable"]),
        ("GAP (not fixable by wording; ask the user)", result["gaps"]),
        ("optional", result["optional"]),
    )
    for label, items in groups:
        for finding in items:
            print(f"- {label}: {finding.get('problem')} [{finding.get('where')}] -> {finding.get('fix')}")
    for question in result["questions"]:
        print(f"? {question}")

    if folder.parent == paths.applications_dir():
        upsert_log(folder, evidence=f"{result['musts_proved']}/{result['musts']}", review_rounds=rounds)
    open_items = len(result["fixable"]) + (0 if result["keep_reading"] else 1)
    if open_items == 0:
        print("\nDone: nothing left that rewording can fix. Stop revising.")
    elif rounds >= MAX_REVIEW_ROUNDS:
        print(f"\nStop: {MAX_REVIEW_ROUNDS} rounds is the limit. Report what is still open instead of revising again.")
    else:
        print(f"\nNext: fix the {open_items} must-fix item(s), rebuild, and run one more review that only checks those items.")
    return 0


def cmd_letter(args: argparse.Namespace) -> int:
    folder, selection, master = load(args.target)
    source = folder / "letter.md"
    if not source.exists():
        raise CvError(f"Write the letter in {source} first (plain paragraphs separated by blank lines).")
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", source.read_text(encoding="utf-8")) if p.strip()]
    basics = master.data["basics"]
    body = render.header(basics) + f'\n<div class="letter"><p class="date">{_long_date(datetime.date.today())}</p>\n'
    body += "\n".join(f"<p>{render.inline(p).replace(chr(10), '<br>')}</p>" for p in paragraphs) + "</div>"
    suffix = "_".join(part for part in (slug(selection.get("company", ""), "_"), slug(selection.get("role", ""), "_")) if part)
    pdf_path = folder / f"{slug(basics['name'], '_')}_Cover_Letter{'_' + suffix if suffix else ''}.pdf"
    html_path = pdf_path.with_suffix(".html")
    html_path.write_text(render.page_html(body, f"{html.escape(basics['name'])} - Cover letter", 10.5, 1.4), encoding="utf-8")
    render.print_pdf(html_path, pdf_path)
    html_path.unlink(missing_ok=True)
    pages = render.page_count(pdf_path)
    print(pdf_path)
    print(f"{pages} page(s), {sum(len(p.split()) for p in paragraphs)} words.")
    if pages > 1:
        print("! A cover letter should fit one page. Shorten it.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    folder, _selection = locate(args.target)
    upsert_log(folder, status=args.status)
    print(f"{folder.name}: {args.status}")
    return 0


def cmd_log(_args: argparse.Namespace) -> int:
    rows = read_log()
    if not rows:
        print("No applications yet.")
    for row in sorted(rows, key=lambda r: r["date"], reverse=True):
        print(f"{row['date']}  {row['status']:<12} {row['company']} - {row['role']}  ({row['folder']})")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    for path in install(Path(args.target).expanduser()):
        print(f"Installed {path}")
    print("Restart Claude Code (or start a new session) to pick them up.")
    return 0


# ---------------------------------------------------------------- entry point


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cv", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"cv {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init").set_defaults(run=cmd_init)
    sub.add_parser("outline").set_defaults(run=cmd_outline)
    new = sub.add_parser("new")
    new.add_argument("company")
    new.add_argument("role")
    new.add_argument("--job", help="file holding the job description, or - to read it from standard input")
    new.set_defaults(run=cmd_new)
    build = sub.add_parser("build")
    build.add_argument("target")
    build.add_argument("--force", action="store_true", help="build even when a check fails")
    build.add_argument("--keep-html", action="store_true")
    build.set_defaults(run=cmd_build)
    for name, run in (("check", cmd_check), ("review", cmd_review), ("letter", cmd_letter)):
        command = sub.add_parser(name)
        command.add_argument("target")
        command.set_defaults(run=run)
    status = sub.add_parser("status")
    status.add_argument("target")
    status.add_argument("status", help="for example: applied, assessment, interview, offer, rejected, withdrawn")
    status.set_defaults(run=cmd_status)
    sub.add_parser("log").set_defaults(run=cmd_log)
    installer = sub.add_parser("install")
    installer.add_argument("--target", default="~/.claude", help="Claude Code's config folder (default: ~/.claude)")
    installer.set_defaults(run=cmd_install)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.run(args)
    except CvError as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
