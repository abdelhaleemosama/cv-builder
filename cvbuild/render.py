"""Turns a resolved document into HTML, plain text and a PDF.

The PDF is printed by a Chromium-based browser already on the machine (Chrome, Chromium, Edge or
Brave) in headless mode, so there is nothing to install. The layout is one column of real text,
which is what applicant tracking systems read reliably.
"""

from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .errors import RenderError
from .selection import HEADINGS
from .text import plain

# Type sizes in points, smallest to largest. The builder uses the largest one that fits a single
# page, so the page is filled rather than left with a gap at the bottom.
SIZES = [round(8.2 + 0.1 * step, 1) for step in range(24)]  # 8.2pt ... 10.5pt
LEADING = 1.24

CSS = (Path(__file__).parent / "style.css").read_text(encoding="utf-8")


def _browser_candidates() -> list[str]:
    program_files = [os.environ.get(name, "") for name in ("ProgramFiles", "ProgramFiles(x86)", "LocalAppData")]
    windows = [
        str(Path(base) / suffix)
        for base in filter(None, program_files)
        for suffix in ("Google/Chrome/Application/chrome.exe", "Microsoft/Edge/Application/msedge.exe", "BraveSoftware/Brave-Browser/Application/brave.exe")
    ]
    return [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        *windows,
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "microsoft-edge",
    ]


def find_browser() -> str | None:
    """The browser used for printing: $CV_BROWSER, else the first Chromium-based one found."""
    override = os.environ.get("CV_BROWSER")
    for candidate in ([override] if override else []) + _browser_candidates():
        if candidate and Path(candidate).is_file():
            return candidate
        if candidate and (found := shutil.which(candidate)):
            return found
    return None


# ---------------------------------------------------------------- HTML

_LINK = re.compile(r"\[([^\]]+)\]\(((?:https?://|mailto:)[^)\s\"'<>]+)\)")


def inline(text: str) -> str:
    """Escapes text and applies **bold**, *italic* and [label](link). A link target cannot carry a quote."""
    out = html.escape(text.strip(), quote=False)
    out = _LINK.sub(r'<a href="\2">\1</a>', out)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", out)


def _titled(name: str, url: str | None = None) -> str:
    """ "Project - what it is" with only the short name in bold, linked when a url is given."""
    short, sep, rest = name.partition(" - ")
    head = f"<strong>{inline(short)}</strong>"
    if url:
        head = f'<a href="{html.escape(url)}">{head}</a>'
    return head + (f" - {inline(rest)}" if sep else "")


def _link(value: str) -> str:
    href = f"mailto:{value}" if "@" in value else f"https://{value}"
    return f'<a href="{html.escape(href)}">{html.escape(value)}</a>'


def header(basics: dict) -> str:
    first = " | ".join([html.escape(basics["location"]), html.escape(basics["phone"]), _link(basics["email"])])
    second = " | ".join(_link(link) for link in basics.get("links", []))
    return f'<h1>{html.escape(basics["name"]).upper()}</h1>\n<p class="contact">{first}{"<br>" + second if second else ""}</p>'


def _list(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{inline(item)}</li>" for item in items) + "</ul>" if items else ""


def _row(left: str, right: str) -> str:
    return f'<div class="row"><span>{left}</span><span class="when">{html.escape(right)}</span></div>'


def _skill_line(group: str, items: list[str], also: list[str]) -> str:
    shown = ", ".join(items) + (f"; {', '.join(also)}" if also else "")
    return f'<p class="skill"><strong>{html.escape(group)}:</strong> {html.escape(shown)}</p>'


def body_html(doc: dict) -> str:
    out = [header(doc["basics"])]
    for name, content in doc["sections"]:
        out.append(f"<h2>{HEADINGS[name]}</h2>")
        if name == "summary":
            out.append(f'<p class="summary">{inline(content)}</p>')
        elif name == "education":
            for edu in content:
                out.append(_row(f"<strong>{inline(edu['degree'])}</strong> - {inline(edu['school_shown'])}", f"{edu['dates']} | {edu['location']}"))
                line = f"GPA {edu['gpa']}" + (f", {edu['rank']}" if edu.get("rank") else "") + "."
                if edu["coursework_shown"]:
                    line += " Coursework (Distinction): " + ", ".join(edu["coursework_shown"]) + "."
                out.append(_list([line]))
        elif name == "experience":
            for job in content:
                out.append(_row(f"<strong>{inline(job['title'])}</strong> - {inline(job['company'])}", f"{job['dates']} | {job['location']}"))
                if job.get("intro"):
                    out.append(f'<p class="lead">{inline(job["intro"])}</p>')
                out.append(_list(job["bullets"]))
        elif name == "projects":
            for project in content:
                out.append(_row(_titled(project["name"], project.get("url")), project.get("dates", "")))
                if project.get("blurb"):
                    out.append(f'<p class="lead">{inline(project["blurb"])}</p>')
                out.append(_list(project["bullets"]))
        elif name == "skills":
            out.extend(_skill_line(*group) for group in content)
        elif name == "certifications":
            out.append(_list(content))
    return "\n".join(out)


def page_html(body: str, title: str, size: float, leading: float = LEADING) -> str:
    return (
        f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>\n'
        f"<style>:root{{--size:{size}pt;--leading:{leading};}}\n{CSS}</style></head>\n<body>\n{body}\n</body></html>\n"
    )


def to_text(doc: dict) -> str:
    """The CV as plain text: what a parser sees, and what the keyword check reads."""
    basics = doc["basics"]
    lines = [basics["name"].upper(), " | ".join([basics["location"], basics["phone"], basics["email"], *basics.get("links", [])]), ""]
    for name, content in doc["sections"]:
        lines.append(HEADINGS[name].upper())
        if name == "summary":
            lines.append(plain(content))
        elif name == "education":
            for edu in content:
                lines.append(f"{edu['degree']} - {edu['school_shown']} ({edu['dates']}, {edu['location']})")
                lines.append(plain(f"- GPA {edu['gpa']}, {edu.get('rank', '')}. Coursework: {', '.join(edu['coursework_shown'])}"))
        elif name in ("experience", "projects"):
            for entry in content:
                head = f"{entry['title']} - {entry['company']}" if name == "experience" else entry["name"]
                lines.append(f"{head} ({entry.get('dates', '')})")
                if lead := entry.get("intro") or entry.get("blurb"):
                    lines.append(plain(lead))
                lines.extend(f"- {plain(b)}" for b in entry["bullets"])
        elif name == "skills":
            lines.extend(f"{group}: {', '.join([*items, *also])}" for group, items, also in content)
        elif name == "certifications":
            lines.extend(f"- {plain(c)}" for c in content)
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- PDF


def print_pdf(html_path: Path, pdf_path: Path) -> None:
    browser = find_browser()
    if browser is None:
        raise RenderError("No Chrome, Chromium, Edge or Brave found. Install one, or set CV_BROWSER to its path.")
    with tempfile.TemporaryDirectory(prefix="cv-browser-") as profile:
        result = subprocess.run(
            [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--user-data-dir={profile}",
                f"--print-to-pdf={pdf_path}",
                html_path.resolve().as_uri(),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    if result.returncode != 0 or not pdf_path.exists():
        raise RenderError(f"The browser could not print the PDF:\n{result.stderr.strip()[-600:]}")


def page_count(pdf_path: Path) -> int:
    return len(re.findall(rb"/Type\s*/Page(?![A-Za-z])", pdf_path.read_bytes()))


def links_in(pdf_path: Path) -> set[str]:
    """The link targets that really open when clicked in the PDF."""
    return {m.decode("latin-1") for m in re.findall(rb"/URI\s*\(([^)]*)\)", pdf_path.read_bytes())}


def build_pdf(body: str, title: str, pdf_path: Path) -> tuple[int, float]:
    """Prints one page at the largest type size that fits. Returns (pages used, size used)."""
    html_path = pdf_path.with_suffix(".html")

    def pages_at(size: float) -> int:
        html_path.write_text(page_html(body, title, size), encoding="utf-8")
        print_pdf(html_path, pdf_path)
        return page_count(pdf_path)

    low, high, best = 0, len(SIZES) - 1, None
    while low <= high:
        middle = (low + high) // 2
        if pages_at(SIZES[middle]) <= 1:
            best, low = middle, middle + 1
        else:
            high = middle - 1
    if best is None:
        return pages_at(SIZES[0]), SIZES[0]
    return pages_at(SIZES[best]), SIZES[best]
