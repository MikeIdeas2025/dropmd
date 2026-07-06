# DropMD — Design Spec

**Date:** 2026-07-06
**Status:** Approved (autonomous /goal session — decisions documented in lieu of interactive approval)

## What

DropMD is a free micro-SaaS: drop any document, get clean LLM-ready Markdown.
Engine: [microsoft/markitdown](https://github.com/microsoft/markitdown) (v0.1.6).
Positioning: the fastest way to turn files into token-efficient Markdown for ChatGPT/Claude/RAG pipelines.

## Why

- LLMs "speak" Markdown natively; Markdown is token-efficient vs raw formats.
- Existing flows (copy-paste from Word/PDF) lose structure (headings, tables, lists).
- MarkItDown is CLI/Python-only — no-code users have no easy way to use it. DropMD is the web UI.

## Business model

- **v1: 100% free**, no auth, no storage. Goal: validate demand + collect traffic.
- **Later (roadmap, not built):** Pro tier — files >4MB, batch conversion, API keys, OCR/audio transcription.
- The Vercel 4.5MB request-body limit doubles as the free-tier boundary.

## Architecture

Single Vercel project, no build step:

```
dropmd/
├── api/
│   ├── _landing.html   # landing + converter app (vanilla JS, served by the function)
│   └── convert.py      # Vercel Python function — MarkItDown engine + landing routes
├── requirements.txt    # markitdown[pdf,docx,pptx,xlsx]==0.1.6
├── vercel.json         # maxDuration 60
├── README.md, LICENSE (MIT), .gitignore
└── docs/superpowers/specs/
```

### API contract — `POST /api/convert`

- Request: raw binary body (NOT multipart), filename via `x-filename` header or `?filename=` query param. Max 4MB (Vercel hard limit 4.5MB).
- Response 200 (JSON): `{ ok, filename, markdown, chars, tokens_estimate }`
  - `tokens_estimate` = ceil(chars/4) heuristic — labeled approximate in UI.
- Errors (JSON `{ ok:false, error }`): 400 missing body/filename, 413 too large, 415 unsupported format, 422 conversion failed, 405 non-POST (GET returns 200 usage doc for devs).
- CORS: `Access-Control-Allow-Origin: *` (public API is part of the product).
- `convert.py` structure: pure function `convert_bytes(data: bytes, filename: str) -> str` + thin `handler` class (testable without HTTP).

### Frontend (index.html)

One page, converter above the fold:
1. **Hero + converter**: headline, drag&drop zone / file picker → POST → result panel (markdown in `<pre>`, Copy button, Download .md, token badge). Loading and error states inline.
2. **Formats grid**: PDF, Word, PowerPoint, Excel, HTML, CSV, JSON, XML, EPub, ZIP.
3. **How it works**: 3 steps.
4. **Why Markdown for LLMs**: structure preserved + token efficiency.
5. **Developers/API**: curl example.
6. **FAQ**: privacy (in-memory, never stored), file limit, free-status, engine credit.
7. Footer: GitHub repo link, "Powered by Microsoft MarkItDown", credit Mikel.

No frameworks, no analytics in v1 (PostHog is a fast follow), dark theme, English copy.

## Constraints & decisions log

| Decision | Choice | Why |
|---|---|---|
| Name | DropMD | drop file → MD; repo/subdomain free |
| Hosting | Vercel only | goal requirement + zero cost |
| Bundle size | 233MB measured with `[pdf,docx,pptx,xlsx]` | under 250MB limit; fallback = drop `xlsx` (−~55MB pandas) |
| Excluded formats v1 | audio, images-OCR, YouTube URLs | heavy deps / need LLM keys; roadmap |
| Upload encoding | raw body, not multipart | stdlib `cgi` deprecated; simpler for curl users |
| Token count | chars/4 heuristic | tiktoken adds MBs; approximation acceptable |
| File limit | 4MB (UI-enforced + server-checked) | Vercel 4.5MB hard limit |
| Auth/DB | none | free product, YAGNI |

## Error handling

- Frontend validates size (<4MB) and non-empty before upload; API re-validates everything.
- MarkItDown exceptions → 415 (UnsupportedFormatException / FileConversionException) or 422 generic, message safe for display.
- Empty conversion result (e.g. blank file) → 200 with empty markdown + UI notice.

## Testing

1. Local: `uv` venv py3.12 → direct tests of `convert_bytes` with real files (docx via macOS `textutil`, pdf via `cupsfilter`, html/csv/json fixtures).
2. Post-deploy e2e: curl prod `/api/convert` with a real file; load landing page.

## Delivery

- GitHub: `MikeIdeas2025/dropmd`, public, MIT.
- Vercel: project `dropmd` → production deploy via CLI.

## v2 — 2026-07-07 (Loom-style redesign + i18n)

- **UI**: light theme inspired by Loom (violet #625DF5, Plus Jakarta Sans, pill buttons, soft cards, lilac accents). Replaced the dark neon-gradient theme, emoji icons and gradient text (AI-slop markers) with inline SVG icons and a solid accent color.
- **i18n**: EN/IT switch in nav. JS dictionary + `data-i18n`/`data-i18n-html` attributes; auto-detects `navigator.language`, persists in localStorage, updates `<html lang>`. Runtime strings (loading, errors, buttons) localized too; API errors mapped client-side by status code so Italian users get Italian messages.
- **Copy**: humanizer pass on both languages. Removed em dashes, rule-of-three lists, slogan headlines and tailing negations; replaced with concrete claims (e.g. "The file never touches a disk. It is discarded the moment the response is sent back to you.").

## Roadmap (not in v1)

- URL/YouTube input · batch & >4MB via Blob upload (Pro) · API keys · PostHog analytics · image OCR & audio transcription (needs LLM/Azure keys) · custom domain.
