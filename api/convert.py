"""DropMD conversion endpoint — Vercel Python function.

POST raw file bytes with the filename in the `x-filename` header (or
`?filename=` query param) and get LLM-ready Markdown back as JSON.
Engine: microsoft/markitdown. Files are processed in memory, never stored.
"""

import io
import json
import math
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from markitdown import MarkItDown, StreamInfo
from markitdown._exceptions import (
    FileConversionException,
    MarkItDownException,
    MissingDependencyException,
    UnsupportedFormatException,
)

MAX_BYTES = 4 * 1024 * 1024  # Vercel rejects bodies >4.5MB; we cap at 4MB

# Module-level so warm invocations skip magika model loading
_md = MarkItDown(enable_plugins=False)

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".xls",
    ".html", ".htm", ".csv", ".json", ".xml",
    ".epub", ".zip", ".txt", ".md", ".markdown", ".ipynb", ".rss", ".atom",
}


def convert_bytes(data: bytes, filename: str) -> str:
    """Convert a file's bytes to Markdown using MarkItDown."""
    ext = os.path.splitext(filename)[1].lower()
    info = StreamInfo(extension=ext or None, filename=filename or None)
    result = _md.convert_stream(io.BytesIO(data), stream_info=info)
    return result.markdown


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _landing_html() -> bytes | None:
    """The Python app captures '/' on Vercel, so it serves the landing itself."""
    here = os.path.dirname(os.path.abspath(__file__))
    for candidate in (
        os.path.join(here, "..", "public", "index.html"),
        os.path.join(os.getcwd(), "public", "index.html"),
    ):
        try:
            with open(candidate, "rb") as f:
                return f.read()
        except OSError:
            continue
    return None


USAGE = {
    "service": "DropMD — https://github.com/MikeIdeas2025/dropmd",
    "usage": (
        "POST raw file bytes to this endpoint with the filename in the "
        "'x-filename' header or '?filename=' query param. Max 4MB."
    ),
    "example": (
        'curl -X POST --data-binary @report.pdf '
        '-H "x-filename: report.pdf" https://dropmd.vercel.app/api/convert'
    ),
    "formats": sorted(SUPPORTED_EXTENSIONS),
}


class handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "x-filename, content-type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204, {})

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            return self._send(200, USAGE)
        html = _landing_html()
        if html is None:
            self.send_response(307)
            self.send_header("Location", "/index.html")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.send_header("Cache-Control", "public, max-age=0, must-revalidate")
        self.end_headers()
        self.wfile.write(html)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return self._send(400, {"ok": False, "error": "Empty body. Send the file bytes as the request body."})
        if length > MAX_BYTES:
            return self._send(413, {"ok": False, "error": "File too large. The free tier accepts files up to 4MB."})

        query = parse_qs(urlparse(self.path).query)
        filename = self.headers.get("x-filename") or (query.get("filename") or [""])[0]
        filename = os.path.basename(filename.strip())
        if not filename:
            return self._send(400, {"ok": False, "error": "Missing filename. Pass it via the 'x-filename' header or '?filename=' query param."})

        data = self.rfile.read(length)

        try:
            markdown = convert_bytes(data, filename)
        except (UnsupportedFormatException, MissingDependencyException):
            return self._send(415, {"ok": False, "error": f"Unsupported file format: '{filename}'. See GET /api/convert for supported formats."})
        except (FileConversionException, MarkItDownException):
            return self._send(422, {"ok": False, "error": "Conversion failed. The file may be corrupted or password-protected."})
        except Exception:
            return self._send(422, {"ok": False, "error": "Unexpected conversion error. Try a different file."})

        self._send(200, {
            "ok": True,
            "filename": filename,
            "markdown": markdown,
            "chars": len(markdown),
            "tokens_estimate": math.ceil(len(markdown) / 4),
        })
