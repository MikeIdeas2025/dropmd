# DropMD ⬇️📝

**Drop any file. Get LLM-ready Markdown.**

Free web converter + API that turns PDF, Word, PowerPoint, Excel, HTML, CSV, JSON, XML, EPub and ZIP files into clean, token-efficient Markdown for ChatGPT, Claude and RAG pipelines.

**Live:** https://dropmd.vercel.app
**Engine:** [microsoft/markitdown](https://github.com/microsoft/markitdown)

## Why

LLMs "speak" Markdown natively and it's highly token-efficient. Copy-pasting from Word or PDF flattens documents into walls of text; DropMD preserves headings, tables, lists and links — the structure that gives your prompt context.

## API

No key needed while in beta. Send raw bytes, get JSON back:

```bash
curl -X POST --data-binary @report.pdf \
     -H "x-filename: report.pdf" \
     https://dropmd.vercel.app/api/convert
```

```json
{ "ok": true, "filename": "report.pdf", "markdown": "# …", "chars": 4936, "tokens_estimate": 1234 }
```

| | |
|---|---|
| Max file size | 4MB (serverless request limit) |
| Filename | `x-filename` header or `?filename=` query param |
| Errors | JSON `{ ok: false, error }` with 400 / 413 / 415 / 422 |
| Usage doc | `GET /api/convert` |

## Stack

- **Frontend:** single static page (`api/_landing.html`, served by the function), vanilla JS, zero build step
- **Backend:** one Vercel Python function ([`api/convert.py`](api/convert.py)) wrapping MarkItDown
- Files are converted **in memory** and never stored or logged

## Run locally

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -r requirements.txt
python -c "
import importlib.util
from http.server import HTTPServer
spec = importlib.util.spec_from_file_location('convert', 'api/convert.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
print('http://127.0.0.1:8931'); HTTPServer(('127.0.0.1', 8931), mod.handler).serve_forever()"
```

or `vercel dev` if you have the Vercel CLI.

## Roadmap

- [ ] Files >4MB via direct blob upload (Pro)
- [ ] Batch conversion (Pro)
- [ ] API keys & rate limits (Pro)
- [ ] URL / YouTube transcript input
- [ ] Image OCR & audio transcription
- [ ] Usage analytics

## Credits & license

Built by [Michele Lauro](https://www.linkedin.com/in/michelelauro/) on top of Microsoft's open-source [MarkItDown](https://github.com/microsoft/markitdown). MIT licensed.
