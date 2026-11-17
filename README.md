# Cover letter generator

Write each cover letter as a Markdown file, then render it to a one-page A4 PDF with a clean, classic layout: centred name and contact line, a thin rule, an underlined title, and a bold signature.

## Setup

```bash
pip install -r requirements.txt
cp profile.example.json profile.json   # then fill in your details
```

`profile.json` holds your personal details. It is git-ignored, so it stays on your machine.

## Write a letter

Copy `letters/example-company-product-manager.md` to a new file, such as `letters/acme-product-manager.md`, and replace the placeholders:

```markdown
---
company: Acme
role: Product Manager
date: 1 February 2027
country: Germany
salutation: Dear Hiring Team,
---

First body paragraph.

Second body paragraph.

Closing paragraph.
```

- `country` decides the header. If it differs from `home_country` in `profile.json`, the header shows "Open to Relocation" and the closing paragraph must mention relocation.
- Body paragraphs are separated by blank lines. Use `**text**` for bold.
- Do not write your name, contact details or sign-off in the letter. They come from `profile.json`.

## Build

```bash
python3 make_cover_letter.py letters/*.md --out out/
```

PDFs are written to `out/` as `Cover_Letter_<Name>_<Company>_<Role>.pdf`.

## What the build checks

| Check | Result |
|---|---|
| En dash or em dash anywhere in the letter | Error, PDF not built |
| Unfilled placeholder in brackets, such as `[Company]` | Error, PDF not built |
| Letter runs past one page | Error, PDF not built |
| Role outside home country whose closing paragraph does not mention relocation | Error |
| Role in home country whose closing paragraph mentions relocation | Error |
| Body outside 350 to 450 words | Warning only |

## Workflow

1. Draft the letter in `letters/`. The Markdown file is the source of truth.
2. Run the build and review the PDF.
3. Commit the `.md` file. Commit PDFs only if you want them in the repo, and remove `out/` from `.gitignore` if so.

## Files

| File | Purpose |
|---|---|
| `make_cover_letter.py` | The generator |
| `profile.example.json` | Template for your details (copy to `profile.json`) |
| `letters/example-company-product-manager.md` | Template letter with placeholders |
| `requirements.txt` | Python dependencies (reportlab) |
| `.gitignore` | Keeps `profile.json` and generated files out of git |
