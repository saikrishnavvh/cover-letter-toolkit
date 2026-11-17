#!/usr/bin/env python3
"""Render cover letter Markdown files into one-page A4 PDFs.

Setup (once):
    pip install -r requirements.txt
    cp profile.example.json profile.json     # then fill in your details

Usage:
    python3 make_cover_letter.py letters/*.md --out out/

Each letter file has a front-matter block (company, role, date, country,
salutation) followed by body paragraphs separated by blank lines. Your name,
contact details and sign-off come from profile.json, so they are never
written into a letter.

Checks (run on every build):
  error    en dash or em dash anywhere in the letter
  error    unfilled placeholder in brackets, such as [Company]
  error    output runs to more than one page
  error    non-home-country role whose closing paragraph does not mention relocation
  error    home-country role whose closing paragraph mentions relocation
  warning  body outside 350-450 words
"""
import argparse
import json
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

HERE = Path(__file__).resolve().parent
PROFILE_PATH = HERE / "profile.json"
PROFILE_KEYS = ["name", "signature", "location", "home_country", "phone",
                "email", "linkedin_url", "linkedin_label", "sign_off"]
LETTER_KEYS = ["company", "role", "date", "country", "salutation"]
WORD_RANGE = (350, 450)
LINK_COLOR = "#1f5fbf"
RULE_COLOR = colors.HexColor("#999999")

STYLES = {
    "name": ParagraphStyle("name", fontName="Times-Bold", fontSize=15, leading=18, alignment=TA_CENTER),
    "contact": ParagraphStyle("contact", fontName="Times-Roman", fontSize=10.5, leading=13, alignment=TA_CENTER),
    "title": ParagraphStyle("title", fontName="Times-Bold", fontSize=12.5, leading=16, alignment=TA_CENTER),
    "body": ParagraphStyle("body", fontName="Times-Roman", fontSize=11.5, leading=15.5, alignment=TA_LEFT, spaceAfter=8),
    "sig": ParagraphStyle("sig", fontName="Times-Bold", fontSize=11.5, leading=15.5, alignment=TA_LEFT),
}


def load_profile() -> dict:
    if not PROFILE_PATH.exists():
        sys.exit("profile.json not found. Copy profile.example.json to profile.json and fill it in.")
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    missing = [k for k in PROFILE_KEYS if not profile.get(k)]
    if missing:
        sys.exit(f"profile.json is missing: {', '.join(missing)}")
    return profile


def parse_letter(path: Path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        sys.exit(f"{path}: missing front matter block (--- ... ---) at top of file")

    meta = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()

    missing = [k for k in LETTER_KEYS if not meta.get(k)]
    if missing:
        sys.exit(f"{path}: front matter is missing {', '.join(missing)}")

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", match.group(2).strip()) if p.strip()]
    return meta, paragraphs


def lint(meta: dict, paragraphs: list[str], profile: dict) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    everything = " ".join([*meta.values(), *paragraphs])

    if re.search(r"[–—]", everything):
        errors.append("contains an en dash or em dash; use commas, periods or parentheses")
    if re.search(r"\[[^\]]*\]", everything):
        errors.append("contains an unfilled placeholder in brackets")

    is_home = meta["country"].lower() == profile["home_country"].lower()
    closing = paragraphs[-1].lower() if paragraphs else ""
    if not is_home and "relocat" not in closing:
        errors.append(f"role outside {profile['home_country']}: closing paragraph should say you are open to relocating")
    if is_home and "relocat" in closing:
        errors.append(f"role in {profile['home_country']}: closing paragraph should not mention relocation")

    words = len(" ".join(paragraphs).split())
    if not WORD_RANGE[0] <= words <= WORD_RANGE[1]:
        warnings.append(f"body is {words} words (target {WORD_RANGE[0]}-{WORD_RANGE[1]})")

    return errors, warnings


def inline(text: str) -> str:
    """Escape XML characters and turn **bold** into reportlab bold tags."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)


def build_story(meta: dict, paragraphs: list[str], profile: dict):
    is_home = meta["country"].lower() == profile["home_country"].lower()

    contact_parts = [
        profile["location"],
        profile["phone"],
        f'<a href="mailto:{profile["email"]}" color="{LINK_COLOR}"><u>{profile["email"]}</u></a>',
        f'<a href="{profile["linkedin_url"]}" color="{LINK_COLOR}"><u>{profile["linkedin_label"]}</u></a>',
    ]
    if not is_home:
        contact_parts.append("Open to Relocation")

    title = inline(f"Cover Letter - {meta['company']}, {meta['role']}")
    story = [
        Paragraph(inline(profile["name"]), STYLES["name"]),
        Spacer(1, 8),
        Paragraph(" | ".join(contact_parts), STYLES["contact"]),
        HRFlowable(width="100%", thickness=0.6, color=RULE_COLOR, spaceBefore=8, spaceAfter=10),
        Paragraph(f"<u>{title}</u>", STYLES["title"]),
        Spacer(1, 18),
        Paragraph(inline(meta["date"]), STYLES["body"]),
        Paragraph(inline(meta["salutation"]), STYLES["body"]),
    ]
    story += [Paragraph(inline(text), STYLES["body"]) for text in paragraphs]
    story += [
        Spacer(1, 10),
        Paragraph(inline(profile["sign_off"]), STYLES["body"]),
        Spacer(1, 8),
        Paragraph(f"<b>{inline(profile['signature'])}</b>", STYLES["sig"]),
    ]
    return story


def render(path: Path, out_dir: Path, profile: dict) -> bool:
    meta, paragraphs = parse_letter(path)
    errors, warnings = lint(meta, paragraphs, profile)

    for w in warnings:
        print(f"  warning: {w}")
    if errors:
        for e in errors:
            print(f"  error: {e}")
        print(f"{path.name}: not built")
        return False

    out_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9]+", "_", f"{profile['name']}_{meta['company']}_{meta['role']}").strip("_")
    out = out_dir / f"Cover_Letter_{slug}.pdf"

    pages = []
    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=0.8 * inch,
        rightMargin=0.8 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title=f"Cover Letter - {meta['company']}, {meta['role']}",
        author=profile["signature"],
    )
    counter = lambda canvas, document: pages.append(1)  # noqa: E731
    doc.build(build_story(meta, paragraphs, profile), onFirstPage=counter, onLaterPages=counter)

    if len(pages) > 1:
        print(f"  error: letter runs to {len(pages)} pages; shorten the body")
        out.unlink(missing_ok=True)
        print(f"{path.name}: not built")
        return False

    print(f"{path.name} -> {out}")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("letters", nargs="+", type=Path, help="Markdown letter files")
    parser.add_argument("--out", type=Path, default=HERE / "out", help="output folder (default: ./out)")
    args = parser.parse_args()

    profile = load_profile()
    results = [render(path, args.out, profile) for path in args.letters]
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
